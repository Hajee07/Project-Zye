"""Day 25 Unit Tests: AI Council Foundation and Deliberation Engine.

Tests:
- Parallel multi-agent deliberation
- Partial failure recovery (one provider down, others succeed)
- Synthesis prompt generation for Gemini Master Brain
- Readiness and quorum calculations
"""

import unittest
from unittest.mock import MagicMock, patch

from zye_ai_plugins.ai_council import AICouncilEngine
from zye_ai_plugins.response_normalizer import AIResponse, AIUsage


def run_coro(coro):
    """Run an async coroutine synchronously without event loop socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


async def fake_gather(*tasks, return_exceptions=True):
    """Synchronous in-memory gather emulator for sandbox testing."""
    results = []
    for t in tasks:
        try:
            results.append(run_coro(t))
        except Exception as exc:
            results.append(exc)
    return results


class TestDay25AICouncil(unittest.TestCase):
    """Test suite for AI Council Engine."""

    def setUp(self):
        self.mock_registry = MagicMock()
        self.council = AICouncilEngine(self.mock_registry)

    def test_01_parallel_deliberation_success(self):
        """Verify concurrent multi-provider query and structured perspectives."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(**kwargs):
            return AIResponse(
                provider_id="openai",
                model="gpt-4o",
                status="success",
                content="ChatGPT recommendation: Use FastAPI for microservices.",
                usage=AIUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30, latency_ms=150.0),
            )
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(**kwargs):
            return AIResponse(
                provider_id="anthropic",
                model="claude-3-5-sonnet-20241022",
                status="success",
                content="Claude recommendation: Consider async performance and Pydantic v2.",
                usage=AIUsage(prompt_tokens=25, completion_tokens=12, total_tokens=37, latency_ms=210.0),
            )
        mock_claude.generate_response = claude_gen

        def mock_get(pid):
            if pid in ("chatgpt", "openai"):
                return mock_chatgpt
            if pid in ("claude", "anthropic"):
                return mock_claude
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            result = run_coro(self.council.deliberate(
                question="What web framework should we use?",
                providers=["chatgpt", "claude"],
                focus_area="code",
            ))

            self.assertTrue(result["success"])
            self.assertEqual(result["successful_count"], 2)
            self.assertEqual(result["total_queried"], 2)
            self.assertIn("chatgpt", result["perspectives"])
            self.assertIn("claude", result["perspectives"])

            # Check synthesis text for Gemini Master Brain
            synthesis = result["synthesis_prompt_ready"]
            self.assertIn("ChatGPT recommendation", synthesis)
            self.assertIn("Claude recommendation", synthesis)
            self.assertIn("SUPREME ARBITER INSTRUCTIONS FOR GEMINI MASTER BRAIN", synthesis)

    def test_02_partial_failure_tolerance(self):
        """Verify Council succeeds even if one provider encounters an error."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(**kwargs):
            return AIResponse(
                provider_id="openai",
                model="gpt-4o",
                status="success",
                content="ChatGPT analysis.",
                usage=AIUsage(latency_ms=100.0),
            )
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(**kwargs):
            return AIResponse(
                provider_id="anthropic",
                model="claude-3-5-sonnet",
                status="error",
                error_message="Rate limit 429",
                content="",
            )
        mock_claude.generate_response = claude_gen

        def mock_get(pid):
            if pid in ("chatgpt", "openai"):
                return mock_chatgpt
            if pid in ("claude", "anthropic"):
                return mock_claude
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            result = run_coro(self.council.deliberate(
                question="Test question",
                providers=["chatgpt", "claude"],
            ))

            self.assertTrue(result["success"])
            self.assertEqual(result["successful_count"], 1)
            self.assertEqual(result["perspectives"]["claude"]["status"], "error")
            self.assertEqual(result["perspectives"]["chatgpt"]["status"], "success")

    def test_03_council_status_readiness(self):
        """Verify council readiness check reports active members correctly."""
        p1 = MagicMock()
        p1.is_configured = True
        p1.config.enabled = True
        p1.config.default_model = "gpt-4o"

        p2 = MagicMock()
        p2.is_configured = False
        p2.config.enabled = True

        def mock_get(pid):
            if pid == "chatgpt":
                return p1
            return p2

        self.mock_registry.get_active_providers.return_value = ["chatgpt"]
        self.mock_registry.get_provider.side_effect = mock_get

        status = run_coro(self.council.get_council_status())
        self.assertTrue(status["council_ready"])
        self.assertEqual(status["active_members_count"], 1)
        self.assertEqual(status["supreme_arbiter"], "Gemini Master Brain (Voice: en-IN-NeerjaNeural)")


if __name__ == "__main__":
    unittest.main()
