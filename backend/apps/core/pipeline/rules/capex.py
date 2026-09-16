from ..base import LedgerRule
from ..state import LedgerState


class CapExThresholdRule(LedgerRule):
    """Capitalize items at or above the CapEx threshold (IRS de minimis)."""

    def execute(self, state: LedgerState) -> LedgerState:
        for line in state.lines:
            if line.personal:
                continue
            if line.amount >= state.capex_threshold and line.category != "Fixed Assets":
                state.warnings.append(
                    f"Capitalized '{line.description}' (${line.amount:,.2f}) — "
                    f"meets the ${state.capex_threshold:,.2f} CapEx threshold."
                )
                line.category = "Fixed Assets"
        return state