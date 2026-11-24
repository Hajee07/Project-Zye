"""
Unit tests for ZYE Model Health Registry, Circuit Breaker, and Gemini 503 Recovery Engine.
"""

from __future__ import annotations

import pytest
import time
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ModelCircuitState, ZyeEventType
from zye_intelligence.circuit_breaker import ModelCircuitBreaker
from zye_intelligence.model_registry import ModelHealthRegistry, ModelCapability
from zye_intelligence.recovery_engine import GeminiRecoveryEngine, ErrorCategory
from zye_intelligence.schemas import sanitize_schema_for_gemini_developer_api


def test_sanitize_schema_strips_additional_properties():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "sub": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"val": {"type": "integer"}},
            },
        },
        "additionalProperties": False,
    }
    sanitized = sanitize_schema_for_gemini_developer_api(schema)
    assert "additionalProperties" not in sanitized
    assert "additionalProperties" not in sanitized["properties"]["sub"]
    assert sanitized["properties"]["name"]["type"] == "string"


def test_circuit_breaker_tripping_and_cooldown():
    cb = ModelCircuitBreaker(default_failure_threshold=3, default_cooldown_seconds=0.2)
    model = "gemini-2.5-flash"

    # Initially closed
    assert cb.allow_request(model) is True
    assert cb.get_state(model) == ModelCircuitState.CLOSED

    # Record 2 failures -> still closed
    cb.record_transient_failure(model)
    cb.record_transient_failure(model)
    assert cb.get_state(model) == ModelCircuitState.CLOSED
    assert cb.allow_request(model) is True

    # 3rd failure -> trips to OPEN
    cb.record_transient_failure(model)
    assert cb.get_state(model) == ModelCircuitState.OPEN
    assert cb.allow_request(model) is False

    # Wait for cooldown to expire (0.2s)
    time.sleep(0.25)

    # Next call allows single HALF_OPEN probe
    assert cb.allow_request(model) is True
    assert cb.get_state(model) == ModelCircuitState.HALF_OPEN
    # Second concurrent call before probe finishes is rejected
    assert cb.allow_request(model) is False

    # Probe succeeds -> resets to CLOSED
    cb.record_success(model)
    assert cb.get_state(model) == ModelCircuitState.CLOSED
    assert cb.allow_request(model) is True


def test_recovery_engine_classification():
    engine = GeminiRecoveryEngine()

    # 503 Overload must NOT rotate keys!
    exc_503 = Exception("503 Service Unavailable: Model is overloaded")
    decision_503 = engine.classify_error(exc_503)
    assert decision_503.category == ErrorCategory.TRANSIENT_503
    assert decision_503.retryable is True
    assert decision_503.rotate_key is False
    assert decision_503.trip_circuit is True

    # 429 Quota Exceeded MUST rotate key
    exc_429 = Exception("429 Resource Exhausted: Quota exceeded for project")
    decision_429 = engine.classify_error(exc_429)
    assert decision_429.category == ErrorCategory.RATE_LIMIT_429
    assert decision_429.retryable is True
    assert decision_429.rotate_key is True
    assert decision_429.trip_circuit is False

    # 400 Invalid Argument fails fast without retry
    exc_400 = Exception("400 Invalid Argument: Field 'x' unrecognized")
    decision_400 = engine.classify_error(exc_400)
    assert decision_400.category == ErrorCategory.CLIENT_400
    assert decision_400.retryable is False
    assert decision_400.rotate_key is False


def test_recovery_engine_sync_execution():
    cb = ModelCircuitBreaker(default_failure_threshold=2, default_cooldown_seconds=1.0)
    engine = GeminiRecoveryEngine(circuit_breaker=cb, base_backoff=0.01, jitter_max=0.01)
    model = "gemini-2.5-pro"

    calls = 0
    def mock_operation():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise Exception("503 Server temporarily overloaded")
        return "success_result"

    res = engine.execute_with_recovery_sync(model, mock_operation, max_retries=3)
    assert res == "success_result"
    assert calls == 2
    assert cb.get_state(model) == ModelCircuitState.CLOSED
