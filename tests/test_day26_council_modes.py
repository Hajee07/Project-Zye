"""Day 26 Unit Tests: AI Council Modes, Multi-Round Deliberation, and Gemini Judge.

Tests:
- QUICK_COUNCIL mode execution
- DEEP_COUNCIL mode with cross-AI critique
- LOCAL_COUNCIL mode (100% offline, privacy-first)
- Partial failure resilience (one provider down, other succeeds)
- Gemini Supreme Arbiter synthesis and verdict categories
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


class TestDay26CouncilModes(unittest.TestCase):
    """Test suite for AI Council Operating Modes and Multi-Round Deliberation."""

    def setUp(self):
        self.mock_registry = MagicMock()
        self.council = AICouncilEngine(self.mock_registry)

    def test_01_quick_council_success(self):
        """Verify QUICK_COUNCIL executes single-round parallel comparison with Gemini handoff."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(**kwargs):
            return AIResponse(
                provider_id="chatgpt",
                model="gpt-4o",
                status="success",
                content="I recommend Solution A: FastAPI microservices with Redis cache.",
                usage=AIUsage(prompt_tokens=20, completion_tokens=15, total_tokens=35, latency_ms=110.0),
            )
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(**kwargs):
            return AIResponse(
                provider_id="claude",
                model="claude-3-5-sonnet",
                status="success",
                content="I recommend Solution B: Modular monolith with PostgreSQL.",
                usage=AIUsage(prompt_tokens=25, completion_tokens=18, total_tokens=43, latency_ms=140.0),
            )
        mock_claude.generate_response = claude_gen

        def mock_get(pid):
            if pid == "chatgpt":
                return mock_chatgpt
            if pid == "claude":
                return mock_claude
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            res = run_coro(self.council.run_quick_council(question="What architecture should we use?"))

            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["mode"], "QUICK")
            self.assertEqual(res["successful_count"], 2)
            self.assertIn("synthesis_prompt_ready", res)
            self.assertIn("Gemini Master Brain", res["synthesis_prompt_ready"])
            self.assertIn("final_decision", res)
            self.assertIn(res["final_decision"]["verdict_category"], ("RECOMMENDED_SOLUTION_A", "RECOMMENDED_SOLUTION_B", "HYBRID_SOLUTION"))

    def test_02_deep_council_cross_critique(self):
        """Verify DEEP_COUNCIL runs cross-critique and decision ranking."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(prompt, **kwargs):
            if "critique the peer proposals" in prompt:
                return AIResponse(provider_id="chatgpt", model="gpt-4o", status="success", content="Claude's monolith lacks horizontal scale.")
            return AIResponse(provider_id="chatgpt", model="gpt-4o", status="success", content="Proposal A: Microservices.")
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(prompt, **kwargs):
            if "critique the peer proposals" in prompt:
                return AIResponse(provider_id="claude", model="claude-3-5-sonnet", status="success", content="ChatGPT's microservices add network latency.")
            return AIResponse(provider_id="claude", model="claude-3-5-sonnet", status="success", content="Proposal B: Monolith.")
        mock_claude.generate_response = claude_gen

        def mock_get(pid):
            if pid == "chatgpt":
                return mock_chatgpt
            if pid == "claude":
                return mock_claude
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            res = run_coro(self.council.run_deep_council(
                question="Architecture design",
                max_rounds=2,
                priority_mode="balanced",
            ))

            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["mode"], "DEEP_COUNCIL")
            self.assertIn("cross_critiques", res)
            self.assertIn("chatgpt", res["cross_critiques"])
            self.assertIn("claude", res["cross_critiques"])
            self.assertIn("evaluation", res)
            self.assertGreaterEqual(len(res["evaluation"]["ranked_solutions"]), 2)

    def test_03_local_council_privacy_mode(self):
        """Verify LOCAL_COUNCIL restricts queries exclusively to local Ollama and bars external calls."""
        mock_ollama = MagicMock()
        async def ollama_gen(**kwargs):
            return AIResponse(
                provider_id="ollama",
                model="llama3.2",
                status="success",
                content="Local analysis from Llama 3.2: Keep data in local SQLite.",
                usage=AIUsage(latency_ms=80.0),
            )
        mock_ollama.generate_response = ollama_gen

        def mock_get(pid):
            if pid == "ollama":
                return mock_ollama
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            res = run_coro(self.council.run_ai_council(
                question="Private offline query",
                privacy_mode=True,
            ))

            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["mode"], "LOCAL_COUNCIL")
            self.assertEqual(res["total_queried"], 1)
            self.assertEqual(res["participants"][0]["provider_id"], "ollama")

    def test_04_partial_failure_resilience(self):
        """Verify Council recovers and completes when one provider fails."""
        mock_chatgpt = MagicMock()
        async def chatgpt_gen(**kwargs):
            return AIResponse(provider_id="chatgpt", model="gpt-4o", status="success", content="Valid proposal.")
        mock_chatgpt.generate_response = chatgpt_gen

        mock_claude = MagicMock()
        async def claude_gen(**kwargs):
            return AIResponse(provider_id="claude", model="claude-3-5-sonnet", status="error", error_message="503 Service Unavailable")
        mock_claude.generate_response = claude_gen

        def mock_get(pid):
            if pid == "chatgpt":
                return mock_chatgpt
            if pid == "claude":
                return mock_claude
            return None

        self.mock_registry.get_provider.side_effect = mock_get

        with patch("asyncio.gather", side_effect=fake_gather):
            res = run_coro(self.council.run_quick_council(question="Test question"))
            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["successful_count"], 1)
            self.assertEqual(res["participants"][1]["status"], "error")


if __name__ == "__main__":
    unittest.main()
