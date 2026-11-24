# ZYE AI — DAY 27 ARCHITECTURE AUDIT & PRE-IMPLEMENTATION ANALYSIS

**Date:** November 21, 2026  
**Auditor:** Principal AI Systems & Reliability Architect  
**Project:** Zye AI Hybrid Assistant  
**Status:** Pre-Implementation Phase  

---

## 1. Existing System Architecture Overview
The Zye AI system is organized into modular subsystems under `d:\Zye`:
- **Core Orchestrator (`main.py`):** Houses `ZyeMCPOperationOrchestrator`, `ZyeHybridAssistant`, `SafetyExecutionGateway`, background task management, Edge-TTS speech coordinator, PortAudio/Silero-VAD listening ear, and prefix-based tool routing.
- **Gemini Master Brain (`zye_brain/gemini_agent.py`, `zye_brain/gemini_gateway.py`):** Houses the 7-key multi-project rotation system, quota tracker, model quality selector (`LOW` / `MEDIUM` / `HIGH`), and system persona instructions.
- **Multi-AI Plugin Hub (Day 25):** FastMCP server (`ai_plugins_mcp.py`) exposing 16 base tools, `ProviderRegistry` managing 10 configured providers (OpenAI, Anthropic, Ollama, Perplexity, DeepSeek, Groq, OpenRouter, Custom), SSRF validator, secret masking, and `UsageTracker`.
- **Advanced AI Council (Day 26):** Expanded `ai_plugins_mcp.py` to 25 tools, added `AICouncilEngine` with 4-round peer deliberation, `claim_extractor.py`, `disagreement_detector.py`, `consensus_analyzer.py`, `council_evaluator.py`, `decision_engine.py` (MCDA), `evidence_analyzer.py`, and `council_report.py`.
- **Operating System & Office Subsystems:** `windows_control_mcp.py`, `office_master_mcp.py`, `browser_accounts_mcp.py`.

---

## 2. Existing Provider Adapters & Configuration
- **Adapters:**
  - `openai_adapter.py`: OpenAI API (`gpt-4o`, `gpt-4o-mini`, `o1`).
  - `anthropic_adapter.py`: Anthropic Messages API (`claude-3-5-sonnet`, `claude-3-haiku`).
  - `ollama_adapter.py`: Local Ollama REST API (`llama3.2`, `deepseek-r1`, etc.) via `http://localhost:11434`.
  - `openai_compatible_adapter.py`: Generic OpenAI-compatible endpoints used by Perplexity, DeepSeek, Groq, OpenRouter, and Custom endpoints.
- **Base Provider (`provider_base.py`):**
  - Defines abstract `BaseAIProvider` with `generate_response()`, `check_health()`, `list_models()`, `get_metadata()`.
  - Maintains `_client: httpx.AsyncClient` with `limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)` and `timeout_seconds = 45.0`.
