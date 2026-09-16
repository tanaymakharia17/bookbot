"""Pending-plan staging operations."""
from __future__ import annotations

import uuid
from typing import Any

from apps.core.constants import ACTION_FILE_HINTS
from apps.core.state import SubmissionState
from apps.services.projection import empty_plan, project


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