"""SOLID interface for deterministic ledger rules."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .state import LedgerState


class LedgerRule(ABC):
    """A single deterministic accounting rule."""

    @abstractmethod
    def execute(self, state: LedgerState) -> LedgerState:
        """Process the state and enforce one rule, returning the state."""
        raise NotImplementedError