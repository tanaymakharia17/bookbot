from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.core.state import SubmissionState


class SubmissionAPITests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.firm = get_default_firm()
        self.client_account = ClientAccount.objects.create(
            firm=self.firm, client_name="Acme"
        )

    def _create(self, **overrides):
        payload = {
            "client_id": str(self.client_account.id),
            "file_names": ["receipt.pdf"],
            "raw_input": "Bought a laptop",
        }
        payload.update(overrides)
        return self.api.post("/api/v1/submissions/", payload, format="json")

    def test_list_is_empty(self):
        response = self.api.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_returns_raw_submission(self):
        response = self._create()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["state"], SubmissionState.RAW)
        self.assertEqual(body["file_names"], ["receipt.pdf"])
        self.assertTrue(Submission.objects.filter(id=body["id"]).exists())

    def test_create_rejects_unknown_client(self):
        response = self._create(client_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 400)
        self.assertIn("client_id", response.json())

    def test_create_requires_files(self):
        response = self._create(file_names=[])
        self.assertEqual(response.status_code, 400)
        self.assertIn("file_names", response.json())

    def test_list_filters_by_client(self):
        Submission.objects.create(client=self.client_account)
        response = self.api.get(f"/api/v1/submissions/?client={self.client_account.id}")
        self.assertEqual(len(response.json()), 1)

    def test_list_rejects_bad_uuid_gracefully(self):
        response = self.api.get("/api/v1/submissions/?client=not-a-uuid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_detail_returns_full_workpaper(self):
        submission = Submission.objects.create(client=self.client_account)
        response = self.api.get(f"/api/v1/submissions/{submission.id}/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        for field in ("sot_markdown", "line_items", "tasks", "pending_plan", "journal_entry"):
            self.assertIn(field, body)

    def test_detail_missing_is_404(self):
        response = self.api.get("/api/v1/submissions/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, 404)