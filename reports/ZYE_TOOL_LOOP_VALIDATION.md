# ZYE AI — Tool Loop Guard & Degenerate Cycle Validation

**Subsystem:** `zye_reliability` (`tool_loop_guard.py`, `verified_execution.py`)  
**Specification:** Master Specification Section 08 & Section 18  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Autonomous agents and voice tool-callers frequently encounter degenerate failure loops when tools return unexpected responses:
1. **A-A-A Repetition:** Repeatedly calling the exact same tool with identical arguments (e.g., repeatedly polling a file or running a failed command).
2. **A-B-A-B Oscillation:** Ping-pong switching between two tools that invalidate each other's assumptions.
3. **Turn Runaway:** Exceeding acceptable tool budgets within a single conversational turn, leading to high latency and context bloat.
4. **False Success Hallucinations:** Agent claiming an action was completed when the underlying tool returned an error or silent failure.

---

## 2. Engineering Solution

### 2.1 Canonical Tool Fingerprinting
`tool_fingerprint(server, tool_name, arguments)` normalizes arguments by sorting dictionary keys and serializing to compact JSON, then generating a 16-character SHA-256 fingerprint:
```python
raw_key = f"{server.strip().lower()}:{tool_name.strip().lower()}:{norm_args}"
return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
```
Ensures different argument ordering produces identical fingerprints, eliminating false misses.

### 2.2 Loop Guard Policies
- **Max Identical Calls:** 3 (4th call warns, 5th hard blocks with `ExecutionOutcome.LOOP_BLOCKED`).
- **Ping-Pong Detection:** Sliding window of 6 inspects period-2 (A-B-A-B) and period-3 (A-B-C-A-B-C) repeating sequences.
- **Turn Budget:** Maximum 4 tool calls per user turn (polling tools granted relaxed budget of 8).
- **Warn-Before-Block:** Issues first-chance warning on initial trigger to permit autonomous course correction before hard blocking.

### 2.3 Verified Tool Execution Lifecycle
Every tool execution transitions through an audited state machine:
`REQUESTED` $\rightarrow$ `AUTHORIZED` $\rightarrow$ `STARTED` $\rightarrow$ `VERIFIED_SUCCESS` / `FAILED`

`verify_result(step, raw_result)` prevents false success by checking:
- `None` or empty results where output is required.
- Result dictionaries with `isError: true` or `status: "failed"`.
- Output strings beginning with `error:`, `exception:`, or non-zero exit codes.

---

## 3. Test Evidence

```
tests/test_tool_loop_guard.py::test_tool_fingerprint_deterministic_and_canonical PASSED [ 20%]
tests/test_tool_loop_guard.py::test_loop_guard_blocks_aaa_repeated_calls PASSED         [ 40%]
tests/test_tool_loop_guard.py::test_loop_guard_ping_pong_detection PASSED              [ 60%]
tests/test_tool_loop_guard.py::test_turn_tool_budget_enforcement PASSED               [ 80%]
tests/test_tool_loop_guard.py::test_verified_execution_anti_hallucination PASSED       [100%]
```
- **CLI Verification:** `python doctor.py --tool-loop-test --trace-health` returned exit code 0.
