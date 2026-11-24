# ZYE AI — DAY 27: ENTERPRISE 3-STATE CIRCUIT BREAKER

## 1. Circuit Breaker Overview
To prevent cascading failures, thread starvation, and repeated network timeouts, Zye AI implements an enterprise-grade 3-State Circuit Breaker (`zye_ai_plugins/resilience/circuit_breaker.py`) isolated per AI provider.

```
+--------------------------------------------------------------------------------+
|                         3-STATE CIRCUIT BREAKER DIAGRAM                        |
+--------------------------------------------------------------------------------+
|                                                                                |
|          +-------------------+                                                 |
|          |      CLOSED       | <--------------------+                          |
|          | (Normal Operation)|                      |                          |
|          +-------------------+                      |                          |
|                    |                                |                          |
|         3 Consecutive Failures                      |                          |
|                    |                        2 Consecutive Successes            |
|                    v                                |                          |
|          +-------------------+                      |                          |
|          |       OPEN        |                      |                          |
|          | (Fail Fast Block) |                      |                          |
|          +-------------------+                      |                          |
|                    |                                |                          |
|           30.0s Cooldown Elapsed                    |                          |
|                    |                                |                          |
|                    v                                |                          |
|          +-------------------+                      |                          |
|          |     HALF_OPEN     | ---------------------+                          |
|          |  (Probe In-Flight)|                                                 |
|          +-------------------+                                                 |
|                    |                                                           |
|             1 Probe Failed                                                     |
|                    +--------------------------------+                          |
|                                                     |                          |
|                                                     v                          |
|                                           (Re-trip to OPEN)                    |
+--------------------------------------------------------------------------------+
```

---

## 2. State Machine Rules

### State 1: CLOSED (Healthy)
- Normal operational state.
- All requests are permitted to reach the provider.
- Failure counter increments on operational errors (network drop, 503, timeout).
- Successful request resets the consecutive failure counter to 0.

### State 2: OPEN (Failing / Tripped)
- Tripped when consecutive failures reach `failure_threshold = 3`.
- **Zero Network Delay:** All incoming requests are rejected immediately ($<0.1$ms) with an informative message.
- Monotonic elapsed time is tracked using `time.monotonic()`, making cooldown calculations immune to system clock shifts.
- Default open duration: `open_duration_seconds = 30.0`.

### State 3: HALF_OPEN (Probe Verification)
- Entered automatically after the 30-second cooldown expires.
- Allows exactly 1 probe request (`half_open_probes = 1`) to test upstream service health.
- If the probe succeeds: `consecutive_successes` increments. Once it reaches `recovery_threshold = 2`, circuit closes completely.
- If the probe fails: Circuit immediately trips back to `OPEN` for another 30 seconds.

---

## 3. Strict Provider Isolation
Circuit breaker state is maintained independently per provider in `CircuitBreakerRegistry`:
- Tripping ChatGPT's circuit breaker has **zero effect** on Claude, Ollama, DeepSeek, or Gemini.
- Gemini Master Brain operates through its own Gateway and is never blocked by external provider circuit trips.

---

## 4. MCP Tools & Observability
- `get_circuit_breaker_status(provider_name)`: Inspect active states, consecutive failures, and remaining cooldown seconds.
- `reset_provider_health(provider_name)`: Authorized administrative tool to reset a tripped breaker back to `CLOSED`.
