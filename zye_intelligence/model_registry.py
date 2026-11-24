"""
ZYE AI — Model Health Registry
==============================

Tracks provider model capabilities, availability, recent latency, and circuit status.
Conforms to Section 07 of Master Engineering Specification.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from zye_core.types import ModelCircuitState

logger = logging.getLogger("zye.intelligence.registry")


class ModelCapability(str, Enum):
    TEXT = "TEXT"
    NATIVE_AUDIO = "NATIVE_AUDIO"
    TOOL_CALLING = "TOOL_CALLING"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    MULTIMODAL_VISION = "MULTIMODAL_VISION"


@dataclass
class ModelMetadata:
    provider: str  # "gemini", "local_ollama", etc.
    model_id: str
    display_name: str
    capabilities: Set[ModelCapability] = field(default_factory=set)
    context_limit: int = 128000
    is_available: bool = True
    recent_latency_ms: float = 0.0
    recent_error_rate: float = 0.0
    last_success_timestamp: float = 0.0
    last_failure_timestamp: float = 0.0
    circuit_state: ModelCircuitState = ModelCircuitState.CLOSED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["capabilities"] = [c.value for c in self.capabilities]
        d["circuit_state"] = self.circuit_state.value
        return d


class ModelHealthRegistry:
    """Thread-safe catalog of available models and real-time health metrics."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetadata] = {}
        self._lock = threading.Lock()
        self._initialize_default_catalog()

    def _initialize_default_catalog(self) -> None:
        """Seed registry with officially supported Gemini and local inference models."""
        # Primary Gemini Models
        self.register_model(
            ModelMetadata(
                provider="gemini",
                model_id="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash (Primary Master Brain)",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.STRUCTURED_OUTPUT,
                    ModelCapability.MULTIMODAL_VISION,
                },
                context_limit=1000000,
            )
        )
        self.register_model(
            ModelMetadata(
                provider="gemini",
                model_id="gemini-2.5-pro",
                display_name="Gemini 2.5 Pro (Deep Reasoning)",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.STRUCTURED_OUTPUT,
                    ModelCapability.MULTIMODAL_VISION,
                },
                context_limit=2000000,
            )
        )
        self.register_model(
            ModelMetadata(
                provider="gemini",
                model_id="gemini-3.8-live",
                display_name="Gemini 3.8 Live (Native Audio Voice Engine)",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.NATIVE_AUDIO,
                    ModelCapability.TOOL_CALLING,
                },
                context_limit=128000,
            )
        )

    def register_model(self, model: ModelMetadata) -> None:
        """Register or update a model's specification."""
        with self._lock:
            self._models[model.model_id] = model

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Look up a model by exact identifier."""
        with self._lock:
            return self._models.get(model_id)

    def list_models(
        self,
        provider: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
    ) -> List[ModelMetadata]:
        """Return registered models filtered by provider and capability."""
        with self._lock:
            models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if capability:
            models = [m for m in models if capability in m.capabilities]

        return models

    def record_request_outcome(
        self,
        model_id: str,
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """Update latency, error rate, and timestamps for model health tracking."""
        with self._lock:
            model = self._models.get(model_id)
            if not model:
                return

            now = time.time()
            if success:
                model.last_success_timestamp = now
                # Exponential moving average for latency
                if model.recent_latency_ms == 0.0:
                    model.recent_latency_ms = latency_ms
                else:
                    model.recent_latency_ms = (0.8 * model.recent_latency_ms) + (0.2 * latency_ms)
                # Decay error rate on success
                model.recent_error_rate = max(0.0, model.recent_error_rate * 0.7)
            else:
                model.last_failure_timestamp = now
                model.recent_error_rate = min(1.0, model.recent_error_rate + 0.3)


# Singleton
_registry: Optional[ModelHealthRegistry] = None
_reg_lock = threading.Lock()


def get_model_registry() -> ModelHealthRegistry:
    global _registry
    with _reg_lock:
        if _registry is None:
            _registry = ModelHealthRegistry()
        return _registry
