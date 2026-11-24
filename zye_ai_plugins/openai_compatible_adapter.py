"""Universal OpenAI-Compatible REST Adapter for Zye AI Multi-AI Plugin Hub.

Powers OpenAI-compatible endpoints:
- Perplexity (https://api.perplexity.ai)
- DeepSeek (https://api.deepseek.com)
- Groq (https://api.groq.com/openai/v1)
- OpenRouter (https://openrouter.ai/api/v1)
- Custom user-configured external endpoints (with strict SSRF validation)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from .plugin_security import sanitize_prompt, validate_endpoint_url
from .provider_base import BaseAIProvider
from .provider_config import SingleProviderConfig
from .response_normalizer import AIResponse, AIUsage

logger = logging.getLogger("zye.ai_plugins.compatible")


class OpenAICompatibleAdapter(BaseAIProvider):
    """Universal adapter for OpenAI-compatible chat completion APIs."""

    def __init__(self, config: SingleProviderConfig, allow_loopback: bool = False):
        super().__init__(config, allow_loopback=allow_loopback)
        self.provider_display_name = config.provider_name.capitalize()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key or ''}",
            "Content-Type": "application/json",
        }
        # Special headers for OpenRouter
        if self.provider_id == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/zye-ai/zye-hybrid-assistant"
            headers["X-Title"] = "Zye AI Hybrid Assistant"
        return headers

    def _resolve_endpoint(self) -> str:
        base_url = self.config.base_url.rstrip("/")
        if not base_url.endswith("/chat/completions"):
            if not base_url.endswith("/v1"):
                # If neither /v1 nor /chat/completions is present, append /v1/chat/completions unless endpoint already has it
                if "/chat" in base_url:
                    return f"{base_url}/completions"
                return f"{base_url}/chat/completions"
            return f"{base_url}/chat/completions"
        return base_url

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Call OpenAI-compatible /chat/completions and return normalized AIResponse."""
        if not self.is_configured:
            return AIResponse(
                provider_id=self.provider_id,
                model_used=model or self.config.default_model,
                content="",
                status="error",
                error_message=f"API key is not configured for provider '{self.provider_id}'",
                metadata={"configured": False},
            )

        # Validate URL safety
        is_safe, err_msg = validate_endpoint_url(self.config.base_url, allow_loopback=self.allow_loopback)
        if not is_safe:
            return AIResponse(
                provider_id=self.provider_id,
                model_used=model or self.config.default_model,
                content="",
                status="error",
                error_message=f"Security violation for provider '{self.provider_id}': {err_msg}",
                metadata={"security_blocked": True},
            )

        client = await self.get_client()
        target_model = model or self.config.default_model
        eff_temp = temperature if temperature is not None else self.config.temperature
        eff_max_tokens = max_tokens or self.config.max_tokens

        sanitized_prompt = sanitize_prompt(prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": sanitize_prompt(system_prompt)})
        messages.append({"role": "user", "content": sanitized_prompt})

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": eff_temp,
        }
        if eff_max_tokens:
            payload["max_tokens"] = eff_max_tokens

        # Pass any extra provider-specific parameters
        for k, v in kwargs.items():
            if k not in payload and v is not None:
                payload[k] = v

        endpoint = self._resolve_endpoint()
        headers = self._get_headers()
        start_time = time.perf_counter()

        try:
            logger.info("Calling %s endpoint: %s [model=%s]", self.provider_display_name, endpoint, target_model)
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                content_text = ""
                finish_reason = None
                if choices:
                    first_choice = choices[0]
                    content_text = first_choice.get("message", {}).get("content", "")
                    finish_reason = first_choice.get("finish_reason")

                usage_raw = data.get("usage", {})
                usage = AIUsage(
                    prompt_tokens=usage_raw.get("prompt_tokens", 0),
                    completion_tokens=usage_raw.get("completion_tokens", 0),
                    total_tokens=usage_raw.get("total_tokens", 0),
                    latency_ms=round(latency_ms, 2),
                )

                # Collect citations or metadata if provided (e.g., Perplexity citations)
                metadata: Dict[str, Any] = {
                    "finish_reason": finish_reason,
                    "status_code": 200,
                }
                if "citations" in data:
                    metadata["citations"] = data.get("citations")
                if "system_fingerprint" in data:
                    metadata["system_fingerprint"] = data.get("system_fingerprint")

                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=data.get("model", target_model),
                    content=content_text,
                    status="success",
                    usage=usage,
                    metadata=metadata,
                )

            elif response.status_code == 401:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"{self.provider_display_name} Authentication Error (401): Invalid API key.",
                    metadata={"status_code": 401},
                )
            elif response.status_code == 429:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"{self.provider_display_name} Rate Limit / Quota Exceeded (429).",
                    metadata={"status_code": 429},
                )
            else:
                err_text = response.text[:400]
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"{self.provider_display_name} API returned HTTP {response.status_code}: {err_text}",
                    metadata={"status_code": response.status_code},
                )

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="timeout",
                error_message=f"{self.provider_display_name} request timed out after {self.config.timeout_seconds}s",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"timeout": True},
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Unexpected error in %s adapter: %s", self.provider_display_name, exc)
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="error",
                error_message=f"{self.provider_display_name} error: {type(exc).__name__}: {str(exc)}",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"exception": str(exc)},
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check API endpoint health using non-billable check or models lookup."""
        if not self.is_configured:
            return {
                "provider_id": self.provider_id,
                "status": "unconfigured",
                "healthy": False,
                "message": f"{self.provider_display_name} API key not configured",
            }

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        # Try /models endpoint
        if "/chat" in base_url:
            models_endpoint = base_url.replace("/chat/completions", "/models").replace("/chat", "/models")
        elif not base_url.endswith("/v1"):
            models_endpoint = f"{base_url}/v1/models"
        else:
            models_endpoint = f"{base_url}/models"

        start_time = time.perf_counter()
        headers = self._get_headers()

        try:
            resp = await client.get(
                models_endpoint,
                headers=headers,
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
                    "message": f"Connected to {self.provider_display_name} successfully",
                }
            elif resp.status_code == 401:
                return {
                    "provider_id": self.provider_id,
                    "status": "auth_error",
                    "healthy": False,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"Invalid {self.provider_display_name} API Key (401)",
                }
            else:
                return {
                    "provider_id": self.provider_id,
                    "status": "warning",
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"{self.provider_display_name} endpoint returned HTTP {resp.status_code}",
                }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "unreachable",
                "healthy": False,
                "error": f"{type(exc).__name__}: {str(exc)}",
                "message": f"Failed to connect to {self.provider_display_name}",
            }

    async def list_models(self) -> List[str]:
        """Fetch list of available models from /models endpoint if available."""
        if not self.is_configured:
            return list(self.config.fallback_models)

        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        if "/chat" in base_url:
            models_endpoint = base_url.replace("/chat/completions", "/models").replace("/chat", "/models")
        elif not base_url.endswith("/v1"):
            models_endpoint = f"{base_url}/v1/models"
        else:
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
            logger.debug("%s list_models failed: %s", self.provider_display_name, exc)

        return list(self.config.fallback_models)
