"""Day 27 Unit Tests: AI Council Integration, Failover & Gemini Preservation.

Tests:
- Council deliberation leverages resilience and bulkhead isolation
- Graceful degradation: when a provider circuit is OPEN or fails, Council preserves successful responses
- Failed participant remains recorded as failed (never fabricated as success)
- Gemini Master Brain remains the sole, unchallenged Supreme Arbiter
"""

import unittest
from unittest.mock import MagicMock, patch

from zye_ai_plugins.ai_council import AICouncilEngine
from zye_ai_plugins.resilience import STATE_OPEN, get_circuit_breaker
from zye_ai_plugins.response_normalizer import AIResponse, AIUsage


def run_coro(coro):
    """Run an async coroutine synchronously without creating a Windows Proactor loopback socket."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError(f"Coroutine {coro} yielded unexpectedly")


async def fake_gather(*tasks, **kwargs):
    """Emulate asyncio.gather synchronously by driving task coroutines in sequence."""
    results = []
    for t in tasks:
        try:
            results.append(run_coro(t))
        except Exception as exc:
            results.append(exc)
    return results


class TestDay27CouncilAndFailover(unittest.TestCase):
    """Test suite for Council resilience and Gemini Master Brain preservation."""

    def setUp(self):
        self.mock_registry = MagicMock()
        self.council = AICouncilEngine(registry=self.mock_registry)

    def test_01_council_handles_degraded_provider(self):
        """Verify Council completes successfully when one provider encounters an error."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(**kwargs):
            return AIResponse(
                provider_id="chatgpt",
                model="gpt-4o",
                status="success",
                content="ChatGPT recommendation: Modular monolith.",
                usage=AIUsage(latency_ms=110.0),
            )
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(**kwargs):
            return AIResponse(
                provider_id="claude",
                model="claude-3-5-sonnet",
                status="error",
                error_message="HTTP 503 Service Unavailable",
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
            res = run_coro(self.council.run_quick_council(question="What architecture should we use?"))

            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["successful_count"], 1)
            # Verify failed provider is recorded accurately as failed
            p_map = {p["provider_id"]: p for p in res["participants"]}
            self.assertEqual(p_map["chatgpt"]["status"], "success")
            self.assertEqual(p_map["claude"]["status"], "error")

            # Verify Gemini Master Brain remains the Supreme Arbiter
            self.assertIn("SUPREME ARBITER INSTRUCTIONS FOR GEMINI MASTER BRAIN", res["synthesis_prompt_ready"])
            self.assertEqual(res["final_decision"]["supreme_arbiter"], "Gemini Master Brain (Authoritative Verdict Ready)")

    def test_02_circuit_breaker_blocks_before_council_dispatch(self):
        """Verify an OPEN circuit prevents network calls for the failing provider."""
        cb = get_circuit_breaker()
        cb.trip_circuit("claude", reason="Repeated 503 failures")
        self.assertEqual(cb.get_circuit_state("claude"), STATE_OPEN)

        permitted, reason = cb.check_permission("claude")
        self.assertFalse(permitted)
        self.assertIn("OPEN", reason)

        # Reset after test
        cb.reset_circuit("claude")


if __name__ == "__main__":
    unittest.main()
