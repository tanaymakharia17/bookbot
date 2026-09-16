"""Tools the review agent can call to stage changes on the pending plan."""
from __future__ import annotations

import uuid
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
]


def _projected_lines(submission) -> list[dict]:
    return project(submission)["line_items"]


def apply_tool_call(submission, name: str, arguments: dict[str, Any]) -> str | None:
    """Apply one tool call to the pending plan. Returns a human label, or None."""
    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    arguments = arguments or {}

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
            return None
        label = "Exclude personal: " + ", ".join(descriptions)
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "exclude_personal",
            "targets": descriptions, "label": label,
        })
        return label

    if name == "capitalize_items":
        threshold = float(settings.CAPEX_THRESHOLD)
        matches = [li for li in _projected_lines(submission)
                   if not li.get("personal") and li["amount"] >= threshold]
        if not matches:
            return None
        label = f"Capitalize items ≥ ${threshold:,.2f}"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "capitalize",
            "threshold": threshold, "label": label,
        })
        return label

    if name == "apply_discount":
        percent = float(arguments.get("percent", 10))
        label = f"Apply a {percent:g}% discount across all lines"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "discount", "percent": percent, "label": label,
        })
        return label

    if name == "split_line_item":
        target = arguments.get("target")
        first = float(arguments.get("first_percent", 70))
        if not target:
            return None
        label = f"Split {target} {first:g} / {100 - first:g}"
        plan["line_item_ops"].append({
            "id": new_op_id(), "type": "split",
            "target": target, "ratios": (first, 100 - first), "label": label,
        })
        return label

    if name == "add_task":
        title = (arguments.get("title") or "").strip()
        if not title:
            return None
        task = {"id": f"task_{uuid.uuid4().hex[:8]}", "title": title, "done": False, "source": "user"}
        label = f"Add task: {title}"
        plan["task_ops"].append({"id": new_op_id(), "type": "add", "task": task, "label": label})
        return label

    if name == "complete_task":
        title = (arguments.get("title") or "").strip().lower()
        if not title:
            return None
        tasks = project(submission)["tasks"]
        match = next((t for t in tasks if t["title"].lower() == title), None)
        if not match:
            return None
        label = f"Complete action: {match['title']}"
        plan["task_ops"].append({
            "id": new_op_id(), "type": "set_done",
            "task_id": match["id"], "done": True, "label": label,
        })
        return label

    return None