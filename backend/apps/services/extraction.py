"""Deterministic extraction heuristics (placeholder for the VLM extractor)."""
from __future__ import annotations

import logging
import re
from typing import Any

from apps.core.constants import VENDOR_HINTS
from apps.core.fsm import SubmissionFSM
from apps.core.state import SubmissionState
from apps.services.sot import build_sot_markdown
from apps.services.task_seeding import seed_agent_tasks

logger = logging.getLogger(__name__)


def extract_amount(text: str) -> float | None:
    """Return the largest dollar-looking amount found in the text."""
    matches = re.findall(r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text)
    values: list[float] = []
    for match in matches:
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    values = [v for v in values if v >= 1]
    return max(values) if values else None


def detect_vendor(text: str) -> tuple[str, str]:
    """Return (vendor_name, category) guessed from the text."""
    lowered = text.lower()
    for hint, (vendor, category) in VENDOR_HINTS.items():
        if hint in lowered:
            return vendor, category
    return "Unknown Vendor", "Uncategorized"


def mock_extract(vendor: str, category: str, total: float) -> list[dict]:
    """Split a total into two placeholder line items."""
    first = round(total * 0.88, 2)
    second = round(total - first, 2)
    return [
        {"description": f"{vendor} — Primary item", "qty": 1, "unit_price": first,
         "amount": first, "category": category, "personal": False},
        {"description": f"{vendor} — Accessory / add-on", "qty": 1, "unit_price": second,
         "amount": second, "category": category, "personal": False},
    ]


def recompute_fields(
    fallback_vendor: str, fallback_category: str, text: str
) -> tuple[str, str, float, str]:
    """Recompute vendor/category/total/payment, keeping the prior vendor if undetected."""
    vendor, category = detect_vendor(text)
    if vendor == "Unknown Vendor" and fallback_vendor:
        vendor = fallback_vendor
        category = fallback_category or "Uncategorized"
    total = extract_amount(text) or 1250.00
    payment = "Cash" if "cash" in text.lower() else "Company Credit Card"
    return vendor, category, total, payment


def submission_context(submission) -> dict[str, Any]:
    """A plain mapping used by task seeding / projection."""
    return {
        "state": submission.state,
        "vendor": submission.vendor,
        "payment_method": submission.payment_method,
        "raw_input": submission.raw_input,
        "line_items": submission.line_items or [],
    }


def initial_chat(submission) -> list[dict[str, str]]:
    items = submission.line_items or []
    business = sum(li["amount"] for li in items if not li.get("personal"))
    personal = [li for li in items if li.get("personal")]
    personal_note = (
        f"\n\n⚠️ I flagged {len(personal)} item(s) that look personal and excluded them "
        f"from the reimbursement total."
        if personal else ""
    )
    return [
        {"role": "agent", "content": f"Files received: {', '.join(submission.file_names or []) or '—'}."},
        {
            "role": "agent",
            "content": (
                f"I've extracted **{len(items)} line items** from the "
                f"{submission.vendor or 'document'} file(s), totaling **${business:,.2f}**."
                f"{personal_note}\n\n"
                f"Tell me what to change and I'll add it to the pending plan — or attach more "
                f"documents with the paperclip. Nothing is applied until you execute the plan."
            ),
        },
    ]


def ensure_tasks(submission, save: bool = True) -> bool:
    """Seed the agent checklist for a non-RAW submission that has none."""
    if submission.state == SubmissionState.RAW or submission.tasks:
        return False
    submission.tasks = seed_agent_tasks(submission_context(submission))
    if submission.state == SubmissionState.COMMITTED:
        for task in submission.tasks:
            if task["title"] == "Post the journal entry to the ledger":
                task["done"] = True
    if save:
        submission.save(update_fields=["tasks", "updated_at"])
    return True


def extract(submission, save: bool = True):
    """Extract a RAW submission: real VLM read when files exist, else stub."""
    from apps.services import storage, vlm

    if submission.state != SubmissionState.RAW:
        ensure_tasks(submission, save=save)
        return submission

    paths = [
        storage.submission_dir(submission.id) / name
        for name in (submission.file_names or [])
    ]
    paths = [p for p in paths if p.exists()]

    data = None
    vlm_error: Exception | None = None
    if paths:
        try:
            data = vlm.read_documents(paths)
        except Exception as exc:  # noqa: BLE001 - fall back to the stub on any VLM error
            vlm_error = exc
            logger.exception("VLM extraction failed for submission %s", submission.id)

    items = vlm.normalize_line_items(data) if data else []
    used_fallback = False
    if items:
        submission.vendor = (data.get("vendor") or "Unknown Vendor").strip() or "Unknown Vendor"
        submission.payment_method = vlm.normalize_payment(data.get("payment_method") or "")
        submission.line_items = items
    else:
        used_fallback = True
        text = " ".join([submission.raw_input or "", *(submission.file_names or [])])
        vendor, category, total, payment = recompute_fields(submission.vendor or "", "", text)
        submission.vendor = vendor
        submission.payment_method = payment
        submission.line_items = mock_extract(vendor, category, total)

    submission.tasks = seed_agent_tasks(submission_context(submission))
    submission.chat_messages = initial_chat(submission)
    if used_fallback and paths:
        reason = f"{type(vlm_error).__name__}" if vlm_error else "the model returned no usable data"
        submission.chat_messages.append({
            "role": "agent",
            "content": (
                f"⚠️ I couldn't read the documents with the AI model ({reason}), "
                "so I used a basic fallback. Please review the line items carefully."
            ),
        })
    submission.sot_markdown = build_sot_markdown(submission)

    SubmissionFSM.transition(submission, SubmissionState.EXTRACTED)
    if save:
        submission.save()
    return submission