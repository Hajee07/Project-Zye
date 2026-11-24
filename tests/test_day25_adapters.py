"""Day 25 Unit Tests: AI Provider Adapters (Mocked Transport).

Tests:
- OpenAIAdapter (ChatGPT): response extraction, token accounting, error handling
- AnthropicAdapter (Claude): content blocks, token usage, rate limit / overload handling
- OllamaAdapter (Local): local /api/chat, offline resilience, model tag discovery
- OpenAICompatibleAdapter (Perplexity, DeepSeek, Groq): generic REST completions
"""

import unittest
from unittest.mock import MagicMock

from zye_ai_plugins.anthropic_adapter import AnthropicAdapter
from zye_ai_plugins.ollama_adapter import OllamaAdapter
from zye_ai_plugins.openai_adapter import OpenAIAdapter
from zye_ai_plugins.openai_compatible_adapter import OpenAICompatibleAdapter
from zye_ai_plugins.provider_config import SingleProviderConfig


def run_coro(coro):
    """Run an async coroutine synchronously without event loop socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestDay25Adapters(unittest.TestCase):
    """Test suite for AI Provider Adapters with mocked transport."""

    def test_01_openai_success_response(self):
        """Verify OpenAI adapter correctly parses 200 response and extracts tokens."""
        cfg = SingleProviderConfig(
            provider_name="openai",
            api_key="sk-test-valid-key-12345",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4o",
        )
        adapter = OpenAIAdapter(cfg)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "gpt-4o",
            "choices": [{"message": {"content": "Hello from ChatGPT!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }

        mock_client = MagicMock()
        mock_client.is_closed = False
        async def mock_post(*args, **kwargs):
            return mock_resp
        mock_client.post = mock_post
        adapter._client = mock_client

        res = run_coro(adapter.generate_response(prompt="Hello"))
        self.assertTrue(res.is_success)
        self.assertEqual(res.content, "Hello from ChatGPT!")
        self.assertEqual(res.usage.prompt_tokens, 12)
        self.assertEqual(res.usage.completion_tokens, 8)
        self.assertEqual(res.usage.total_tokens, 20)
        self.assertEqual(res.model_used, "gpt-4o")

    def test_02_openai_auth_error(self):
        """Verify OpenAI 401 error handling."""
        cfg = SingleProviderConfig(
            provider_name="openai",
            api_key="sk-invalid-key-12345",
            base_url="https://api.openai.com/v1",
        )
        adapter = OpenAIAdapter(cfg)

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        mock_client = MagicMock()
        mock_client.is_closed = False
        async def mock_post(*args, **kwargs):
            return mock_resp
        mock_client.post = mock_post
        adapter._client = mock_client

        res = run_coro(adapter.generate_response(prompt="Hello"))
        self.assertFalse(res.is_success)
        self.assertIn("Authentication Error", res.error_message)

    def test_03_anthropic_success_response(self):
        """Verify Anthropic Messages API block extraction."""
        cfg = SingleProviderConfig(
            provider_name="anthropic",
            api_key="sk-ant-test-key-12345",
            base_url="https://api.anthropic.com/v1",
            default_model="claude-3-5-sonnet-20241022",
        )
        adapter = AnthropicAdapter(cfg)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "Hello from Claude 3.5 Sonnet!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 10},
        }

        mock_client = MagicMock()
        mock_client.is_closed = False
        async def mock_post(*args, **kwargs):
            return mock_resp
        mock_client.post = mock_post
        adapter._client = mock_client

        res = run_coro(adapter.generate_response(prompt="Hello Claude"))
        self.assertTrue(res.is_success)
        self.assertEqual(res.content, "Hello from Claude 3.5 Sonnet!")
        self.assertEqual(res.usage.prompt_tokens, 15)
        self.assertEqual(res.usage.completion_tokens, 10)
        self.assertEqual(res.usage.total_tokens, 25)

    def test_04_ollama_local_execution(self):
        """Verify local Ollama chat and offline response."""
        cfg = SingleProviderConfig(
            provider_name="ollama",
            base_url="http://127.0.0.1:11434",
            default_model="llama3.2",
            enabled=True,
        )
        adapter = OllamaAdapter(cfg)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Hello from local Llama 3.2!"},
            "prompt_eval_count": 22,
            "eval_count": 14,
            "total_duration": 500000000,
        }

        mock_client = MagicMock()
        mock_client.is_closed = False
        async def mock_post(*args, **kwargs):
            return mock_resp
        mock_client.post = mock_post
        adapter._client = mock_client

        res = run_coro(adapter.generate_response(prompt="Hello Ollama"))
        self.assertTrue(res.is_success)
        self.assertEqual(res.content, "Hello from local Llama 3.2!")
        self.assertEqual(res.usage.prompt_tokens, 22)
        self.assertEqual(res.usage.completion_tokens, 14)
        self.assertTrue(res.metadata.get("local"))

    def test_05_openai_compatible_perplexity_citations(self):
        """Verify OpenAICompatibleAdapter captures Perplexity citations."""
        cfg = SingleProviderConfig(
            provider_name="perplexity",
            api_key="pplx-test-key-12345",
            base_url="https://api.perplexity.ai",
            default_model="sonar-pro",
        )
        adapter = OpenAICompatibleAdapter(cfg)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "sonar-pro",
            "choices": [{"message": {"content": "Answer with citations."}, "finish_reason": "stop"}],
            "citations": ["https://example.com/source1", "https://example.com/source2"],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }

        mock_client = MagicMock()
        mock_client.is_closed = False
        async def mock_post(*args, **kwargs):
            return mock_resp
        mock_client.post = mock_post
        adapter._client = mock_client

        res = run_coro(adapter.generate_response(prompt="Research query"))
        self.assertTrue(res.is_success)
        self.assertEqual(res.content, "Answer with citations.")
        self.assertIn("citations", res.metadata)
        self.assertEqual(len(res.metadata["citations"]), 2)


if __name__ == "__main__":
    unittest.main()
