"""Pending-plan staging operations."""
from __future__ import annotations

import uuid
from typing import Any

from apps.core.constants import ACTION_FILE_HINTS
from apps.core.fsm import SubmissionFSM
from apps.core.state import SubmissionState
from apps.services.extraction import mock_extract, recompute_fields, submission_context
from apps.services.projection import (
    apply_line_op,
    apply_task_op,
    dedup,
    empty_plan,
    plan_count,
    project,
)
from apps.services.task_seeding import seed_agent_tasks


def _append_chat(submission, content: str) -> None:
    messages = list(submission.chat_messages or [])
    messages.append({"role": "agent", "content": content})
    submission.chat_messages = messages


def _propose_action_completions(submission, staged_save: list[str]) -> list[str]:
    plan = submission.pending_plan
    open_actions = {t["title"]: t for t in project(submission)["tasks"] if not t["done"]}
    proposed: list[str] = []
    for name in staged_save:
        lowered = name.lower()
        for hint, action in ACTION_FILE_HINTS.items():
            if hint in lowered and action in open_actions:
                task = open_actions[action]
                already = any(
                    o.get("type") == "set_done" and o.get("task_id") == task["id"]
                    for o in plan["task_ops"]
                )
                if not already:
                    plan["task_ops"].append({
                        "id": f"op_{uuid.uuid4().hex[:8]}",
                        "type": "set_done", "task_id": task["id"], "done": True,
                        "label": f"Complete action: {action}",
                    })
                    proposed.append(action)
    return proposed


def stage_files(submission, files: list[dict[str, Any]]) -> dict[str, Any]:
    if submission.state == SubmissionState.RAW:
        return {"error": "Extraction is still in progress."}
    if submission.state == SubmissionState.COMMITTED:
        return {"error": "This submission is posted. Create a new submission to add documents."}

    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    known = (
        set(submission.file_names or [])
        | set(submission.reference_files or [])
        | set(plan["save_files"])
    )
    staged_save: list[str] = []
    staged_ref: list[str] = []

    for entry in files:
        name = (entry.get("name") or "").strip()
        if not name or name in known:
            continue
        if entry.get("save"):
            plan["save_files"].append(name)
            staged_save.append(name)
        else:
            submission.reference_files = list(submission.reference_files or []) + [name]
            staged_ref.append(name)
        known.add(name)

    proposed = _propose_action_completions(submission, staged_save)

    lines = []
    if staged_save:
        lines.append(f"**Save {len(staged_save)} file(s)** → will recompute: " + ", ".join(staged_save))
    if staged_ref:
        lines.append(f"**{len(staged_ref)} reference file(s)** (context only, no recompute): " + ", ".join(staged_ref))
    for action in proposed:
        lines.append(f"**Complete action:** {action}")
    if lines:
        _append_chat(submission, "Added to the pending plan:\n\n- " + "\n- ".join(lines))

    return {"proposed": proposed, "staged_save": staged_save, "staged_ref": staged_ref}


def _guard(submission):
    if submission.state == SubmissionState.COMMITTED:
        return {"error": "This submission is posted."}
    return None


def stage_task_add(submission, title: str) -> dict[str, Any]:
    guard = _guard(submission)
    if guard:
        return guard
    title = (title or "").strip()
    if not title:
        return {"error": "Task title cannot be empty."}

    if any(t["title"].lower() == title.lower() for t in project(submission)["tasks"]):
        return {"error": "That task already exists."}

    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    task = {"id": f"task_{uuid.uuid4().hex[:8]}", "title": title, "done": False, "source": "user"}
    plan["task_ops"].append({
        "id": f"op_{uuid.uuid4().hex[:8]}", "type": "add", "task": task,
        "label": f"Add task: {title}",
    })
    return {}


