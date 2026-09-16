"""General ledger queries (derived from posted journal entries)."""
from __future__ import annotations

from typing import Any

from apps.core.models import Submission


def _totals(entry: dict) -> tuple[float, float]:
    lines = entry.get("lines", [])
    debit = sum(line["amount"] for line in lines if line["entry_type"] == "DEBIT")
    credit = sum(line["amount"] for line in lines if line["entry_type"] == "CREDIT")
    return round(debit, 2), round(credit, 2)


def _posted() -> list[Submission]:
    return list(
        Submission.objects.exclude(journal_entry__isnull=True).select_related("client")
    )


def list_entries(client_id: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for submission in _posted():
        if client_id and str(submission.client_id) != str(client_id):
            continue
        entry = submission.journal_entry
        debit, credit = _totals(entry)
        out.append({
            "id": entry["id"],
            "submission_id": str(submission.id),
            "date": entry.get("transaction_date"),
            "client_id": str(submission.client_id),
            "client_name": submission.client.client_name if submission.client else "",
            "vendor": submission.vendor,
            "total": debit,
            "line_count": len(entry.get("lines", [])),
            "balanced": abs(debit - credit) < 0.001,
        })
    return sorted(out, key=lambda e: (e["date"] or "", e["id"]), reverse=True)


def get_entry(entry_id: str) -> dict[str, Any] | None:
    for submission in _posted():
        entry = submission.journal_entry
        if entry.get("id") != entry_id:
            continue
        debit, credit = _totals(entry)
        return {
            "id": entry["id"],
            "submission_id": str(submission.id),
            "transaction_date": entry.get("transaction_date"),
            "client_id": str(submission.client_id),
            "client_name": submission.client.client_name if submission.client else "",
            "vendor": submission.vendor,
            "payment_method": submission.payment_method,
            "lines": entry.get("lines", []),
            "total_debits": debit,
            "total_credits": credit,
            "balanced": abs(debit - credit) < 0.001,
        }
    return None