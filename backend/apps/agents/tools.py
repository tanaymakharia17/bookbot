"""Tools the review agent can call to inspect documents and stage plan changes."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from django.conf import settings

from apps.core.constants import PERSONAL_KEYWORDS
from apps.services.projection import empty_plan, project


def new_op_id() -> str:
    return f"op_{uuid.uuid4().hex[:8]}"


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "exclude_personal_items",
            "description": "Stage the exclusion of personal line items from reimbursement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exact descriptions of the line items to exclude.",
                    }
                },
                "required": ["descriptions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capitalize_items",
            "description": "Stage capitalizing all business items at or above the CapEx threshold.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_discount",
            "description": "Stage a proportional discount across every line item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "percent": {"type": "number", "description": "Discount percent, e.g. 10"}
                },
                "required": ["percent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "split_line_item",
            "description": "Stage splitting one line item across two software categories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Description of the line to split."},
                    "first_percent": {"type": "number", "description": "Percent for the first part."},
                },
                "required": ["target", "first_percent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a custom action item to the checklist (staged).",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Stage completing an existing action item by its title.",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_document",
            "description": (
                "Re-read one of the submission's documents and answer a question about it. "
                "Use this when the CPA asks about something that may not be in the extracted "
                "line items (tax, fees, discounts, a specific line)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Exact file name, e.g. receipt.webp"},
                    "question": {"type": "string", "description": "What to look for in the document."},
                },
                "required": ["file", "question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_line_item",
            "description": "Stage adding a missing line item (e.g. sales tax, a forgotten fee).",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "amount": {"type": "number"},
                    "qty": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "category": {
                        "type": "string",
                        "description": "One of: Fixed Assets, IT Equipment, Office Supplies, "
                        "Software, Meals, Travel, Professional Fees, Taxes, Uncategorized",
                    },
                },
                "required": ["description", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_line_item",
            "description": "Stage correcting an existing line item (amount, qty, category, description).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Exact current description."},
                    "amount": {"type": "number"},
                    "qty": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_line_item",
            "description": "Stage removing a line item that should not be there.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Exact current description."}
                },
                "required": ["target"],
            },
        },
    },
]


def _projected_lines(submission) -> list[dict]:
    return project(submission)["line_items"]


def _resolve_file(submission, name: str) -> Path | None:
    from apps.services import storage

    directory = storage.submission_dir(submission.id)
    if not directory.exists():
        return None
    lowered = name.strip().lower()
    for path in directory.iterdir():
        if path.is_file() and path.name.lower() == lowered:
            return path
    return None


def dispatch_tool(submission, name: str, arguments: dict[str, Any]) -> tuple[str | None, str]:
    """Run a tool call.

    Returns ``(plan_label, observation)`` — ``plan_label`` is set when a staged
    change was added; ``observation`` is the text fed back to the model.
    """
    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    arguments = arguments or {}

    if name == "inspect_document":
        file_name = (arguments.get("file") or "").strip()
        question = (arguments.get("question") or "").strip()
        if not file_name or not question:
            return None, "Missing file or question."
        path = _resolve_file(submission, file_name)
        if path is None:
            return None, f"File '{file_name}' not found for this submission."
        try:
            from apps.services import vlm

            answer = vlm.inspect_document(path, question)
        except Exception as exc:  # noqa: BLE001
            return None, f"Could not read the document ({type(exc).__name__})."
        return None, answer or "No answer found in the document."

    if name == "exclude_personal_items":
        descriptions = list(dict.fromkeys(arguments.get("descriptions") or []))
        if not descriptions:
            lines = _projected_lines(submission)
            matches = [
                li for li in lines
                if not li.get("personal")
                and any(k in li["description"].lower() for k in PERSONAL_KEYWORDS)
            ] or lines[-1:]
            descriptions = [li["description"] for li in matches]
        if not descriptions:
            return None, "No line items to exclude."
        label = "Exclude personal: " + ", ".join(descriptions)
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "exclude_personal",
            "targets": descriptions, "label": label,
        })
        return label, label

    if name == "capitalize_items":
        threshold = float(settings.CAPEX_THRESHOLD)
        matches = [li for li in _projected_lines(submission)
                   if not li.get("personal") and li["amount"] >= threshold]
        if not matches:
            return None, f"No line items reach the ${threshold:,.2f} CapEx threshold."
        label = f"Capitalize items ≥ ${threshold:,.2f}"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "capitalize",
            "threshold": threshold, "label": label,
        })
        return label, label

    if name == "apply_discount":
        percent = float(arguments.get("percent", 10))
        label = f"Apply a {percent:g}% discount across all lines"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "discount", "percent": percent, "label": label,
        })
        return label, label

    if name == "split_line_item":
        target = arguments.get("target")
        first = float(arguments.get("first_percent", 70))
        if not target:
            return None, "No target provided to split."
        label = f"Split {target} {first:g} / {100 - first:g}"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "split",
            "target": target, "ratios": (first, 100 - first), "label": label,
        })
        return label, label

    if name == "add_line_item":
        description = (arguments.get("description") or "").strip()
        if not description:
            return None, "Line item needs a description."
        line = {
            "description": description,
            "qty": arguments.get("qty") or 1,
            "unit_price": arguments.get("unit_price") or 0,
            "amount": arguments.get("amount") or 0,
            "category": arguments.get("category") or "Uncategorized",
        }
        label = f"Add line: {description} (${float(line['amount']):,.2f})"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "add_line_item", "line": line, "label": label,
        })
        return label, label

    if name == "update_line_item":
        target = (arguments.get("target") or "").strip()
        if not target:
            return None, "No target provided to update."
        fields = {
            key: arguments[key]
            for key in ("amount", "qty", "unit_price", "category", "description")
            if arguments.get(key) is not None
        }
        if not fields:
            return None, "No fields provided to update."
        summary = ", ".join(f"{k}={v}" for k, v in fields.items())
        label = f"Update line: {target} ({summary})"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "update_line_item",
            "target": target, "fields": fields, "label": label,
        })
        return label, label

    if name == "remove_line_item":
        target = (arguments.get("target") or "").strip()
        if not target:
            return None, "No target provided to remove."
        label = f"Remove line: {target}"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "remove_line_item",
            "target": target, "label": label,
        })
        return label, label

    if name == "add_task":
        title = (arguments.get("title") or "").strip()
        if not title:
            return None, "Task needs a title."
        task = {"id": f"task_{uuid.uuid4().hex[:8]}", "title": title, "done": False, "source": "user"}
        label = f"Add task: {title}"
        plan["task_ops"].append({"id": new_op_id(), "type": "add", "task": task, "label": label})
        return label, label

    if name == "complete_task":
        title = (arguments.get("title") or "").strip().lower()
        if not title:
            return None, "Task needs a title."
        tasks = project(submission)["tasks"]
        match = next((t for t in tasks if t["title"].lower() == title), None)
        if not match:
            return None, f"No open action titled '{title}'."
        label = f"Complete action: {match['title']}"
        plan["task_ops"].append({
            "id": new_op_id(), "type": "set_done",
            "task_id": match["id"], "done": True, "label": label,
        })
        return label, label

    return None, f"Unknown tool '{name}'."