# ZYE AI — DAY 26: COUNCIL SECURITY, PRIVACY & DEFENSIVE ARCHITECTURE

## 1. Security Architecture Principles
The Multi-AI Council operates across external third-party cloud APIs and local inference engines. To safeguard the host environment, user secrets, and data privacy, the Day 26 architecture enforces defense-in-depth across 5 operational boundaries.

---

## 2. Air-Gapped Local Privacy Mode (`LOCAL_COUNCIL`)
When sensitive code, proprietary databases, or private documents are analyzed:
- The user can command: *"Run a local council on this internal code"*.
- The council activates `LOCAL_COUNCIL` mode (`privacy_mode=True`).
- **Hard Cloud Barricade:** The council engine intercepts the provider list and forces `target_providers = ["ollama"]`.
- Calls to OpenAI, Anthropic, Perplexity, DeepSeek, Groq, or OpenRouter are structurally blocked.
- Only loopback endpoint `http://127.0.0.1:11434` is contacted.

---

## 3. Server-Side Request Forgery (SSRF) Protection
All HTTP requests route through the Day 25 SSRF Validator (`zye_ai_plugins.ssrf_validator`):
- **Cloud Providers:** Must resolve to valid public IPv4/IPv6 addresses via HTTPS (`https://`).
- **Subnet Blocking:** Private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS metadata endpoints (`169.254.169.254`) are blocked.
- **Controlled Loopback:** Loopback (`127.0.0.1`, `localhost`) is strictly forbidden for all cloud providers and permitted *only* for the registered local Ollama adapter.

---

## 4. Credential Sanitization & Secret Masking
To prevent accidental leakage of sensitive tokens:
1. **Outbound Prompt Sanitization:** Outbound prompts dispatched to external models are scanned for regex patterns matching API keys (`sk-[a-zA-Z0-9]{32,}`, `ghp_[a-zA-Z0-9]{36}`, etc.) and redacted with `[REDACTED_API_KEY]`.
2. **Metadata Masking:** MCP inspection tools (`get_provider_metadata`, `get_ai_plugin_status`) mask secrets displaying only the first 3 characters and trailing ellipsis (`sk-ant...`). Empty keys are designated `[NOT_CONFIGURED]`.

---

## 5. Security Contradiction Gate
If any model in the Council detects a security vulnerability (e.g. SQL injection, unauthenticated endpoint, weak cryptography) that another model claims is safe:
- The Disagreement Detector classifies the conflict as **`CRITICAL` severity**.
- The Consensus Analyzer marks the status as **`CONTRADICTORY_POSITIONS`**.
- The Council Engine flags `requires_evidence_resolution = True`.
- Gemini Master Brain informs the user of the critical risk and requires **explicit confirmation** before any associated tool or automated change is executed.
