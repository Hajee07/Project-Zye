# ZYE AI — Capability Security & Injection Scanner Validation

**Subsystem:** `zye_security` (`capabilities.py`, `injection_scanner.py`, `sanitizer.py`)  
**Specification:** Master Specification Section 26  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Autonomous tool dispatch and external data ingestion (e.g. web search results, documents, email) expose AI systems to prompt injection, jailbreaks, unauthorized filesystem access, and destructive shell execution.

---

## 2. Implemented Architecture

### 2.1 RBAC Capability Policy (`capabilities.py`)
- Fine-grained capability labels:
  - `FILE_READ`, `FILE_WRITE`, `NETWORK_FETCH`, `CODE_EXECUTE`, `MEMORY_READ`, `MEMORY_WRITE`, `TOOL_INVOKE`, `SCHEDULE_CREATE`, `SYSTEM_ADMIN`.
- Pattern-based resource matching using `fnmatch` (e.g. `scripts/safe_*.py`).
- **Fail-Closed Elevation Gate:** Privileged actions (`CODE_EXECUTE`, `SYSTEM_ADMIN`) strictly require explicit grants even when `default_deny=False`.
- Explicit denials always override grants.

### 2.2 Prompt Injection & Adversarial Scanner (`injection_scanner.py`)
Scans raw text against compiled vulnerability signatures:
1. **System Prompt Override:** `ignore all previous instructions`, `disregard instructions`.
2. **Identity Jailbreak:** `you are now DAN / unrestricted / jailbroken`.
3. **Destructive Shell Commands:** `; rm -rf`, `&& del /f`, `powershell -enc`.
4. **Path Traversal Traps:** `../../windows/system32`, `../../etc/passwd`.
5. **Hidden Delimiter Traps:** `<!-- system: override -->`.
- Detected violations emit `ZyeEventType.SECURITY_ALERT` on the Unified Event Bus.

### 2.3 Input Sanitizer (`sanitizer.py`)
Strips non-printable control characters (`\x00-\x1f`), normalizes line breaks, and enforces safe length bounds.

---

## 3. Test Evidence

```
tests/test_security_capabilities.py::test_capability_policy_permissions_and_denial PASSED [ 33%]
tests/test_security_capabilities.py::test_injection_scanner_detects_malicious_prompts PASSED [ 66%]
tests/test_security_capabilities.py::test_input_sanitizer PASSED                           [100%]
```
- **CLI Verification:** `python doctor.py --skill-security-health` returned exit code 0.
