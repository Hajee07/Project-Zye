"""Dynamic AI Provider Registry for Zye AI Multi-AI Plugin Hub.

Manages lifecycle, configuration, instantiation, and discovery of all AI providers:
- ChatGPT (OpenAI)
- Claude (Anthropic)
- Local Ollama
- Perplexity
- DeepSeek
- Groq
- OpenRouter
- Custom user endpoints
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .anthropic_adapter import AnthropicAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .openai_compatible_adapter import OpenAICompatibleAdapter
from .plugin_security import mask_secret, validate_endpoint_url
from .provider_base import BaseAIProvider
from .provider_config import AIPluginMasterConfig, SingleProviderConfig, load_master_config

logger = logging.getLogger("zye.ai_plugins.registry")


class ProviderRegistry:
    """Central registry and lifecycle manager for all AI provider adapters."""

    def __init__(self, config: Optional[AIPluginMasterConfig] = None):
        self.config = config or load_master_config()
        self._providers: Dict[str, BaseAIProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Instantiate adapters based on configuration."""
        # 1. OpenAI / ChatGPT
        openai_cfg = self.config.get_provider("openai")
        if openai_cfg:
            openai_cfg.provider_name = openai_cfg.provider_name or "openai"
            self._providers["openai"] = OpenAIAdapter(openai_cfg)
            self._providers["chatgpt"] = self._providers["openai"]

        # 2. Anthropic / Claude
        anthropic_cfg = self.config.get_provider("anthropic")
        if anthropic_cfg:
            anthropic_cfg.provider_name = anthropic_cfg.provider_name or "anthropic"
            self._providers["anthropic"] = AnthropicAdapter(anthropic_cfg)
            self._providers["claude"] = self._providers["anthropic"]

        # 3. Local Ollama
        ollama_cfg = self.config.get_provider("ollama")
        if ollama_cfg:
            ollama_cfg.provider_name = ollama_cfg.provider_name or "ollama"
            self._providers["ollama"] = OllamaAdapter(ollama_cfg)

        # 4. Perplexity
        perplexity_cfg = self.config.get_provider("perplexity")
        if perplexity_cfg:
            perplexity_cfg.provider_name = perplexity_cfg.provider_name or "perplexity"
            self._providers["perplexity"] = OpenAICompatibleAdapter(perplexity_cfg)

        # 5. DeepSeek
        deepseek_cfg = self.config.get_provider("deepseek")
        if deepseek_cfg:
            deepseek_cfg.provider_name = deepseek_cfg.provider_name or "deepseek"
            self._providers["deepseek"] = OpenAICompatibleAdapter(deepseek_cfg)

        # 6. Groq
        groq_cfg = self.config.get_provider("groq")
        if groq_cfg:
            groq_cfg.provider_name = groq_cfg.provider_name or "groq"
            self._providers["groq"] = OpenAICompatibleAdapter(groq_cfg)

        # 7. OpenRouter
        openrouter_cfg = self.config.get_provider("openrouter")
        if openrouter_cfg:
            openrouter_cfg.provider_name = openrouter_cfg.provider_name or "openrouter"
            self._providers["openrouter"] = OpenAICompatibleAdapter(openrouter_cfg)

        # 8. Custom Provider
        custom_cfg = self.config.get_provider("custom")
        if custom_cfg:
            custom_cfg.provider_name = custom_cfg.provider_name or "custom"
            self._providers["custom"] = OpenAICompatibleAdapter(custom_cfg)

        logger.info("Initialized %d AI provider instances in registry.", len(self._providers))

    def get_provider(self, provider_id: str) -> Optional[BaseAIProvider]:
        """Lookup provider instance by ID or alias."""
        return self._providers.get(provider_id.lower().strip())

    def get_active_providers(self) -> List[str]:
        """List provider IDs that are enabled and configured."""
        active = []
        seen = set()
        for pid, provider in self._providers.items():
            if id(provider) in seen:
                continue
            seen.add(id(provider))
            if provider.is_configured and provider.config.enabled:
                active.append(pid)
        return sorted(active)

    def list_all_providers(self) -> List[Dict[str, Any]]:
        """List metadata for all known providers."""
        results = []
        seen = set()

        for pid, provider in self._providers.items():
            if id(provider) in seen:
                continue
            seen.add(id(provider))

            results.append({
                "provider_id": provider.provider_id,
                "display_name": provider.config.provider_name.capitalize(),
                "base_url": provider.config.base_url,
                "default_model": provider.config.default_model,
                "enabled": provider.config.enabled,
                "is_configured": provider.is_configured,
                "api_key_masked": mask_secret(provider.config.api_key),
                "is_local": getattr(provider, "allow_loopback", False),
                "timeout_seconds": provider.config.timeout_seconds,
            })
        return sorted(results, key=lambda x: x["provider_id"])

    async def get_all_models(self) -> Dict[str, List[str]]:
        """Fetch available models for each provider."""
        models_map: Dict[str, List[str]] = {}
        seen = set()

        for pid, provider in self._providers.items():
            if id(provider) in seen:
                continue
            seen.add(id(provider))
            try:
                models = await provider.list_models()
                models_map[provider.provider_id] = models
            except Exception as exc:
                logger.debug("Failed listing models for %s: %s", provider.provider_id, exc)
                models_map[provider.provider_id] = list(provider.config.fallback_models)

        return models_map

    def register_custom_provider(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: str = "default",
        timeout_seconds: float = 60.0,
    ) -> Dict[str, Any]:
        """Dynamically register or update a custom external AI endpoint."""
        is_safe, err = validate_endpoint_url(base_url, allow_loopback=False)
        if not is_safe:
            return {"success": False, "error": f"Security validation failed: {err}"}

        cfg = SingleProviderConfig(
            provider_name=name.lower().strip(),
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
            enabled=True,
        )
        adapter = OpenAICompatibleAdapter(cfg, allow_loopback=False)
        self._providers[name.lower().strip()] = adapter
        logger.info("Registered custom AI provider: %s (%s)", name, base_url)
        return {"success": True, "provider_id": name.lower().strip(), "base_url": base_url}

    async def close_all(self) -> None:
        """Close HTTP connection pools for all providers."""
        seen = set()
        for provider in self._providers.values():
            if id(provider) in seen:
                continue
            seen.add(id(provider))
            try:
                await provider.close()
            except Exception as exc:
                logger.debug("Error closing provider %s: %s", provider.provider_id, exc)


# Global singleton instance
_registry_instance: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get or create singleton ProviderRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProviderRegistry()
    return _registry_instance
