"""Universal Provider Base Class for Zye AI Multi-AI Plugin Hub (Day 25).

Defines the standard abstract contract for all AI provider adapters:
- Async HTTP connection pooling via httpx.AsyncClient
- Normalization into AIResponse and AIUsage
- Non-billable health checking
- Model discovery and security validation
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from .plugin_security import mask_secret
from .provider_config import SingleProviderConfig
from .response_normalizer import AIResponse, AIUsage

logger = logging.getLogger("zye.ai_plugins.base")


class BaseAIProvider(ABC):
    """Abstract base class for all external and local AI providers."""

    def __init__(
        self,
        config_or_id: Union[SingleProviderConfig, str],
        display_name: str = "",
        provider_type: str = "generic",
        default_model: str = "",
        enabled: bool = True,
        timeout_seconds: float = 45.0,
        allow_loopback: bool = False,
    ) -> None:
        if isinstance(config_or_id, SingleProviderConfig):
            self.config = config_or_id
            self.provider_id = (config_or_id.provider_name or "provider").lower().strip()
            self.display_name = display_name or self.provider_id.capitalize()
            self.provider_type = provider_type
            self.default_model = config_or_id.default_model or default_model
            self.enabled = config_or_id.enabled
            self.timeout_seconds = config_or_id.timeout_seconds or timeout_seconds
            self.allow_loopback = allow_loopback
        else:
            self.provider_id = str(config_or_id).lower().strip()
            self.display_name = display_name or self.provider_id.capitalize()
            self.provider_type = provider_type
            self.default_model = default_model
            self.enabled = enabled
            self.timeout_seconds = timeout_seconds
            self.allow_loopback = allow_loopback
            self.config = SingleProviderConfig(
                provider_name=self.provider_id,
                default_model=default_model,
                enabled=enabled,
                timeout_seconds=timeout_seconds,
            )

        self._client: Optional[httpx.AsyncClient] = None
        self.last_successful_request: Optional[float] = None
        self.last_error: Optional[str] = None
        self.total_requests: int = 0
        self.total_errors: int = 0

    @property
    def is_configured(self) -> bool:
        """Return True if required credentials/settings are present."""
        if getattr(self, "allow_loopback", False):
            return True
        key = getattr(self.config, "api_key", "")
        return bool(key and not key.startswith("your_") and not key.startswith("placeholder"))

    async def get_client(self) -> httpx.AsyncClient:
        """Get or initialize the reusable httpx.AsyncClient with connection pooling."""
        if self._client is None or getattr(self._client, "is_closed", False):
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
                limits=limits,
            )
        return self._client


    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Execute chat completion and return normalized AIResponse."""
        pass

    async def generate(
        self,
        prompt: str,
        system_role: str = "",
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        """Compatibility wrapper forwarding to generate_response."""
        opts = options or {}
        return await self.generate_response(
            prompt=prompt,
            system_prompt=system_role,
            model=model,
            temperature=opts.get("temperature"),
            max_tokens=opts.get("max_tokens"),
        )

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform non-billable availability and health check."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Compatibility wrapper forwarding to check_health."""
        return await self.check_health()

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Retrieve list of supported or discoverable models."""
        pass

    async def close(self) -> None:
        """Release underlying HTTP client resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def get_metadata(self) -> Dict[str, Any]:
        """Return provider metadata and health metrics."""
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "provider_type": self.provider_type,
            "default_model": self.default_model or self.config.default_model,
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "is_configured": self.is_configured,
            "is_local": self.allow_loopback,
            "masked_key": mask_secret(getattr(self.config, "api_key", "")),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
        }
