# ZYE AI — Resource Governor & Local AI Optimization Report

**Subsystem:** `zye_reliability` (`resource_governor.py`), `zye_intelligence` (`local_readiness.py`)  
**Specification:** Master Specification Section 27  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Running local LLM inference (e.g. Ollama, llama.cpp) on personal Windows workstations without hardware gating risks thrashing, OOM crashes, audio dropout in Gemini Live, and OS instability.

---

## 2. Implemented Architecture

### 2.1 Hysteresis Resource Governor
- **Monitored Metrics:** Host Virtual Memory (psutil), CPU utilization, and system root drive disk usage.
- **States:**
  - `NORMAL`: RAM $< 80\%$ and CPU $< 90\%$.
  - `RESOURCE_PRESSURE`: RAM $\ge 80\%$.
  - `HIGH_MEMORY_PRESSURE`: RAM $\ge 88\%$. Strictly blocks all local model loading and heavy background workers.
  - `DEGRADED`: CPU $\ge 90\%$.
  - `RECOVERING`: Memory dropped below 88% but remains $\ge 78\%$.
- **Hysteresis Boundary:** Once memory pressure is triggered, the governor refuses to return to `NORMAL` until RAM drops strictly below **78%**, preventing rapid flapping/thrashing.

### 2.2 Hardware-Aware Local Readiness
`LocalReadinessDetector` evaluates:
1. Physical RAM & available RAM headroom.
2. CPU core count.
3. NVIDIA GPU existence and VRAM via `nvidia-smi`.
4. Ollama and llama-cpp runtime availability.
5. **Strict Gate:** If `ResourceGovernor` reports `HIGH_MEMORY_PRESSURE` or `RESOURCE_PRESSURE`, local inference is rejected and ZYE falls back immediately to **Gemini Master Brain**.

---

## 3. Real-World Live Host Validation

Executing `python doctor.py --resource-health --local-model-readiness` on the active workstation produced real observable evidence:
- **Host RAM Utilization:** **94.7%** (852 MB available of 15.7 GB).
- **Governor State:** `HIGH_MEMORY_PRESSURE`.
- **NVIDIA GPU:** Detected (6,141 MB VRAM).
- **Ollama Runtime:** Installed.
- **Admission Gate:** **PROTECTED / REJECTED**  
  `Local model inference rejected: Host RAM is 94.7% (exceeds 88.0% limit). Falling back to Gemini Master Brain.`

The 88% memory protection gate successfully intercepted and prevented local inference from crashing the memory-constrained host, routing seamlessly to Gemini Cloud.

---

## 4. Test Evidence

```
tests/test_resource_governor.py::test_resource_governor_hysteresis_state_machine PASSED                [ 25%]
tests/test_resource_governor.py::test_resource_governor_blocks_local_inference_at_high_pressure PASSED [ 50%]
tests/test_resource_governor.py::test_local_readiness_fails_closed_under_memory_pressure PASSED        [ 75%]
tests/test_resource_governor.py::test_hybrid_router_selects_gemini_and_handles_circuit_failover PASSED [100%]
```
