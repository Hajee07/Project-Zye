"""Local Ollama REST API Adapter for Zye AI Multi-AI Plugin Hub.

Connects to locally running Ollama instance:
- Default: http://127.0.0.1:11434
- POST /api/chat
- GET /api/tags (installed models)
- GET /api/version
- Non-billable, zero cloud exposure, 100% private local execution.
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

logger = logging.getLogger("zye.ai_plugins.ollama")

DEFAULT_OLLAMA_FALLBACK_MODELS = [
    "llama3.2",
    "llama3",
    "mistral",
    "phi3",
    "deepseek-r1",
    "gemma2",
]


class OllamaAdapter(BaseAIProvider):
    """Adapter for local Ollama REST server."""

    def __init__(self, config: SingleProviderConfig):
        # Allow loopback for Ollama
        super().__init__(config, allow_loopback=True)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "content-type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
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
        """Call Ollama /api/chat and return normalized AIResponse."""
        if not self.config.enabled:
            return AIResponse(
                provider_id=self.provider_id,
                model_used=model or self.config.default_model,
                content="",
                status="error",
                error_message=f"Local Ollama provider '{self.provider_id}' is disabled in configuration",
                metadata={"configured": False, "enabled": False},
            )

        client = await self.get_client()
        target_model = model or self.config.default_model
        eff_temp = temperature if temperature is not None else self.config.temperature

        sanitized_prompt = sanitize_prompt(prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": sanitize_prompt(system_prompt)})
        messages.append({"role": "user", "content": sanitized_prompt})

        options: Dict[str, Any] = {"temperature": eff_temp}
        if max_tokens or self.config.max_tokens:
            options["num_predict"] = max_tokens or self.config.max_tokens

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        base_url = self.config.base_url.rstrip("/")
        if not base_url.endswith("/api/chat"):
            if base_url.endswith("/api"):
                endpoint = f"{base_url}/chat"
            else:
                endpoint = f"{base_url}/api/chat"
        else:
            endpoint = base_url

        start_time = time.perf_counter()
        headers = self._get_headers()

        try:
            logger.info("Calling local Ollama endpoint: %s [model=%s]", endpoint, target_model)
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if response.status_code == 200:
                data = response.json()
                msg = data.get("message", {})
                content_text = msg.get("content", "")

                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                total_duration_ns = data.get("total_duration", 0)

                usage = AIUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    latency_ms=round(latency_ms, 2),
                )

                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=data.get("model", target_model),
                    content=content_text,
                    status="success",
                    usage=usage,
                    metadata={
                        "total_duration_ns": total_duration_ns,
                        "done": data.get("done", True),
                        "done_reason": data.get("done_reason"),
                        "status_code": 200,
                        "local": True,
                    },
                )

            elif response.status_code == 404:
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"Ollama model '{target_model}' not found. Run 'ollama pull {target_model}' in terminal.",
                    metadata={"status_code": 404, "model_missing": True},
                )
            else:
                err_text = response.text[:400]
                return AIResponse(
                    provider_id=self.provider_id,
                    model_used=target_model,
                    content="",
                    status="error",
                    error_message=f"Ollama server returned status {response.status_code}: {err_text}",
                    metadata={"status_code": response.status_code},
                )

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="unreachable",
                error_message=f"Local Ollama server is not running at {self.config.base_url}. Start Ollama service on your PC.",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"connect_error": True, "local": True},
            )
        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="timeout",
                error_message=f"Ollama request timed out after {self.config.timeout_seconds}s (local model may still be generating)",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"timeout": True},
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Unexpected error in OllamaAdapter: %s", exc)
            return AIResponse(
                provider_id=self.provider_id,
                model_used=target_model,
                content="",
                status="error",
                error_message=f"Ollama error: {type(exc).__name__}: {str(exc)}",
                usage=AIUsage(latency_ms=round(latency_ms, 2)),
                metadata={"exception": str(exc)},
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check if local Ollama daemon is active and responsive."""
        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        version_endpoint = f"{base_url}/api/version"

        start_time = time.perf_counter()
        try:
            resp = await client.get(version_endpoint, timeout=5.0)
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            if resp.status_code == 200:
                ver_data = resp.json()
                version_str = ver_data.get("version", "unknown")
                # Also check available models
                models = await self.list_models()
                return {
                    "provider_id": self.provider_id,
                    "status": "healthy",
                    "healthy": True,
                    "version": version_str,
                    "latency_ms": round(latency_ms, 2),
                    "models_count": len(models),
                    "installed_models": models,
                    "message": f"Local Ollama v{version_str} is running ({len(models)} models available)",
                }
            else:
                return {
                    "provider_id": self.provider_id,
                    "status": "unhealthy",
                    "healthy": False,
                    "latency_ms": round(latency_ms, 2),
                    "message": f"Ollama responded with HTTP {resp.status_code}",
                }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "status": "unreachable",
                "healthy": False,
                "message": f"Local Ollama is offline or unreachable at {base_url} ({type(exc).__name__})",
            }

    async def list_models(self) -> List[str]:
        """Fetch list of models locally pulled into Ollama."""
        client = await self.get_client()
        base_url = self.config.base_url.rstrip("/")
        tags_endpoint = f"{base_url}/api/tags"

        try:
            resp = await client.get(tags_endpoint, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models_info = data.get("models", [])
                names = [m.get("name") for m in models_info if "name" in m]
                if names:
                    return sorted(names)
        except Exception as exc:
            logger.debug("Ollama list_models failed: %s", exc)

        return list(DEFAULT_OLLAMA_FALLBACK_MODELS)
