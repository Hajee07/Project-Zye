# OpenJarvis to ZYE AI Component Mapping & Strategy Report

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Reference Source:** `D:\Zye\references\OpenJarvis-main\`  
**Target Architecture:** ZYE Python Assistant (`main.py`, `zye_core/`, `zye_guard.py`, `zye_intelligence/`)  
**Status:** ALL 44 CORE REFERENCE MODULES CLASSIFIED  

---

## 1. Component Classification Matrix

| OpenJarvis Reference Path | Target ZYE Location | Classification | Integration Rationale & Acceptance Test |
| :--- | :--- | :--- | :--- |
| `src/openjarvis/core/events.py` | `zye_core/event_bus.py` | **ADAPT_TO_ZYE** | Adapt thread-safe pub/sub event bus with bounded history to coordinate ZYE subsystems without blocking Gemini receive loop. Tested via `test_event_bus.py`. |
| `src/openjarvis/core/config.py` | `zye_config.toml` | **ALREADY_IMPLEMENTED_IN_ZYE** | ZYE uses TOML configuration with atomic loading and validation. Extend with `[openjarvis_upgrade]` section. |
| `src/openjarvis/core/registry.py` | `zye_core/model_registry.py` | **ADAPT_TO_ZYE** | Model capability registry tracking text, native audio, tool calls, and circuit-breaker states. |
| `src/openjarvis/core/types.py` | `zye_core/types.py` | **ADAPT_TO_ZYE** | Shared dataclasses for event envelopes, turn contexts, and verified execution outcomes. |
| `src/openjarvis/core/credentials.py` | `zye_security/credentials.py` | **ADAPT_TO_ZYE** | Secret redactor & credential stripper to ensure API keys/tokens are never leaked in logs or traces. |
| `src/openjarvis/agents/loop_guard.py` | `zye_reliability/tool_loop_guard.py` | **ADAPT_TO_ZYE** | Canonical tool fingerprinting (`SHA-256`), A-A-A repetition detection, and A-B-A-B ping-pong loop prevention. Tested via `test_tool_loop_guard.py`. |
| `src/openjarvis/agents/orchestrator.py` | `zye_orchestrator.py` / `main.py` | **DESIGN_REFERENCE_ONLY** | ZYE already possesses its master MCP Orchestrator. Adapt timeout and lifecycle patterns only. |
| `src/openjarvis/agents/executor.py` | `zye_reliability/verified_execution.py`| **ADAPT_TO_ZYE** | Enforce verified execution states (`REQUESTED`, `AUTHORIZED`, `VERIFIED_SUCCESS`, etc.). |
| `src/openjarvis/engine/_base.py` | `zye_intelligence/engine_base.py` | **ADAPT_TO_ZYE** | Abstract base inference interface supporting Gemini Master Brain with optional local subordinate inference. |
| `src/openjarvis/engine/cloud.py` | `zye_intelligence/gemini_engine.py` | **ALREADY_IMPLEMENTED_IN_ZYE** | Existing 7-key Gemini API manager and Gemini Live remain primary. Strengthen with 503 recovery. |
| `src/openjarvis/engine/ollama.py` | `zye_intelligence/local_inference.py` | **OPTIONAL** | Subordinate local model caller, feature-flagged and resource-gated. Disabled when RAM is high. |
| `src/openjarvis/engine/multi.py` | `zye_intelligence/circuit_breaker.py` | **ADAPT_TO_ZYE** | Multi-engine failover circuit breaker with exponential backoff and half-open probing for 503 errors. |
| `src/openjarvis/intelligence/model_catalog.py`| `zye_intelligence/model_catalog.py` | **ADAPT_TO_ZYE** | Model capability metadata catalog mapping model IDs to verified multimodal/audio capabilities. |
| `src/openjarvis/learning/routing/router.py` | `zye_intelligence/hybrid_router.py` | **ADAPT_TO_ZYE** | Deterministic, explainable router keeping simple queries local and complex reasoning on Gemini. |
| `src/openjarvis/learning/routing/complexity.py` | `zye_intelligence/complexity.py` | **ADAPT_TO_ZYE** | Lightweight heuristic query complexity evaluator (token count, reasoning keywords, tool needs). |
| `src/openjarvis/learning/routing/heuristic_policy.py` | `zye_intelligence/hybrid_router.py` | **ADAPT_TO_ZYE** | Heuristic fallback routing policy prioritizing security and resource budgets. |
| `src/openjarvis/security/capabilities.py` | `zye_security/capabilities.py` | **ADAPT_TO_ZYE** | Fine-grained capability security system (`file:read`, `tool:invoke`, `system:modify`, etc.). |
| `src/openjarvis/security/runtime.py` | `zye_guard.py` | **ADAPT_TO_ZYE** | Integrate capability checks directly into existing `zye_guard.py` execution gate. |
| `src/openjarvis/security/audit.py` | `zye_security/audit.py` | **ADAPT_TO_ZYE** | Bounded security audit logger recording granted and blocked capability operations. |
| `src/openjarvis/security/credential_stripper.py` | `zye_security/sanitizer.py` | **ADAPT_TO_ZYE** | Redaction of Gemini keys, OpenAI tokens, and authorization bearer headers. |
| `src/openjarvis/security/injection_scanner.py` | `zye_security/injection_scanner.py` | **ADAPT_TO_ZYE** | Secondary heuristic scanner for indirect prompt injection in external tool/web content. |
| `src/openjarvis/security/file_policy.py` | `zye_security/file_policy.py` | **ADAPT_TO_ZYE** | Safe path traversal prevention, canonicalizing paths and blocking access outside allowed scopes. |
| `src/openjarvis/security/ssrf.py` | `zye_security/ssrf.py` | **ADAPT_TO_ZYE** | Block private subnet / loopback SSRF targeting sensitive internal services. |
| `src/openjarvis/security/taint.py` | `zye_security/taint.py` | **ADAPT_TO_ZYE** | Taint tracking marking external content (web, documents) as untrusted data, never instructions. |
| `src/openjarvis/security/subprocess_sandbox.py` | `zye_guard.py` | **DESIGN_REFERENCE_ONLY** | ZYE uses Windows process automation with verification. Adapt safety boundary checks. |
| `src/openjarvis/memory/service.py` | `zye_memory/memory_service.py` | **ADAPT_TO_ZYE** | Non-blocking background fact extraction worker using bounded queues. Never blocks voice turns. |
| `src/openjarvis/memory/store.py` | `zye_memory/memory_store.py` | **ADAPT_TO_ZYE** | SQLite-backed persistent memory store with provenance, update timestamps, and user deletion. |
| `src/openjarvis/memory/extractor.py` | `zye_memory/fact_extractor.py` | **ADAPT_TO_ZYE** | Rule- and pattern-based fact extraction parsing durable user preferences without saving keys. |
| `src/openjarvis/scheduler/scheduler.py` | `zye_scheduler/task_scheduler.py` | **ADAPT_TO_ZYE** | SQLite-persisted autonomous scheduler for one-time and recurring background tasks with leases. |
| `src/openjarvis/scheduler/store.py` | `zye_scheduler/task_store.py` | **ADAPT_TO_ZYE** | Persistent SQLite task database storing schedules, statuses, and execution leases. |
| `src/openjarvis/skills/manager.py` | `zye_skills/skill_manager.py` | **ADAPT_TO_ZYE** | Manifest-based skill management with capability verification and integrity checksums. |
| `src/openjarvis/skills/security.py` | `zye_skills/skill_security.py` | **ADAPT_TO_ZYE** | Blocks untrusted execution steps, unreviewed shell commands, and privilege escalations. |
| `src/openjarvis/telemetry/` | `zye_telemetry/telemetry_engine.py` | **ADAPT_TO_ZYE** | Local-only system metrics: CPU, process RAM, available RAM, latency percentiles, queue depth. |
| `src/openjarvis/traces/collector.py` | `zye_telemetry/trace_collector.py` | **ADAPT_TO_ZYE** | Turn-scoped execution traces recording request latency, tool outcomes, and recovery decisions. |
| `src/openjarvis/mcp/client.py` | `zye_mcp_host.py` | **DESIGN_REFERENCE_ONLY** | ZYE already has production MCP client infrastructure. Adapt persistent connection patterns. |
| `src/openjarvis/mcp/transport.py` | `zye_mcp_host.py` | **ALREADY_IMPLEMENTED_IN_ZYE** | Stdio and SSE transports are active in Day 12 MCP orchestrator. |
| `desktop/src-tauri/src/overlay.html` | `desktop/overlay.html` | **ADAPT_TO_ZYE** | Minimalist floating HUD overlay with real-time waveform, listening status, and model health. |
| `src/openjarvis/server/ws_bridge.py` | `zye_desktop/ws_bridge.py` | **ADAPT_TO_ZYE** | Authenticated loopback WebSocket bridge (`ws://127.0.0.1:8765`) streaming sanitized state to HUD. |
| `frontend/src/` | `desktop/control_center/` | **DESIGN_REFERENCE_ONLY** | System Pulse and Trace Debugger visual patterns adapted into lightweight web control center. |
| `deploy/windows/install.ps1` | `deploy/install_zye_service.ps1` | **DESIGN_REFERENCE_ONLY** | Reference for interactive current-user scheduled task logon startup (Session 1, never Session 0). |
| `crates/*` (Rust crates) | `crates/` | **OPTIONAL / DEFERRED** | Optional Rust acceleration deferred until Python baseline benchmarks identify bottlenecks. |
| Mining / Training modules | N/A | **REJECTED_FOR_SECURITY_OR_RESOURCE_REASONS** | Unrelated cryptocurrency mining, unvetted RL training, and experimental training rejected. |

---

## 2. Key Architecture Principles Enforced
1. **ZYE is the Sole Master Brain:** No secondary autonomous agent runs in parallel.
2. **Fail-Closed Security:** External data is tainted; permissions are deny-by-default.
3. **Resource Awareness:** Local model loading is strictly deferred or rejected when RAM $> 88\%$.
4. **Deterministic Tool Gating:** Loop guard bounds repeated calls to max 3 per turn.
5. **No Blind Dependencies:** Zero untrusted packages installed; standard Python libraries prioritized.
