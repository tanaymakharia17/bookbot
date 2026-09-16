"""Pipeline orchestrator (chain of responsibility)."""
from __future__ import annotations

from .base import LedgerRule
from .state import LedgerState


class LedgerPipeline:
    """Runs a sequence of ``LedgerRule``s over a ``LedgerState``."""

    def __init__(self, rules: list[LedgerRule] | None = None) -> None:
        self.rules: list[LedgerRule] = list(rules or [])

    def add_rule(self, rule: LedgerRule) -> "LedgerPipeline":
        self.rules.append(rule)
        return self

    def process(self, initial_state: LedgerState) -> LedgerState:
        current = initial_state
        for rule in self.rules:
            current = rule.execute(current)
        return current