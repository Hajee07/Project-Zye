"""
ZYE AI — AI Provider Configuration Manager (Day 25)
Loads and validates settings from zye_config.toml and environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SingleProviderConfig(BaseModel):
    """Configuration schema for a single AI provider."""
    provider_name: str = ""
    enabled: bool = True
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    timeout_seconds: float = 45.0
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    fallback_models: list[str] = Field(default_factory=list)
    extra_headers: dict[str, str] = Field(default_factory=dict)



class AIPluginMasterConfig(BaseModel):
    """Master configuration for the Day 25 Multi-AI Plugin Hub."""
    enabled: bool = True
    ai_council_enabled: bool = True
    max_council_participants: int = 4
    default_timeout_seconds: float = 45.0
    max_retries: int = 2
    max_prompt_chars: int = 30000
    max_response_chars: int = 30000

    # Provider configurations
    openai: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="openai",
            default_model="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
        )
    )
    anthropic: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="anthropic",
            default_model="claude-3-5-sonnet-20241022",
            base_url="https://api.anthropic.com/v1",
        )
    )
    ollama: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="ollama",
            default_model="llama3.2",
            base_url="http://127.0.0.1:11434",
            timeout_seconds=60.0,
        )
    )
    perplexity: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="perplexity",
            default_model="sonar",
            base_url="https://api.perplexity.ai",
        )
    )
    deepseek: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="deepseek",
            default_model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
        )
    )
    groq: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="groq",
            default_model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
        )
    )
    openrouter: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="openrouter",
            default_model="meta-llama/llama-3.3-70b-instruct",
            base_url="https://openrouter.ai/api/v1",
        )
    )
    custom: SingleProviderConfig = Field(
        default_factory=lambda: SingleProviderConfig(
            provider_name="custom",
            enabled=False,
            default_model="",
            base_url="",
        )
    )

    def get_provider(self, name: str) -> Optional[SingleProviderConfig]:
        target = name.lower().strip()
        alias_map = {
            "chatgpt": "openai",
            "claude": "anthropic",
        }
        eff = alias_map.get(target, target)
        return getattr(self, eff, None)



def load_ai_plugins_config(config_path: Optional[Path] = None) -> AIPluginMasterConfig:
    """
    Load configuration from zye_config.toml with environment variable overrides.
    """
    toml_dict: dict[str, Any] = {}
    path = config_path or (PROJECT_ROOT / "zye_config.toml")
    if path.is_file():
        try:
            import tomllib
            with open(path, "rb") as f:
                data = tomllib.load(f)
                toml_dict = data.get("ai_plugins", {})
        except Exception:
            toml_dict = {}

    master = AIPluginMasterConfig(**{k: v for k, v in toml_dict.items() if k in AIPluginMasterConfig.model_fields})

    # Apply environment variable overrides (highest precedence)
    master.openai.api_key = os.environ.get("OPENAI_API_KEY", master.openai.api_key).strip()
    master.openai.default_model = os.environ.get("OPENAI_MODEL", master.openai.default_model).strip()

    master.anthropic.api_key = os.environ.get("ANTHROPIC_API_KEY", master.anthropic.api_key).strip()
    master.anthropic.default_model = os.environ.get("CLAUDE_MODEL", master.anthropic.default_model).strip()

    master.ollama.base_url = os.environ.get("OLLAMA_URL", master.ollama.base_url).strip()
    master.ollama.default_model = os.environ.get("OLLAMA_MODEL", master.ollama.default_model).strip()

    master.perplexity.api_key = os.environ.get("PERPLEXITY_API_KEY", master.perplexity.api_key).strip()
    master.deepseek.api_key = os.environ.get("DEEPSEEK_API_KEY", master.deepseek.api_key).strip()
    master.groq.api_key = os.environ.get("GROQ_API_KEY", master.groq.api_key).strip()
    master.openrouter.api_key = os.environ.get("OPENROUTER_API_KEY", master.openrouter.api_key).strip()

    master.custom.api_key = os.environ.get("CUSTOM_AI_API_KEY", master.custom.api_key).strip()
    master.custom.base_url = os.environ.get("CUSTOM_AI_BASE_URL", master.custom.base_url).strip()
    master.custom.default_model = os.environ.get("CUSTOM_AI_MODEL", master.custom.default_model).strip()
    if os.environ.get("CUSTOM_AI_ENABLED", "").lower() in ("true", "1", "yes"):
        master.custom.enabled = True

    return master


load_master_config = load_ai_plugins_config