- **Configuration (`provider_config.py`):**
  - Reads environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_URL`, etc.).
  - Pydantic models for single and master configs.

---

## 3. Existing Gemini Master Brain Integration & Sovereign Authority
- **Sovereignty Law:** External AI providers are strictly subordinate advisors. Gemini Master Brain is the sole, unchallenged Supreme Arbiter.
- **Gateways:** `zye_brain/gemini_gateway.py` manages 7 independent API key slots (`GEMINI_API_KEY_01` through `GEMINI_API_KEY_07`) with request allocation and quota tracking.
- **No Gemini Bypass:** Day 27 must never replace, duplicate, or alter the 7-key manager or appoint external models to replace Gemini.

---

## 4. Existing Council Workflow (Day 26)
- **Deliberation Pipeline:**
  1. *Round 1 (Independent):* Concurrent requests dispatched via `asyncio.gather(*tasks)`.
  2. *Round 2 (Cross-Critique):* In `DEEP_COUNCIL` mode, models critique anonymized peer proposals.
  3. *Round 3 (Revised Position):* Contradiction & disagreement matrices built.
  4. *Round 4 (Supreme Arbiter Dossier):* Multi-criteria weighted scoring synthesized and handed off to Gemini.
- **Current Concurrency Implementation:**
  - Uses raw `asyncio.gather(*tasks, return_exceptions=True)` without per-provider rate limiting, semaphores, or backpressure.
  - If a provider is slow or hanging, the entire gather waits until timeout.

---

## 5. Existing HTTP Connection Management & Retry Policies
- **HTTP Client Management:**
  - Each `BaseAIProvider` instance holds an independent `httpx.AsyncClient`.
  - Keep-alive is set to 5 connections, max 10 connections.
  - No global connection pooling or bulkhead isolation across providers.
- **Retry Policies:**
  - Currently, requests in provider adapters execute in a single try/except block.
  - No exponential backoff, jitter, or `Retry-After` header parsing.
  - Errors are caught and returned as `AIResponse(status="error", error_message=...)`.
- **Rate-Limit Handling:**
  - 429 errors from providers are simply logged as error strings. No token buckets or cooldown locks exist.

---

## 6. Existing Usage Tracking & Health Monitoring
- **`usage_tracker.py`:**
  - `ProviderMetrics` tracks: `request_count`, `success_count`, `failure_count`, `timeout_count`, token counts, and min/max/total latency.
  - In-memory thread-safe dictionary.
  - Missing: Rolling observation windows (1h, 24h, 7d), percentile latencies (p50, p95, p99), cost estimation, reliability ranking with sample confidence.
- **`provider_health.py`:**
  - Non-billable `check_health()` pinging `/models` or `/health` endpoints.
  - Missing: Formal health state taxonomy (CONFIGURED, AVAILABLE, DEGRADED, RATE_LIMITED, CIRCUIT_OPEN, AUTH_FAILED, DISABLED, UNKNOWN), active circuit-breaker states.

---

## 7. Gap Analysis: Missing Day 27 Features
1. **Intelligent Provider Router:** No dynamic provider selection based on mode (BALANCED, QUALITY_FIRST, SPEED_FIRST, COST_FIRST, RELIABILITY_FIRST, LOCAL_ONLY, USER_SELECTED, COUNCIL_MODE, PRIVACY_RESTRICTED).
2. **Circuit Breaker:** No 3-state (CLOSED, OPEN, HALF_OPEN) circuit breaker per provider with monotonic time and failure thresholds.
3. **Advanced Retry Engine:** No retry policy with exponential backoff, full jitter, classification of transient vs permanent errors, and `Retry-After` support.
4. **Rate Limiting & Cooldowns:** No rate limiter tracking request/token quotas and provider-specific cooldowns.
5. **Adaptive Concurrency & Bulkhead Isolation:** No per-provider semaphores, bounded request queues, or failure isolation.
6. **Cost Estimator:** No rate-card pricing metadata per model (input/output tokens) or cost reporting.
7. **Reliability Ranking & Telemetry:** No sample-size weighted reliability ranking or rolling window metrics (P50, P95, P99).
8. **Performance Benchmarking:** No synthetic test harness for latency, throughput, and recovery benchmarking.
9. **Automatic Provider Failover:** No graceful failover to eligible fallback providers when an unpinned provider fails.

---

## 8. Reusable Assets & Anti-Conflict Strategy
- **Reusability:**
  - Reuse `BaseAIProvider` and existing adapters without destructive modifications.
  - Reuse `SingleProviderConfig` and `AIPluginMasterConfig`.
  - Reuse `UsageTracker` and enhance with persistent telemetry.
  - Reuse FastMCP server in `ai_plugins_mcp.py`.
- **Anti-Conflict Strategy:**
  - Keep all Day 27 subsystems organized cleanly in modular packages under `zye_ai_plugins/`:
    - `zye_ai_plugins/routing/` (router, policy)
    - `zye_ai_plugins/resilience/` (circuit breaker, retry policy, rate limiter, concurrency controller, bulkhead)
    - `zye_ai_plugins/telemetry/` (health, metrics, cost estimator)
    - `zye_ai_plugins/benchmarking/` (runner, profiles)
  - Ensure all Day 25 & Day 26 public APIs in `zye_ai_plugins/__init__.py` and tools in `ai_plugins_mcp.py` maintain 100% backward compatibility.
  - Strictly preserve Windows sandbox test execution rules (avoid raw `asyncio.run()` in unit test files to prevent Windows loopback socket deadlocks).

---

## 9. Minimal Implementation Plan
1. **Modular Architecture Setup:**
   - Create directories `zye_ai_plugins/routing/`, `zye_ai_plugins/resilience/`, `zye_ai_plugins/telemetry/`, `zye_ai_plugins/benchmarking/`.
2. **Resilience Layer:**
   - `circuit_breaker.py`: 3-state circuit breaker per provider with monotonic time.
   - `retry_policy.py`: Transient vs permanent error classifier, exponential backoff, jitter, retry-after.
   - `rate_limiter.py`: Lightweight token bucket rate limiter per provider.
   - `concurrency_controller.py`: Bounded semaphores and queue management.
   - `bulkhead.py`: Provider isolation manager wrapping client requests.
3. **Telemetry & Cost Layer:**
   - `cost_estimator.py`: Model pricing metadata, cost estimation, token accounting.
   - `provider_health.py`: Extended state machine (CONFIGURED, AVAILABLE, DEGRADED, RATE_LIMITED, CIRCUIT_OPEN, AUTH_FAILED, DISABLED, UNKNOWN).
   - `provider_metrics.py`: Rolling observation window statistics, P50/P95/P99 latency calculations, and reliability ranking.
4. **Routing Layer:**
   - `routing_policy.py`: Routing modes and priority scoring.
   - `provider_router.py`: Intelligent provider selection, fallback resolver, capability validation, and decision explanation.
5. **Benchmarking Layer:**
   - `benchmark_profiles.py` & `benchmark_runner.py`: Synthetic test harness for latency, concurrency, and reliability benchmarks.
6. **Integration with MCP, Orchestrator & Persona:**
   - Wire tools into `ai_plugins_mcp.py` (total 40 FastMCP tools).
   - Wire routing in `main.py` and voice commands in `gemini_agent.py`.
   - Integrate with `ai_council.py` to route through the resilience layer.
7. **Doctor Diagnostics:**
   - Implement Stage 23 in `doctor.py` (`--day27-check`).
8. **Testing & Certification:**
   - Write unit test suites, run regression tests, benchmark suite, generate docs, and final reports.
