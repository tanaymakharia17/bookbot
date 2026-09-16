"""Review agent: OpenRouter LLM with tool calling, deterministic fallback."""
from __future__ import annotations

import json
from typing import Any

from django.conf import settings

from apps.agents.tools import TOOL_DEFINITIONS, apply_tool_call, new_op_id
from apps.core.constants import PERSONAL_KEYWORDS
from apps.services.projection import empty_plan, project

SYSTEM_PROMPT = """You are Bookbot, an AI bookkeeping review assistant for a CPA.
You help review an extracted submission's line items and action items.

Rules:
- Changes are STAGED in a "pending plan"; they are NOT applied until the CPA executes the plan.
  Never claim a change is done — say it was added to the plan.
- Use the provided tools to stage changes when the CPA asks for them.
- Reference line items by their exact description.
- Be concise and specific.
"""


def respond(submission, message: str) -> str:
    """Return the agent's reply, staging any requested changes on the plan."""
    if settings.OPENROUTER_API_KEY:
        try:
            return _llm_respond(submission, message)
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
    context: dict[str, Any] = {
        "submission_id": str(submission.id),
        "state": submission.state,
        "vendor": proj["vendor"],
        "payment_method": proj["payment_method"],
        "line_items": proj["line_items"],
        "tasks": proj["tasks"],
        "pending_plan": submission.pending_plan or empty_plan(),
    }

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Submission context (JSON):\n" + json.dumps(context, indent=2, default=str)},
    ]
    for past in (submission.chat_messages or [])[-10:]:
        messages.append({"role": past["role"], "content": past["content"]})
    messages.append({"role": "user", "content": message})

    completion = client.chat.completions.create(
        model=settings.AGENT_MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        temperature=0.2,
        max_tokens=800,
    )
    choice = completion.choices[0].message

    applied: list[str] = []
    for call in (choice.tool_calls or []):
        try:
            arguments = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            arguments = {}
        label = apply_tool_call(submission, call.function.name, arguments)
        if label:
            applied.append(label)

    text = (choice.content or "").strip()
    if applied:
        note = "Added to the pending plan:\n\n- " + "\n- ".join(applied)
        return f"{text}\n\n{note}".strip() if text else note
    if text:
        return text
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