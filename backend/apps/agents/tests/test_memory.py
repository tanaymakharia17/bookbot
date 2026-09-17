from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import ClientAccount, Submission
from apps.core.services import get_default_firm
from apps.core.state import SubmissionState as S
from apps.services import agent


def fake_completion(content: str = "ok", total_tokens: int = 123):
    usage = MagicMock()
    usage.total_tokens = total_tokens
    message = MagicMock()
    message.content = content
    message.tool_calls = []
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


@override_settings(
    OPENROUTER_API_KEY="test-key",
    AGENT_CONTEXT_MAX_TOKENS=60000,
    AGENT_SUBMISSION_TOKEN_BUDGET=300000,
)
class ChatMemoryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        firm = get_default_firm()
        client = ClientAccount.objects.create(firm=firm, client_name="Acme")
        self.sub = Submission.objects.create(
            client=client,
            state=S.NEEDS_REVIEW,
            vendor="Target",
            document_context=[{"file": "receipt.pdf", "text": "LINE " * 1000}],
            chat_messages=[
                {"role": "cpa" if i % 2 == 0 else "agent", "content": f"message {i}"}
                for i in range(20)
            ],
        )

    @patch("openai.OpenAI")
    def test_full_history_and_document_text_are_sent(self, mock_openai):
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_completion()

        agent.respond(self.sub, "hello")

        messages = client.chat.completions.create.call_args.kwargs["messages"]
        joined = " ".join(str(m.get("content")) for m in messages)
        self.assertIn("message 0", joined)       # would be dropped by a last-10 window
        self.assertIn("LINE LINE LINE", joined)  # full document text, not truncated
        self.assertEqual(messages[-1]["content"], "hello")

    @patch("openai.OpenAI")
    def test_tokens_used_accumulates(self, mock_openai):
        client = mock_openai.return_value
        client.chat.completions.create.return_value = fake_completion(total_tokens=500)

        agent.respond(self.sub, "hi")

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tokens_used, 500)

    @override_settings(AGENT_SUBMISSION_TOKEN_BUDGET=100)
    @patch("openai.OpenAI")
    def test_budget_exhausted_blocks_call(self, mock_openai):
        self.sub.tokens_used = 150
        self.sub.save(update_fields=["tokens_used"])
        client = mock_openai.return_value

        with self.assertRaises(agent.ContextLimitReached):
            agent.respond(self.sub, "hi")

        client.chat.completions.create.assert_not_called()

    @override_settings(AGENT_CONTEXT_MAX_TOKENS=100)
    @patch("openai.OpenAI")
    def test_context_too_large_blocks_call(self, mock_openai):
        client = mock_openai.return_value

        with self.assertRaises(agent.ContextLimitReached):
            agent.respond(self.sub, "hi")

        client.chat.completions.create.assert_not_called()

    @override_settings(AGENT_SUBMISSION_TOKEN_BUDGET=100)
    @patch("openai.OpenAI")
    def test_chat_endpoint_reports_limit(self, mock_openai):
        self.sub.tokens_used = 150
        self.sub.save(update_fields=["tokens_used"])

        resp = self.api.post(
            f"/api/v1/submissions/{self.sub.id}/chat/",
            {"message": "hi"},
            format="json",
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("limit_reached"))
        self.sub.refresh_from_db()
        self.assertTrue(self.sub.chat_messages[-1]["content"].startswith("⚠️"))
        self.assertEqual(self.sub.chat_messages[-2]["content"], "hi")