from django.test import SimpleTestCase

from apps.core.fsm import InvalidTransitionError, SubmissionFSM
from apps.core.state import SubmissionState as S


class SubmissionFSMTests(SimpleTestCase):
    def test_allowed_transitions(self):
        self.assertTrue(SubmissionFSM.can_transition(S.RAW, S.EXTRACTED))
        self.assertTrue(SubmissionFSM.can_transition(S.NEEDS_REVIEW, S.COMMITTED))
        self.assertTrue(SubmissionFSM.can_transition(S.BLOCKED_COMPLIANCE, S.NEEDS_REVIEW))

    def test_disallowed_transitions(self):
        self.assertFalse(SubmissionFSM.can_transition(S.RAW, S.COMMITTED))
        self.assertFalse(SubmissionFSM.can_transition(S.EXTRACTED, S.BLOCKED_COMPLIANCE))

    def test_committed_is_terminal(self):
        self.assertTrue(SubmissionFSM.is_terminal(S.COMMITTED))
        self.assertFalse(SubmissionFSM.is_terminal(S.NEEDS_REVIEW))

    def test_transition_raises_on_invalid(self):
        class Dummy:
            state = S.RAW

        with self.assertRaises(InvalidTransitionError):
            SubmissionFSM.transition(Dummy(), S.COMMITTED)

    def test_transition_updates_state(self):
        class Dummy:
            state = S.RAW

        obj = Dummy()
        SubmissionFSM.transition(obj, S.EXTRACTED)
        self.assertEqual(obj.state, S.EXTRACTED)