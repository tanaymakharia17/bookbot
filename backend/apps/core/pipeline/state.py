"""Ledger pipeline data model.

Pure Python (no Django imports) so the deterministic accounting engine can be
unit-tested in isolation, per the architecture spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


DEBIT = "DEBIT"
CREDIT = "CREDIT"


@dataclass
class LedgerLineItem:
    """A single extracted line item to be classified."""

    description: str
    amount: Decimal
    category: str = "Uncategorized"
    personal: bool = False


@dataclass
class LedgerEntryDraft:
    """A proposed journal line (debit or credit)."""

    account_code: str
    account_name: str
    entry_type: str
    amount: Decimal
    description: str = ""


@dataclass
class LedgerState:
    """Carrier object threaded through the rule pipeline."""

    submission_id: str
    client_id: str
    lines: list[LedgerLineItem] = field(default_factory=list)
    vendor: str = ""
    payment_method: str = ""
    capex_threshold: Decimal = Decimal("2500.00")
    total_reimbursement_payable: Decimal = Decimal("0.00")
    posted_entries: list[LedgerEntryDraft] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)