# ZYE AI — Model Reliability & Gateway Failover Report

**Subsystem:** `zye_intelligence` (`circuit_breaker.py`, `recovery_engine.py`, `hybrid_router.py`)  
**Specification:** Master Specification Section 08 & Section 09  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Under high demand or Google Cloud API congestion, Gemini models can return `503 Service Unavailable` or `429 Resource Exhausted`. Prior naive implementations had two critical flaws:
1. **Blind Key Rotation on 503:** 503 represents server-side model overload. Rotating across all 7 Gemini API keys during a 503 burns rate limit quotas on every single key while the model is still unavailable.
2. **Infinite Retries on Bad Input:** 400 Client errors (e.g. `additionalProperties` schema validation errors) were repeatedly retried, wasting request budgets on deterministic failures.

---

## 2. Implemented Architecture

### 2.1 Model Circuit Breaker (`circuit_breaker.py`)
- **States:** `CLOSED` (normal traffic), `OPEN` (tripped after 3 consecutive transient failures; cooldown: 30s), `HALF_OPEN` (single probe permitted).
- **Partitioning:** Thread-safe metrics registry maintained independently per model ID (e.g. `gemini-2.5-pro` vs `gemini-2.5-flash`).
- **Cooldown Hysteresis:** If the probe succeeds during `HALF_OPEN`, state transitions back to `CLOSED`. If it fails, circuit re-trips to `OPEN`.

### 2.2 Error Classification & Recovery Engine (`recovery_engine.py`)

| Encountered Error | Category | Retryable | Rotate API Key? | Trip Circuit? | Action |
|---|---|---|---|---|---|
| `503 UNAVAILABLE` | `TRANSIENT_503` | **Yes** | **NO (Withheld)** | **Yes** | Exponential backoff + jitter; never burn 7 keys on overload |
| `429 RESOURCE_EXHAUSTED` | `RATE_LIMIT_429` | **Yes** | **YES (Rotate)** | **No** | Key pool rotation to next healthy key |
| `400 INVALID_ARGUMENT` | `CLIENT_400` | **NO** | **NO** | **No** | Fail-fast immediately; zero pointless retries |
| `401 / 403 AUTH` | `AUTH_401_403` | **Yes** | **YES (Rotate)** | **No** | Mark key unauthorized and rotate |
| `TIMEOUT` | `NETWORK_TIMEOUT` | **Yes** | **NO** | **Yes** | Network retry with backoff |

### 2.3 Schema Sanitization (`schemas.py`)
- `sanitize_schema_for_gemini_developer_api()` recursively strips `additionalProperties` and un-supported Pydantic attributes before requests reach the Gemini Developer API, eliminating deterministic 400 schema rejects.

---

## 3. Test Evidence

```
tests/test_model_circuit_breaker.py::test_sanitize_schema_strips_additional_properties PASSED [ 25%]
tests/test_model_circuit_breaker.py::test_circuit_breaker_tripping_and_cooldown PASSED         [ 50%]
tests/test_model_circuit_breaker.py::test_recovery_engine_classification PASSED               [ 75%]
tests/test_model_circuit_breaker.py::test_recovery_engine_sync_execution PASSED               [100%]
```
- **CLI Verification:** `python doctor.py --model-routing-health --gemini-failover-health --circuit-breaker-test` returned exit code 0.