def stage_task_toggle(submission, task_id: str, done: bool) -> dict[str, Any]:
    guard = _guard(submission)
    if guard:
        return guard

    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan

    for op in plan["task_ops"]:
        if op.get("type") == "add" and op["task"]["id"] == task_id:
            op["task"]["done"] = done
            return {}

    committed = next((t for t in (submission.tasks or []) if t["id"] == task_id), None)
    plan["task_ops"] = [
        o for o in plan["task_ops"]
        if not (o.get("type") == "set_done" and o.get("task_id") == task_id)
    ]
    if committed and committed.get("done") == done:
        return {}
    title = committed["title"] if committed else task_id
    plan["task_ops"].append({
        "id": f"op_{uuid.uuid4().hex[:8]}", "type": "set_done", "task_id": task_id, "done": done,
        "label": ("Complete action: " if done else "Reopen action: ") + title,
    })
    return {}


def stage_task_remove(submission, task_id: str) -> dict[str, Any]:
    guard = _guard(submission)
    if guard:
        return guard

    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan

    staged = next(
        (o for o in plan["task_ops"] if o.get("type") == "add" and o["task"]["id"] == task_id),
        None,
    )
    if staged:
        plan["task_ops"] = [o for o in plan["task_ops"] if o is not staged]
        return {}

    committed = next((t for t in (submission.tasks or []) if t["id"] == task_id), None)
    if not committed:
        return {"error": "Task not found."}

    plan["task_ops"] = [o for o in plan["task_ops"] if o.get("task_id") != task_id]
    plan["task_ops"].append({
        "id": f"op_{uuid.uuid4().hex[:8]}", "type": "remove", "task_id": task_id,
        "label": f"Remove task: {committed['title']}",
    })
    return {}


def remove_plan_op(submission, op_id: str) -> dict[str, Any]:
    plan = submission.pending_plan or empty_plan()
    submission.pending_plan = plan
    if op_id.startswith("file::"):
        name = op_id.split("::", 1)[1]
        plan["save_files"] = [n for n in plan["save_files"] if n != name]
    else:
        plan["line_item_ops"] = [o for o in plan["line_item_ops"] if o["id"] != op_id]
        plan["task_ops"] = [o for o in plan["task_ops"] if o["id"] != op_id]
    return {}


def execute_plan(submission) -> dict[str, Any]:
    if submission.state == SubmissionState.RAW:
        return {"error": "Extraction is still in progress."}
    if submission.state == SubmissionState.COMMITTED:
        return {"error": "This submission is posted."}

    plan = submission.pending_plan or empty_plan()
    if plan_count(plan) == 0:
        return {"error": "There is no pending plan to execute."}

    saved = plan["save_files"]
    if saved:
        submission.file_names = dedup(list(submission.file_names or []) + saved)
        text = " ".join([submission.raw_input or "", *(submission.file_names or [])])
        category = (submission.line_items or [{}])[0].get("category") if submission.line_items else ""
        vendor, category, total, payment = recompute_fields(submission.vendor or "", category, text)
        submission.vendor = vendor
        submission.payment_method = payment
        submission.line_items = mock_extract(vendor, category, total)

    for op in plan["line_item_ops"]:
        submission.line_items = apply_line_op(submission.line_items or [], op)

    if saved:
        submission.tasks = [t for t in (submission.tasks or []) if t.get("source") == "user"]
        submission.tasks += seed_agent_tasks(submission_context(submission))

    for op in plan["task_ops"]:
        submission.tasks = apply_task_op(submission.tasks or [], op)

    submission.pending_plan = empty_plan()
    if submission.state in (SubmissionState.EXTRACTED, SubmissionState.PENDING_CLIENT):
        SubmissionFSM.transition(submission, SubmissionState.NEEDS_REVIEW)

    _append_chat(
        submission,
        "Executed the plan. The Source of Truth, final data and action list are updated.",
    )
    return {}


def discard_plan(submission) -> dict[str, Any]:
    submission.pending_plan = empty_plan()
    _append_chat(submission, "Discarded the pending plan. Nothing was changed.")
    return {}