from django.test import TestCase, override_settings

from apps.agents.tools import dispatch_tool
from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.core.state import SubmissionState as S
from apps.services.projection import project


def sample_items():
    return [
        {"description": "Printer Paper", "qty": 1, "unit_price": 89.0, "amount": 89.0,
         "category": "Office Supplies", "personal": False},
        {"description": "Dyson Vacuum V15", "qty": 1, "unit_price": 350.0, "amount": 350.0,
         "category": "Uncategorized", "personal": False},
    ]


class ToolDispatchTests(TestCase):
    def setUp(self):
        firm = get_default_firm()
        client = ClientAccount.objects.create(firm=firm, client_name="Acme")
        self.sub = Submission.objects.create(
            client=client,
            state=S.NEEDS_REVIEW,
            vendor="Target",
            line_items=sample_items(),
        )

    def test_add_line_item_stages_and_projects(self):
        label, observation = dispatch_tool(
            self.sub, "add_line_item",
            {"description": "Sales Tax", "amount": 33.30, "category": "Taxes"},
        )
        self.assertIsNotNone(label)
        self.assertIn("Sales Tax", observation)
        self.assertEqual(self.sub.pending_plan["line_item_ops"][0]["type"], "add_line_item")
        descriptions = [li["description"] for li in project(self.sub)["line_items"]]
        self.assertIn("Sales Tax", descriptions)

    def test_update_line_item(self):
        dispatch_tool(self.sub, "update_line_item", {"target": "Printer Paper", "amount": 99.0})
        lines = {li["description"]: li for li in project(self.sub)["line_items"]}
        self.assertEqual(lines["Printer Paper"]["amount"], 99.0)

    def test_remove_line_item(self):
        dispatch_tool(self.sub, "remove_line_item", {"target": "dyson vacuum v15"})
        descriptions = [li["description"] for li in project(self.sub)["line_items"]]
        self.assertNotIn("Dyson Vacuum V15", descriptions)

    def test_exclude_personal_still_works(self):
        label, _ = dispatch_tool(self.sub, "exclude_personal_items", {"descriptions": ["Dyson Vacuum V15"]})
        self.assertIsNotNone(label)
        flags = {li["description"]: li["personal"] for li in project(self.sub)["line_items"]}
        self.assertTrue(flags["Dyson Vacuum V15"])

    @override_settings(OPENROUTER_API_KEY="")
    def test_inspect_document_missing_file(self):
        label, observation = dispatch_tool(
            self.sub, "inspect_document", {"file": "nope.pdf", "question": "tax?"}
        )
        self.assertIsNone(label)
        self.assertIn("not found", observation.lower())

    def test_unknown_tool(self):
        label, observation = dispatch_tool(self.sub, "does_not_exist", {})
        self.assertIsNone(label)
        self.assertIn("Unknown tool", observation)