# ZYE AI — MCP Automation Security & Protection Protocol

## 1. Security Architecture

Automation of native Windows applications and personal web accounts requires strict, non-bypassable security controls.

---

## 2. Core Security Invariants

1. **Negative Pre-Mortem Gate**:
   Every tool execution is evaluated for failure modes, data loss risks, and irreversible side effects prior to execution (`ZyeNegativePreMortem`).
2. **Two-Stage Destructive Operation Gating**:
   Irreversible actions (sending messages, making calls, deleting files, process termination) cannot be triggered by a single intent. They require explicit confirmation flags (`confirmed=True`).
3. **Prompt Injection Boundary**:
   Untrusted text extracted from web pages or external documents is wrapped in `<untrusted_content>` delimiters with executable script neutralization.
4. **Credential Isolation**:
   All 7 Gemini API keys and credentials are encrypted at rest and masked in memory logs (`mask_credential`).
