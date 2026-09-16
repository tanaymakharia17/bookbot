from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.core.state import SubmissionState as S


def sample_items():
    return [
        {"description": "Printer Paper", "qty": 1, "unit_price": 89.0, "amount": 89.0,
         "category": "Office Supplies", "personal": False},
        {"description": "Dyson Vacuum V15", "qty": 1, "unit_price": 350.0, "amount": 350.0,
         "category": "Uncategorized", "personal": False},
    ]


@override_settings(OPENROUTER_API_KEY="")
class ReviewAPITests(TestCase):
    def setUp(self):
        self.api = APIClient()
        firm = get_default_firm()
        self.client_account = ClientAccount.objects.create(firm=firm, client_name="Acme")
        self.sub = Submission.objects.create(
            client=self.client_account,
            state=S.NEEDS_REVIEW,
            vendor="Target",
            payment_method="Company Credit Card",
            raw_input="supplies + vacuum",
            line_items=sample_items(),
        )

    def test_chat_history_empty(self):
        resp = self.api.get(f"/api/v1/submissions/{self.sub.id}/chat/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_chat_stages_plan(self):
        resp = self.api.post(
            f"/api/v1/submissions/{self.sub.id}/chat/",
            {"message": "exclude the vacuum"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("plan", body["reply"].lower())
        self.sub.refresh_from_db()
        ops = self.sub.pending_plan["line_item_ops"]
        self.assertEqual(ops[0]["type"], "exclude_personal")

    def test_stage_files_proposes_completion(self):
        self.sub.state = S.BLOCKED_COMPLIANCE
        self.sub.blocker = "Missing W-8BEN-E"
        self.sub.save()
        resp = self.api.post(
            f"/api/v1/submissions/{self.sub.id}/plan/files/",
            {"files": [{"name": "acme_w-8ben.pdf", "save": True}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Request Form W-8BEN-E from foreign vendor", resp.json()["proposed"])

    def test_stage_task_add(self):
        resp = self.api.post(
            f"/api/v1/submissions/{self.sub.id}/plan/tasks/",
            {"title": "Call client"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.pending_plan["task_ops"][0]["type"], "add")

    def test_execute_plan_commits(self):
        self.api.post(
            f"/api/v1/submissions/{self.sub.id}/chat/",
            {"message": "exclude the vacuum"},
            format="json",
        )
        resp = self.api.post(f"/api/v1/submissions/{self.sub.id}/plan/execute/")
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        flags = [li["personal"] for li in self.sub.line_items]
        self.assertEqual(flags, [False, True])
        self.assertEqual(self.sub.pending_plan["line_item_ops"], [])

    def test_journal_preview_is_balanced(self):
        resp = self.api.get(f"/api/v1/submissions/{self.sub.id}/journal_preview/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["balanced"])

    def test_approve_posts_to_ledger(self):
        resp = self.api.post(f"/api/v1/submissions/{self.sub.id}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.state, S.COMMITTED)
        self.assertIsNotNone(self.sub.journal_entry)

    def test_resolve_compliance(self):
        self.sub.state = S.BLOCKED_COMPLIANCE
        self.sub.blocker = "Missing W-8BEN-E"
        self.sub.save()
        resp = self.api.post(f"/api/v1/submissions/{self.sub.id}/resolve_compliance/")
        self.assertEqual(resp.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.state, S.NEEDS_REVIEW)
        self.assertTrue(self.sub.blocker_resolved)

    def test_ledger_lists_posted_entries(self):
        self.api.post(f"/api/v1/submissions/{self.sub.id}/approve/")
        resp = self.api.get("/api/v1/ledger/")
        self.assertEqual(resp.status_code, 200)
        entries = resp.json()
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["balanced"])