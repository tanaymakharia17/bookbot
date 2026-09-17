"""Review agent: OpenRouter LLM with tool calling, deterministic fallback."""
from __future__ import annotations

import json
from typing import Any

from django.conf import settings

from apps.agents.tools import TOOL_DEFINITIONS, dispatch_tool, new_op_id
from apps.core.constants import PERSONAL_KEYWORDS
from apps.services.projection import empty_plan, project

SYSTEM_PROMPT = """You are Bookbot, an AI bookkeeping review assistant for a CPA.
You help review an extracted submission's line items and action items.

Rules:
- Changes are STAGED in a "pending plan"; they are NOT applied until the CPA executes the plan.
  Never claim a change is done — say it was added to the plan.
- Use the provided tools to stage changes when the CPA asks for them.
- The submission context includes `documents`: a per-file digest with transcribed text.
  If the CPA asks about something that may not be in the line items (tax, fees, discounts,
  a specific detail), call `inspect_document` to re-read the relevant file before answering.
- Use `add_line_item` / `update_line_item` / `remove_line_item` to fix omissions or mistakes.
- Reference line items by their exact description.
- Be concise and specific.
"""


class ContextLimitReached(Exception):
    """Raised when a submission's chat context or token budget is exhausted."""


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Approximate token count for a message list (chars / chars-per-token)."""
    chars = 0
    for entry in messages:
        content = entry.get("content")
        if isinstance(content, str):
            chars += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    chars += len(str(part.get("text") or ""))
        chars += len(str(entry.get("tool_calls") or ""))
    return int(chars / max(settings.AGENT_CHARS_PER_TOKEN, 1))


def respond(submission, message: str) -> str:
    """Return the agent's reply, staging any requested changes on the plan."""
    if settings.OPENROUTER_API_KEY:
        try:
            return _llm_respond(submission, message)
        except ContextLimitReached:
            raise
        except Exception:  # noqa: BLE001 - fall back to deterministic responder
            pass
    return _fallback_respond(submission, message)


def _llm_respond(submission, message: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
    )

    proj = project(submission)
    documents = [
        {
            "file": doc.get("file"),
            "vendor": doc.get("vendor"),
            "date": doc.get("date"),
            "total": doc.get("total"),
            "text": doc.get("text") or "",
        }
        for doc in (submission.document_context or [])
    ]
    context: dict[str, Any] = {
        "submission_id": str(submission.id),
        "state": submission.state,
        "files": submission.file_names or [],
        "vendor": proj["vendor"],
        "payment_method": proj["payment_method"],
        "line_items": proj["line_items"],
        "tasks": proj["tasks"],
        "pending_plan": submission.pending_plan or empty_plan(),
        "documents": documents,
    }

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Submission context (JSON):\n" + json.dumps(context, indent=2, default=str)},
    ]
    # Full conversation history — this submission's chat is one continuous session.
    for past in (submission.chat_messages or []):
        messages.append({"role": past["role"], "content": past["content"]})
    messages.append({"role": "user", "content": message})

    applied: list[str] = []
    final_text = ""
    for _ in range(4):
        estimated = estimate_messages_tokens(messages)
        if estimated > settings.AGENT_CONTEXT_MAX_TOKENS:
            raise ContextLimitReached(
                f"This submission's chat context is too large for one request "
                f"(~{estimated:,} tokens; limit {settings.AGENT_CONTEXT_MAX_TOKENS:,}). "
                "Start a new submission or remove some documents to continue."
            )
        if submission.tokens_used + estimated > settings.AGENT_SUBMISSION_TOKEN_BUDGET:
            raise ContextLimitReached(
                f"This submission has reached its AI token budget "
                f"({submission.tokens_used:,}/{settings.AGENT_SUBMISSION_TOKEN_BUDGET:,}). "
                "Start a new submission to continue."
            )

        completion = client.chat.completions.create(
            model=settings.AGENT_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=800,
            extra_headers={"X-Session-Id": str(submission.id)},
        )
        if completion.usage and completion.usage.total_tokens:
            submission.tokens_used += int(completion.usage.total_tokens)
            submission.save(update_fields=["tokens_used", "updated_at"])

        choice = completion.choices[0].message
        tool_calls = list(choice.tool_calls or [])
        if not tool_calls:
            final_text = (choice.content or "").strip()
            break

        messages.append({
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ],
        })
        for call in tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            label, observation = dispatch_tool(submission, call.function.name, arguments)
            if label:
                applied.append(label)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": observation or "ok",
            })

    if applied:
        note = "Added to the pending plan:\n\n- " + "\n- ".join(applied)
        return f"{final_text}\n\n{note}".strip() if final_text else note
    if final_text:
        return final_text
    return _fallback_respond(submission, message)


def _fallback_respond(submission, message: str) -> str:
    m = message.lower()
    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    lines = project(submission)["line_items"]

    if any(w in m for w in ["exclude", "personal", "private", "vacuum"]):
        if not lines:
            return "There's nothing to exclude yet."
        matches = [
            li for li in lines
            if not li.get("personal")
            and any(k in li["description"].lower() for k in PERSONAL_KEYWORDS)
        ] or [lines[-1]]
        descriptions = [li["description"] for li in matches]
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "exclude_personal",
            "targets": descriptions,
            "label": "Exclude personal: " + ", ".join(descriptions),
        })
        return f"Added to the plan: exclude {len(descriptions)} personal item(s). It applies when you execute the plan."

    if any(w in m for w in ["capitalize", "fixed asset", "reclass", "depreciat"]):
        threshold = float(settings.CAPEX_THRESHOLD)
        matches = [li for li in lines if not li.get("personal") and li["amount"] >= threshold]
        if not matches:
            return f"No line items reach the ${threshold:,.2f} CapEx threshold."
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "capitalize", "threshold": threshold,
            "label": f"Capitalize items ≥ ${threshold:,.2f}",
        })
        return f"Added to the plan: capitalize {len(matches)} item(s)."

    if any(w in m for w in ["discount", "proportional", "reduce"]):
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "discount", "percent": 10,
            "label": "Apply a 10% discount across all lines",
        })
        return "Added to the plan: a 10% discount across all lines."

    if any(w in m for w in ["split", "percent", "%"]):
        if not lines:
            return "There's nothing to split yet."
        target = max(lines, key=lambda li: li["amount"])
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "split", "target": target["description"],
            "ratios": (70, 30), "label": f"Split {target['description']} 70 / 30",
        })
        return f"Added to the plan: split {target['description']} 70 / 30."

    if any(w in m for w in ["approve", "looks good", "finalize", "post"]):
        return ("Review the pending plan, click **Execute plan**, then "
                "**Approve & Post to Ledger** to save it to the ledger.")

    return ("I can stage changes for you: exclude personal items, capitalize above threshold, "
            "apply a discount, or split a line. Attach documents with the paperclip to stage them. "
            "Nothing changes until you execute the plan.")