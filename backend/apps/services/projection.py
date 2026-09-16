"""Projection of committed state + pending plan into the reviewed view."""
from __future__ import annotations

import copy
from typing import Any

from apps.services.extraction import mock_extract, recompute_fields
from apps.services.task_seeding import seed_agent_tasks


def empty_plan() -> dict[str, list]:
    return {"save_files": [], "line_item_ops": [], "task_ops": []}


def plan_count(plan: dict[str, Any] | None) -> int:
    if not plan:
        return 0
    return (
        len(plan.get("save_files", []))
        + len(plan.get("line_item_ops", []))
        + len(plan.get("task_ops", []))
    )


def dedup(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def apply_line_op(lines: list[dict], op: dict[str, Any]) -> list[dict]:
    kind = op.get("type")
    if kind == "exclude_personal":
        targets = set(op.get("targets", []))
        for line in lines:
            if line["description"] in targets:
                line["personal"] = True
    elif kind == "capitalize":
        threshold = op.get("threshold", 2500.00)
        for line in lines:
            if not line.get("personal") and line["amount"] >= threshold:
                line["category"] = "Fixed Assets"
    elif kind == "discount":
        factor = 1 - op.get("percent", 10) / 100
        for line in lines:
            line["amount"] = round(line["amount"] * factor, 2)
            line["unit_price"] = round(line["unit_price"] * factor, 2)
    elif kind == "split":
        target = op.get("target")
        a, b = op.get("ratios", (70, 30))
        for line in lines:
            if line["description"] == target:
                part_a = round(line["amount"] * a / 100, 2)
                part_b = round(line["amount"] - part_a, 2)
                line["amount"] = part_a
                line["unit_price"] = part_a
                line["category"] = "Software"
                line["description"] = f"{target} ({a}%)"
                lines.append({
                    "description": f"{target} ({b}%)", "qty": 1, "unit_price": part_b,
                    "amount": part_b, "category": "Software", "personal": False,
                })
                break
    return lines


def apply_task_op(tasks: list[dict], op: dict[str, Any]) -> list[dict]:
    kind = op.get("type")
    if kind == "add":
        tasks = tasks + [copy.deepcopy(op["task"])]
    elif kind == "set_done":
        for task in tasks:
            if task["id"] == op.get("task_id"):
                task["done"] = bool(op.get("done"))
    elif kind == "remove":
        tasks = [t for t in tasks if t["id"] != op.get("task_id")]
    return tasks


def project(submission) -> dict[str, Any]:
    """Return the projected (committed + pending) view of a submission."""
    plan = submission.pending_plan or empty_plan()
    saved = plan.get("save_files", [])

    if saved:
        text = " ".join([submission.raw_input or "", *(submission.file_names or []), *saved])
        category = (submission.line_items or [{}])[0].get("category") if submission.line_items else ""
        vendor, category, total, payment = recompute_fields(
            submission.vendor or "", category, text
        )
        lines = mock_extract(vendor, category, total)
    else:
        vendor = submission.vendor
        payment = submission.payment_method
        lines = copy.deepcopy(submission.line_items or [])

    for op in plan.get("line_item_ops", []):
        lines = apply_line_op(lines, op)

    if saved:
        tasks = [copy.deepcopy(t) for t in (submission.tasks or []) if t.get("source") == "user"]
        tasks += seed_agent_tasks({
            "vendor": vendor,
            "payment_method": payment,
            "line_items": lines,
            "state": submission.state,
            "raw_input": submission.raw_input,
        })
    else:
        tasks = copy.deepcopy(submission.tasks or [])

    for op in plan.get("task_ops", []):
        tasks = apply_task_op(tasks, op)

    return {
        "vendor": vendor,
        "payment_method": payment,
        "line_items": lines,
        "tasks": tasks,
        "file_names": dedup(list(submission.file_names or []) + list(saved)),
        "has_pending": plan_count(plan) > 0,
    }


def plan_labels(plan: dict[str, Any] | None) -> list[dict[str, str]]:
    if not plan:
        return []
    labels: list[dict[str, str]] = []
    for name in plan.get("save_files", []):
        labels.append({"id": f"file::{name}", "kind": "file", "label": f"Save file: {name}"})
    for op in plan.get("line_item_ops", []):
        labels.append({"id": op["id"], "kind": "line", "label": op.get("label", op.get("type", ""))})
    for op in plan.get("task_ops", []):
        labels.append({"id": op["id"], "kind": "task", "label": op.get("label", op.get("type", ""))})
    return labels