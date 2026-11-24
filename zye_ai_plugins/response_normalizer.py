"""ZYE AI — Universal AI Response Normalization (Day 25).

Standardized response model for all external and local AI providers.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AIUsage(BaseModel):
    """Normalized token usage metadata."""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: float = 0.0
    provider_cost_usd: Optional[float] = None

    def __init__(self, **data: Any):
        # Support prompt_tokens / completion_tokens synonyms
        if "prompt_tokens" in data and "input_tokens" not in data:
            data["input_tokens"] = data.pop("prompt_tokens")
        if "completion_tokens" in data and "output_tokens" not in data:
            data["output_tokens"] = data.pop("completion_tokens")
        super().__init__(**data)

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens or 0

    @property
    def completion_tokens(self) -> int:
        return self.output_tokens or 0


class AIResponse(BaseModel):
    """Universal normalized AI response across all providers."""
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:10]}")
    provider_id: str
    provider_name: str = ""
    model: str = ""
    status: str = "success"  # "success" | "error" | "rate_limited" | "timeout" | "unconfigured" | "unreachable"
    content: str = ""
    finish_reason: Optional[str] = "stop"
    usage: AIUsage = Field(default_factory=AIUsage)
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        # Support model_used / error_message / metadata synonyms
        if "model_used" in data and "model" not in data:
            data["model"] = data.pop("model_used")
        if "error_message" in data and "error" not in data:
            data["error"] = data.pop("error_message")
        if "metadata" in data and "raw_metadata" not in data:
            data["raw_metadata"] = data.pop("metadata")
        super().__init__(**data)

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def model_used(self) -> str:
        return self.model

    @property
    def error_message(self) -> Optional[str]:
        return self.error

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.raw_metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching standard Zye assistant response schema."""
        d = self.model_dump()
        d["is_success"] = self.is_success
        d["model_used"] = self.model_used
        d["error_message"] = self.error_message
        return d
