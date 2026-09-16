from __future__ import annotations

from decimal import Decimal

from ...accounts import CATEGORY_ACCOUNTS, DEFAULT_PAYMENT_ACCOUNT, PAYMENT_ACCOUNTS
from ..base import LedgerRule
from ..state import CREDIT, DEBIT, LedgerEntryDraft, LedgerState


class JournalBuilderRule(LedgerRule):
    """Build double-entry journal lines from the classified line items.

    Business lines become debits (by category); the total becomes a single
    credit against the payment account.
    """

    def execute(self, state: LedgerState) -> LedgerState:
        entries: list[LedgerEntryDraft] = []
        debit_total = Decimal("0.00")

        for line in state.lines:
            if line.personal:
                continue
            code, name = CATEGORY_ACCOUNTS.get(
                line.category, CATEGORY_ACCOUNTS["Uncategorized"]
            )
            entries.append(
                LedgerEntryDraft(
                    account_code=code,
                    account_name=name,
                    entry_type=DEBIT,
                    amount=line.amount,
                    description=line.description,
                )
            )
            debit_total += line.amount

        pay_code, pay_name = PAYMENT_ACCOUNTS.get(
            state.payment_method, DEFAULT_PAYMENT_ACCOUNT
        )
        entries.append(
            LedgerEntryDraft(
                account_code=pay_code,
                account_name=pay_name,
                entry_type=CREDIT,
                amount=debit_total,
                description=f"Payment — {state.vendor or 'vendor'}",
            )
        )

        state.posted_entries = entries
        return state