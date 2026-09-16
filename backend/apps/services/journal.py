"""Journal construction and preview via the deterministic rule pipeline."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings

from apps.core.pipeline import LedgerPipeline, LedgerState
from apps.core.pipeline.rules import (
    CapExThresholdRule,
    DoubleEntryBalanceRule,
    JournalBuilderRule,
    PersonalExpenseRule,
)
from apps.core.pipeline.state import CREDIT, DEBIT, LedgerLineItem
from apps.services.projection import project


def _pipeline() -> LedgerPipeline:
    return LedgerPipeline([
        PersonalExpenseRule(),
        CapExThresholdRule(),
        JournalBuilderRule(),
        DoubleEntryBalanceRule(),
    ])


def build_state(submission, lines: list[dict]) -> LedgerState:
    proj = project(submission)
    return LedgerState(
        submission_id=str(submission.id),
        client_id=str(submission.client_id),
        lines=[
            LedgerLineItem(
                description=li["description"],
                amount=Decimal(str(li["amount"])),
                category=li.get("category", "Uncategorized"),
                personal=bool(li.get("personal")),
            )
            for li in lines
        ],
        vendor=proj["vendor"] or "",
        payment_method=proj["payment_method"] or "",
        capex_threshold=Decimal(str(settings.CAPEX_THRESHOLD)),
    )


def serialize(state: LedgerState) -> dict:
    lines = [
        {
            "account_code": entry.account_code,
            "account_name": entry.account_name,
            "entry_type": entry.entry_type,
            "amount": float(entry.amount),
            "description": entry.description,
        }
        for entry in state.posted_entries
    ]
    debits = sum((e.amount for e in state.posted_entries if e.entry_type == DEBIT), Decimal("0.00"))
    credits = sum((e.amount for e in state.posted_entries if e.entry_type == CREDIT), Decimal("0.00"))
    return {
        "lines": lines,
        "total_debits": float(debits),
        "total_credits": float(credits),
        "balanced": abs(debits - credits) < Decimal("0.001"),
        "warnings": state.warnings,
    }


def build(submission, lines: list[dict]) -> dict:
    state = _pipeline().process(build_state(submission, lines))
    return serialize(state)


def preview(submission) -> dict | None:
    """Preview the journal for the projected line items."""
    proj = project(submission)
    if not any(not li.get("personal") for li in proj["line_items"]):
        return None
    return build(submission, proj["line_items"])


def make_entry(submission, lines: list[dict]) -> dict:
    result = build(submission, lines)
    return {
        "id": f"je_{uuid.uuid4().hex[:8]}",
        "submission_id": str(submission.id),
        "transaction_date": date.today().isoformat(),
        "lines": result["lines"],
    }