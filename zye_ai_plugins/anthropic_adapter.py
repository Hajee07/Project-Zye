"""Anthropic Claude API Adapter for Zye AI Multi-AI Plugin Hub.

Handles communication with Anthropic Messages API:
- POST /v1/messages
- Headers: x-api-key, anthropic-version: 2023-06-01
- Model fallback and token management
- Structured AIResponse normalization
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from .plugin_security import sanitize_prompt
from .provider_base import BaseAIProvider
from .provider_config import SingleProviderConfig
from .response_normalizer import AIResponse, AIUsage

logger = logging.getLogger("zye.ai_plugins.anthropic")

DEFAULT_ANTHROPIC_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
]


class AnthropicAdapter(BaseAIProvider):
    """Adapter for Anthropic Claude Messages API."""

    def __init__(self, config: SingleProviderConfig):
        super().__init__(config)
        self.api_version = "2023-06-01"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "x-api-key": self.config.api_key or "",
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }
        return headers

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Call Anthropic Messages API and return normalized AIResponse."""
        if not self.is_configured:
            return AIResponse(
                provider_id=self.provider_id,
                model_used=model or self.config.default_model,
                content="",
                status="error",
                error_message=f"Anthropic API key is not configured for provider '{self.provider_id}'",
                metadata={"configured": False},
            )

        client = await self.get_client()
        target_model = model or self.config.default_model
        eff_temp = temperature if temperature is not None else self.config.temperature
        eff_max_tokens = max_tokens or self.config.max_tokens or 4096

        sanitized_prompt = sanitize_prompt(prompt)

        # Messages format for Anthropic
        messages = [{"role": "user", "content": sanitized_prompt}]
        payload: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": eff_max_tokens,
            "messages": messages,
            "temperature": eff_temp,
        }
        if system_prompt:
            payload["system"] = sanitize_prompt(system_prompt)

        # Target endpoint
        base_url = self.config.base_url.rstrip("/")
        if not base_url.endswith("/v1/messages") and not base_url.endswith("/messages"):
            if "/v1" in base_url:
                endpoint = f"{base_url}/messages"
            else:
                endpoint = f"{base_url}/v1/messages"
        else:
            endpoint = base_url

        start_time = time.perf_counter()
        headers = self._get_headers()

        try:
            logger.info("Sending request to Anthropic API endpoint: %s [model=%s]", endpoint, target_model)
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                data = response.json()
                content_blocks = data.get("content", [])
                text_content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")

                usage_raw = data.get("usage", {})
                usage = AIUsage(
                    prompt_tokens=usage_raw.get("input_tokens", 0),
                    completion_tokens=usage_raw.get("output_tokens", 0),
                    total_tokens=usage_raw.get("input_tokens", 0) + usage_raw.get("output_tokens", 0),
                    latency_ms=round(latency_ms, 2),
                )

                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=data.get("model", target_model),
                    content=text_content,
                    status="success",
                    usage=usage,
                    metadata={
                        "stop_reason": data.get("stop_reason"),
                        "stop_sequence": data.get("stop_sequence"),
                        "status_code": 200,
                    },
                )

            elif response.status_code == 401:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message="Anthropic Authentication Error (401): Invalid API key.",
                    metadata={"status_code": 401},
                )
            elif response.status_code == 429:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message="Anthropic Rate Limit Exceeded (429): Too many requests or quota exceeded.",
                    metadata={"status_code": 429},
                )
            elif response.status_code == 529:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message="Anthropic Service Overloaded (529): Please try again later.",
                    metadata={"status_code": 529},
                )
            else:
                err_text = response.text[:400]
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"Anthropic API returned status {response.status_code}: {err_text}",
                    metadata={"status_code": response.status_code},
                )

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="timeout",
                error_message=f"Anthropic request timed out after {self.config.timeout_seconds}s",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"timeout": True},
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Unexpected error in AnthropicAdapter: %s", exc)
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="error",
                error_message=f"Anthropic error: {type(exc).__name__}: {str(exc)}",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"exception": str(exc)},
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check Anthropic API health."""
        if not self.is_configured:
            return {
                "provider_id": self.provider_id,
                "status": "unconfigured",
                "healthy": False,
                "message": "API key not configured",
            }

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        if "/v1" not in base_url:
            models_endpoint = f"{base_url}/v1/models"
        else:
            models_endpoint = f"{base_url}/models"

        start_time = time.perf_counter()
        try:
            resp = await client.get(
                models_endpoint,
                headers=self._get_headers(),
                timeout=min(self.config.timeout_seconds, 10.0),
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
                    "message": "Connected successfully to Anthropic API",
                }
            elif resp.status_code == 401:
                return {
                    "provider_id": self.provider_id,
                    "status": "auth_error",
                    "healthy": False,
                    "latency_ms": round(latency_ms, 2),
                    "message": "Invalid Anthropic API Key (401)",
                }
            else:
                return {
                    "provider_id": self.provider_id,
                    "status": "warning",
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"Anthropic endpoint returned HTTP {resp.status_code}",
                }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "unreachable",
                "healthy": False,
                "error": f"{type(exc).__name__}: {str(exc)}",
                "message": "Failed to connect to Anthropic API",
            }

    async def list_models(self) -> List[str]:
        """List available Anthropic models."""
        if not self.is_configured:
            return list(DEFAULT_ANTHROPIC_MODELS)

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        models_endpoint = f"{base_url}/v1/models" if "/v1" not in base_url else f"{base_url}/models"

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
            logger.debug("Failed to fetch Anthropic models dynamically: %s", exc)

        return list(DEFAULT_ANTHROPIC_MODELS)
