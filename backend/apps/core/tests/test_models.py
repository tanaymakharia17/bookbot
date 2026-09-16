from django.test import TestCase

from apps.core.models import ClientAccount, CpaFirm, Submission
from apps.core.state import SubmissionState


class SubmissionModelTests(TestCase):
    def setUp(self):
        self.firm = CpaFirm.objects.create(firm_name="Test Firm")
        self.client = ClientAccount.objects.create(firm=self.firm, client_name="Acme")

    def test_defaults(self):
        submission = Submission.objects.create(client=self.client)

        self.assertEqual(submission.state, SubmissionState.RAW)
        self.assertEqual(submission.file_names, [])
        self.assertEqual(submission.reference_files, [])
        self.assertEqual(submission.line_items, [])
        self.assertEqual(submission.tasks, [])
        self.assertEqual(submission.pending_plan, {})
        self.assertIsNone(submission.journal_entry)
        self.assertIsNone(submission.approved_at)

    def test_str_includes_client_and_state(self):
        submission = Submission.objects.create(client=self.client, vendor="Apple")
        self.assertIn("Acme", str(submission))

    def test_client_delete_cascades(self):
        Submission.objects.create(client=self.client)
        self.client.delete()
        self.assertEqual(Submission.objects.count(), 0)

    def test_ordering_is_newest_first(self):
        first = Submission.objects.create(client=self.client, vendor="First")
        second = Submission.objects.create(client=self.client, vendor="Second")
        self.assertEqual(list(Submission.objects.all()), [second, first])