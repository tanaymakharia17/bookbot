"""Review actions: approve and compliance resolution."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.core.constants import POST_LEDGER_TASK
from apps.core.fsm import SubmissionFSM
from apps.core.state import SubmissionState
from apps.services.journal import make_entry
from apps.services.plan import _append_chat
from apps.services.projection import empty_plan, plan_count


def mark_posted_task(submission) -> None:
    for task in (submission.tasks or []):
        if task.get("title") == POST_LEDGER_TASK:
            task["done"] = True


def approve(submission) -> dict[str, Any]:
    if submission.state == SubmissionState.COMMITTED:
        return {"error": "Submission has already been posted."}
    if submission.state == SubmissionState.RAW:
        return {"error": "Extraction is still in progress."}
    if submission.state == SubmissionState.BLOCKED_COMPLIANCE:
        return {"error": submission.blocker or "Submission is blocked on compliance."}
    if plan_count(submission.pending_plan) > 0:
        return {"error": "Execute or discard the pending plan before approving."}

    business = [li for li in (submission.line_items or []) if not li.get("personal")]
    if not business:
        return {"error": "No business line items remain after exclusions."}

    try:
        entry = make_entry(submission, submission.line_items)
    except ValueError as exc:
        return {"error": str(exc)}

    if submission.state == SubmissionState.EXTRACTED:
        SubmissionFSM.transition(submission, SubmissionState.NEEDS_REVIEW)
    SubmissionFSM.transition(submission, SubmissionState.COMMITTED)

    submission.journal_entry = entry
    submission.approved_at = timezone.now()
    submission.pending_plan = empty_plan()
    mark_posted_task(submission)

    total = sum(line["amount"] for line in entry["lines"] if line["entry_type"] == "DEBIT")
    _append_chat(
        submission,
        f"Posted to the ledger — {len(entry['lines'])} lines, debits = credits = ${total:,.2f}.",
    )
    return {"journal_entry": entry}