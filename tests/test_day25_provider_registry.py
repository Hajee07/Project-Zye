"""Day 25 Unit Tests: AI Provider Registry, Configuration, and Security.

Tests:
- Configuration parsing from TOML and defaults
- Provider registration and alias resolution (chatgpt -> openai, claude -> anthropic)
- SSRF security protection (private IP blocking, HTTPS enforcement, loopback isolation)
- Metadata masking of sensitive API keys
- Custom provider dynamic registration
"""

import unittest
from unittest.mock import patch

from zye_ai_plugins.plugin_security import mask_secret, sanitize_prompt, validate_endpoint_url
from zye_ai_plugins.provider_config import AIPluginMasterConfig, SingleProviderConfig, load_ai_plugins_config
from zye_ai_plugins.provider_registry import ProviderRegistry, get_provider_registry


class TestDay25ProviderRegistry(unittest.TestCase):
    """Test suite for Day 25 Provider Registry and Configuration."""

    def setUp(self):
        self.master_cfg = AIPluginMasterConfig()
        self.registry = ProviderRegistry(self.master_cfg)

    def test_01_alias_resolution(self):
        """Verify chatgpt resolves to openai and claude resolves to anthropic."""
        openai_p = self.registry.get_provider("openai")
        chatgpt_p = self.registry.get_provider("chatgpt")
        self.assertIsNotNone(openai_p)
        self.assertIs(openai_p, chatgpt_p)

        anthropic_p = self.registry.get_provider("anthropic")
        claude_p = self.registry.get_provider("claude")
        self.assertIsNotNone(anthropic_p)
        self.assertIs(anthropic_p, claude_p)

    def test_02_ollama_provider_registered(self):
        """Verify local Ollama provider exists and allows loopback."""
        ollama_p = self.registry.get_provider("ollama")
        self.assertIsNotNone(ollama_p)
        self.assertTrue(getattr(ollama_p, "allow_loopback", False))

    def test_03_ssrf_blocking_private_ips(self):
        """Verify SSRF validator blocks private subnets and non-HTTPS endpoints."""
        # 192.168.x.x
        safe, err = validate_endpoint_url("https://192.168.1.1/v1/chat")
        self.assertFalse(safe)
        self.assertIn("private IP", err)

        # 10.x.x.x
        safe, err = validate_endpoint_url("https://10.0.0.5/v1")
        self.assertFalse(safe)
        self.assertIn("private IP", err)

        # 172.16.x.x
        safe, err = validate_endpoint_url("https://172.20.1.1/v1")
        self.assertFalse(safe)

        # Non-HTTPS for cloud provider
        safe, err = validate_endpoint_url("http://api.openai.com/v1")
        self.assertFalse(safe)
        self.assertIn("HTTPS", err)

        # Valid HTTPS public URL
        safe, err = validate_endpoint_url("https://api.openai.com/v1")
        self.assertTrue(safe)
        self.assertEqual(err, "")

    def test_04_ssrf_loopback_isolation(self):
        """Verify loopback is blocked for external providers, allowed only when specified."""
        safe_blocked, _ = validate_endpoint_url("http://127.0.0.1:11434", allow_loopback=False)
        self.assertFalse(safe_blocked)

        safe_allowed, _ = validate_endpoint_url("http://127.0.0.1:11434", allow_loopback=True)
        self.assertTrue(safe_allowed)

    def test_05_secret_masking(self):
        """Verify sensitive credentials are never displayed in plaintext."""
        self.assertEqual(mask_secret(""), "[NOT_CONFIGURED]")
        self.assertEqual(mask_secret(None), "[NOT_CONFIGURED]")
        self.assertEqual(mask_secret("short"), "****")
        masked = mask_secret("sk-proj-1234567890abcdef1234567890")
        self.assertTrue(masked.startswith("sk-..."))
        self.assertTrue(masked.endswith("7890"))
        self.assertNotIn("1234567890abcdef", masked)

    def test_06_prompt_sanitization(self):
        """Verify API keys are automatically redacted from outbound prompts."""
        raw = "Analyze this error with key sk-proj-1234567890abcdef1234567890 and Gemini AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
        cleaned = sanitize_prompt(raw)
        self.assertNotIn("sk-proj-1234567890abcdef1234567890", cleaned)
        self.assertNotIn("AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6", cleaned)
        self.assertIn("[REDACTED_API_KEY]", cleaned)


    def test_07_custom_provider_registration(self):
        """Verify dynamic registration of custom AI provider with SSRF validation."""
        # Malicious registration attempt
        bad_res = self.registry.register_custom_provider(
            name="evil_ai",
            base_url="http://192.168.1.50/api",
        )
        self.assertFalse(bad_res["success"])
        self.assertIn("Security validation failed", bad_res["error"])

        # Legitimate registration
        good_res = self.registry.register_custom_provider(
            name="research_ai",
            base_url="https://api.research-lab.org/v1",
            api_key="test-key-123",
            default_model="custom-v1",
        )
        self.assertTrue(good_res["success"])
        custom_p = self.registry.get_provider("research_ai")
        self.assertIsNotNone(custom_p)
        self.assertEqual(custom_p.config.default_model, "custom-v1")

    def test_08_singleton_registry(self):
        """Verify get_provider_registry returns persistent singleton instance."""
        reg1 = get_provider_registry()
        reg2 = get_provider_registry()
        self.assertIs(reg1, reg2)


if __name__ == "__main__":
    unittest.main()
