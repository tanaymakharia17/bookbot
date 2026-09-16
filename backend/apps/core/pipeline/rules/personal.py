from decimal import Decimal

from ..base import LedgerRule
from ..state import LedgerState


class PersonalExpenseRule(LedgerRule):
    """Exclude personal items and total the reimbursable amount."""

    def execute(self, state: LedgerState) -> LedgerState:
        total = Decimal("0.00")
        for line in state.lines:
            if line.personal:
                state.warnings.append(
                    f"Excluded personal item '{line.description}' (${line.amount:,.2f})."
                )
            else:
                total += line.amount
        state.total_reimbursement_payable = total
        return state