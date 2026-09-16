"""Submission lifecycle state machine."""
from __future__ import annotations

from .state import SubmissionState

S = SubmissionState


class InvalidTransitionError(Exception):
    """Raised when a state transition is not permitted."""


#: Allowed target states for each state.
TRANSITIONS: dict[str, set[str]] = {
    S.RAW: {S.EXTRACTED},
    S.EXTRACTED: {S.NEEDS_REVIEW},
    S.NEEDS_REVIEW: {S.COMMITTED, S.PENDING_CLIENT, S.BLOCKED_COMPLIANCE},
    S.PENDING_CLIENT: {S.NEEDS_REVIEW},
    S.BLOCKED_COMPLIANCE: {S.NEEDS_REVIEW, S.COMMITTED},
    S.COMMITTED: set(),
}


class SubmissionFSM:
    """Validates and applies submission state transitions."""

    @staticmethod
    def allowed(state: str) -> set[str]:
        return set(TRANSITIONS.get(state, set()))

    @classmethod
    def can_transition(cls, current: str, target: str) -> bool:
        return target in cls.allowed(current)

    @classmethod
    def transition(cls, submission, target: str):
        if not cls.can_transition(submission.state, target):
            raise InvalidTransitionError(
                f"Cannot move submission from {submission.state} to {target}."
            )
        submission.state = target
        return submission

    @staticmethod
    def is_terminal(state: str) -> bool:
        return not TRANSITIONS.get(state, set())