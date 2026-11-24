"""OpenAI ChatGPT Adapter for Zye AI Multi-AI Plugin Hub (Day 25).

Connects to official OpenAI Chat Completions API:
- POST /v1/chat/completions
- Bearer token authentication
- Model discovery via GET /v1/models
- Non-billable health checks
- Token usage tracking and structured normalization
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from .plugin_security import sanitize_prompt, validate_endpoint_url
from .provider_base import BaseAIProvider
from .provider_config import SingleProviderConfig
from .response_normalizer import AIResponse, AIUsage

logger = logging.getLogger("zye.ai_plugins.openai")

DEFAULT_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1-preview",
    "o1-mini",
]


class OpenAIAdapter(BaseAIProvider):
    """Adapter for OpenAI ChatGPT API."""

    def __init__(
        self,
        config_or_key: Union[SingleProviderConfig, str] = "",
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        enabled: bool = True,
        timeout_seconds: float = 45.0,
    ) -> None:
        if isinstance(config_or_key, SingleProviderConfig):
            cfg = config_or_key
            if not cfg.provider_name:
                cfg.provider_name = "openai"
            super().__init__(cfg, display_name="OpenAI ChatGPT", provider_type="openai")
        else:
            cfg = SingleProviderConfig(
                provider_name="openai",
                api_key=str(config_or_key),
                base_url=base_url,
                default_model=default_model,
                enabled=enabled,
                timeout_seconds=timeout_seconds,
            )
            super().__init__(cfg, display_name="OpenAI ChatGPT", provider_type="openai")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key or ''}",
            "Content-Type": "application/json",
        }

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Call OpenAI /chat/completions and return normalized AIResponse."""
        target_model = model or self.config.default_model or "gpt-4o-mini"
        self.total_requests += 1

        if not self.config.enabled:
            return AIResponse(
                provider_id=self.provider_id,
                provider_name=self.display_name,
                model=target_model,
                status="error",
                error="OpenAI ChatGPT provider is disabled in configuration.",
            )

        if not self.is_configured:
            return AIResponse(
                provider_id=self.provider_id,
                provider_name=self.display_name,
                model=target_model,
                status="unconfigured",
                error="OPENAI_API_KEY is missing or unconfigured.",
            )

        is_valid_url, err_msg = validate_endpoint_url(self.config.base_url)
        if not is_valid_url:
            return AIResponse(
                provider_id=self.provider_id,
                provider_name=self.display_name,
                model=target_model,
                status="error",
                error=f"Unsafe or invalid OpenAI base URL: {err_msg}",
            )

        client = await self.get_client()
        sanitized = sanitize_prompt(prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": sanitize_prompt(system_prompt)})
        messages.append({"role": "user", "content": sanitized})

        eff_temp = temperature if temperature is not None else 0.7
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": eff_temp,
        }
        if max_tokens or self.config.max_tokens:
            payload["max_tokens"] = max_tokens or self.config.max_tokens

        base_url = self.config.base_url.rstrip("/")
        if not base_url.endswith("/chat/completions"):
            endpoint = f"{base_url}/chat/completions"
        else:
            endpoint = base_url

        start_time = time.perf_counter()
        try:
            resp = await client.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                content_text = ""
                finish_reason = "stop"
                if choices:
                    first = choices[0]
                    content_text = first.get("message", {}).get("content", "")
                    finish_reason = first.get("finish_reason", "stop")

                u_raw = data.get("usage", {})
                usage = AIUsage(
                    prompt_tokens=u_raw.get("prompt_tokens", 0),
                    completion_tokens=u_raw.get("completion_tokens", 0),
                    total_tokens=u_raw.get("total_tokens", 0),
                    latency_ms=round(latency_ms, 2),
                )
                self.last_successful_request = time.time()

                return AIResponse(
                    provider_id=self.provider_id,
                    provider_name=self.display_name,
                    model=data.get("model", target_model),
                    status="success",
                    content=content_text,
                    finish_reason=finish_reason,
                    usage=usage,
                    latency_ms=round(latency_ms, 2),
                    raw_metadata={"status_code": 200},
                )

            elif resp.status_code == 401:
                self.total_errors += 1
                return AIResponse(
                    provider_id=self.provider_id,
                    provider_name=self.display_name,
                    model=target_model,
                    status="error",
                    error="OpenAI Authentication Error (401): Invalid API key.",
                    latency_ms=round(latency_ms, 2),
                )
            elif resp.status_code == 429:
                self.total_errors += 1
                return AIResponse(
                    provider_id=self.provider_id,
                    provider_name=self.display_name,
                    model=target_model,
                    status="rate_limited",
                    error="OpenAI Rate Limit Exceeded (429): Quota exceeded or too many requests.",
                    latency_ms=round(latency_ms, 2),
                )
            else:
                self.total_errors += 1
                return AIResponse(
                    provider_id=self.provider_id,
                    provider_name=self.display_name,
                    model=target_model,
                    status="error",
                    error=f"OpenAI API returned HTTP {resp.status_code}: {resp.text[:300]}",
                    latency_ms=round(latency_ms, 2),
                )

        except httpx.TimeoutException:
            self.total_errors += 1
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                provider_name=self.display_name,
                model=target_model,
                status="timeout",
                error=f"OpenAI request timed out after {self.config.timeout_seconds}s",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as exc:
            self.total_errors += 1
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                provider_name=self.display_name,
                model=target_model,
                status="error",
                error=f"OpenAI error: {type(exc).__name__}: {str(exc)}",
                latency_ms=round(latency_ms, 2),
            )

    async def check_health(self) -> Dict[str, Any]:
        """Perform non-billable availability check via GET /models."""
        if not self.is_configured:
            return {
                "provider_id": self.provider_id,
                "status": "unconfigured",
                "healthy": False,
                "message": "OpenAI API key is missing or unconfigured",
            }

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        models_endpoint = f"{base_url}/models" if not base_url.endswith("/models") else base_url

        start_time = time.perf_counter()
        try:
            resp = await client.get(
                models_endpoint,
                headers=self._get_headers(),
                timeout=10.0,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", []) if "id" in m]
                return {
                    "provider_id": self.provider_id,
                    "status": "healthy",
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                    "models_count": len(models),
                    "message": "Connected successfully to OpenAI API",
                }
            elif resp.status_code == 401:
                return {
                    "provider_id": self.provider_id,
                    "status": "auth_error",
                    "healthy": False,
                    "latency_ms": round(latency_ms, 2),
                    "message": "Invalid OpenAI API Key (401)",
                }
            else:
                return {
                    "provider_id": self.provider_id,
                    "status": "warning",
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"OpenAI models endpoint returned HTTP {resp.status_code}",
                }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "unreachable",
                "healthy": False,
                "message": f"Failed to connect to OpenAI API: {exc}",
            }

    async def list_models(self) -> List[str]:
        """Fetch models dynamically or return defaults."""
        if not self.is_configured:
            return list(DEFAULT_OPENAI_MODELS)

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        models_endpoint = f"{base_url}/models"

        try:
            resp = await client.get(
                models_endpoint,
                headers=self._get_headers(),
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", []) if "id" in m]
                if models:
                    return sorted(models)
        except Exception as exc:
            logger.debug("Failed to fetch OpenAI models dynamically: %s", exc)

        return list(DEFAULT_OPENAI_MODELS)
