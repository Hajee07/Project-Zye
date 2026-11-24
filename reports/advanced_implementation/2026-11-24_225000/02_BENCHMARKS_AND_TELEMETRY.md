# ZYE AI — BENCHMARKS, TIMING INSTRUMENTATION & TELEMETRY

**Measured On:** Windows 10/11 x64  
**Runtime:** Python 3.12 (venv)  
**Evidence Timestamp:** 2026-11-24 23:35:00 IST  

---

## 1. Acoustic & Audio Pipeline Benchmarks

| Metric | Pre-Repair Baseline | Post-Repair Result | Target Requirement | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Barge-in Trigger Latency** | 160 ms (5 frames) | **~64 ms (2 frames)** | < 100 ms | **EXCEEDED** |
| **Barge-in Threshold (RMS)** | 2800 RMS | **2200 RMS** | < 2500 RMS | **PASS** |
| **Full-Duplex Speech Admission** | 0% (blocked by half-duplex safety) | **100% (1200 RMS admitted during speech)** | Admitted | **PASS** |
| **Turn Stall Rate** | 100% after tool execution | **0.0% (`_turn_tool_requested` cleared)** | 0% | **PASS** |
| **Physical Write Telemetry (T10)** | Identical to T8 (arrival) | **Measured from `last_write_timestamp_ns`** | Disentangled | **PASS** |

---

## 2. Event Bus & Concurrency Benchmarks

| Metric | Pre-Repair Baseline | Post-Repair Result | Target Requirement | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Slow Listener First Publish Delay** | 60.45 ms (blocked synchronous caller) | **25.18 ms (capped at budget)** | < 30 ms | **PASS** |
| **Slow Listener Subsequent Delay** | 60.45 ms | **0.07 ms (queued to background worker)** | < 1 ms | **EXCEEDED** |
| **History Bounded Capacity** | 1000 items | **1000 items (FIFO deque eviction)** | Memory-safe | **PASS** |
| **Secret Redaction Latency** | 0.02 ms | **0.02 ms (regex token masking)** | < 0.1 ms | **PASS** |

---

## 3. Reliability & Memory Performance

| Metric | Pre-Repair Baseline | Post-Repair Result | Target Requirement | Status |
| :--- | :--- | :--- | :--- | :--- |
| **In-Memory Fact Store Retention** | Crashed (`OperationalError`) | **Persistent `_shared_conn` with `RLock`** | Schema survives | **PASS** |
| **Task Failure Settlement** | False `completed` status | **Recorded `status = 'failed'` with error** | Truthful | **PASS** |
| **Resource Governor Hysteresis** | Flapped to `NORMAL` at 79% RAM | **Latched in `RECOVERING` until RAM < 78%** | No thrashing | **PASS** |
| **Gemini 429 Retry-After Delay** | Truncated 120s to 60s | **128.60s (120s + jitter)** | >= Provider wait | **PASS** |

---

## 4. MCP Stdio Tool Discovery

| Stdio Server | Protocol Version | Discovered Tools | Schema Preserved |
| :--- | :--- | :--- | :--- |
| `computer_intelligence_mcp.py` | `2025-11-25` | **66 tools** | `input_schema` & `schema` |
| `self_repair_mcp.py` | `2025-11-25` | **12 tools** | `input_schema` & `schema` |
| `external_mcp/spotify-mcp-server` | `2024-11-05` (JSON-RPC 2.0) | **10 tools** | Non-blocking queue reader |
