from decimal import Decimal

from ..base import LedgerRule
from ..state import CREDIT, DEBIT, LedgerState

TOLERANCE = Decimal("0.001")


class DoubleEntryBalanceRule(LedgerRule):
    """Enforce sum(debits) == sum(credits)."""

    def execute(self, state: LedgerState) -> LedgerState:
        debits = sum(
            (e.amount for e in state.posted_entries if e.entry_type == DEBIT),
            Decimal("0.00"),
        )
        credits = sum(
            (e.amount for e in state.posted_entries if e.entry_type == CREDIT),
            Decimal("0.00"),
        )
        if abs(debits - credits) > TOLERANCE:
            raise ValueError(
                f"CRITICAL DOUBLE-ENTRY VIOLATION: debits (${debits:,.2f}) "
                f"do not equal credits (${credits:,.2f})."
            )
        return state