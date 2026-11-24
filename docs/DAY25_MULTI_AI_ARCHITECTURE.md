# Zye AI — Day 25: Universal Multi-AI Plugin Hub Architecture

**Version:** 1.0 (Day 25 Milestone)  
**Phase:** 2 — Windows OS Control, MS Office Automation & Multi-AI Integration  
**Date:** 2026-11-21  
**Lead Architect:** Principal AI Systems Architect

---

## 1. Architectural Philosophy: The Supreme Arbiter Model

Zye AI operates on a strict **Hierarchical Supreme Arbiter** architecture.

```
                     +---------------------------------------+
                     |         USER SPEECH & COMMANDS        |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |    GEMINI MASTER BRAIN (SUPREME)      |
                     |  - Intent Parsing & Autonomous Action |
                     |  - Tool Selection & Orchestration     |
                     |  - Final Synthesis & Voice Generation |
                     |    (Edge-TTS: en-IN-NeerjaNeural)     |
                     +---------------------------------------+
                                         |
             +---------------------------+---------------------------+
             |                                                       |
             v                                                       v
+--------------------------+                               +--------------------------+
|  OS & OFFICE MCP SERVERS |                               |  MULTI-AI PLUGIN HUB MCP |
| - windows_control_mcp    |                               |  (ai_plugins_mcp.py)     |
| - system_os_mcp          |                               +--------------------------+
| - office_master_mcp      |                                             |
| - browser_accounts_mcp   |                    +------------------------+------------------------+
+--------------------------+                    |                        |                        |
                                                v                        v                        v
                                    +--------------------+   +--------------------+   +--------------------+
                                    |     CHATGPT API    |   |     CLAUDE API     |   |    LOCAL OLLAMA    |
                                    |  (OpenAIAdapter)   |   | (AnthropicAdapter) |   |  (OllamaAdapter)   |
                                    +--------------------+   +--------------------+   +--------------------+
                                                |                        |                        |
                                                +------------------------+------------------------+
                                                                         |
                                                                         v
                                                            +--------------------------+
                                                            |  NORMALIZED AIResponse   |
                                                            |  Returned to Gemini for  |
                                                            |  Decision & Spoken Voice |
                                                            +--------------------------+
```

### 1.1 Non-Negotiable Core Tenet
**Google Gemini is the permanent, unchallenged Master Brain.**
- External AI models (ChatGPT, Claude, Perplexity, DeepSeek, Groq, OpenRouter) and local models (Ollama) **NEVER** replace Gemini as the assistant's executive brain.
- External providers are strictly pluggable tools invoked via FastMCP tool calls when:
  1. The user explicitly requests a specific model (e.g., *"Ask ChatGPT to write a Python script"*, *"Ask Claude to review this architecture"*).
  2. The user initiates multi-model deliberation via the AI Council (*"Compare ChatGPT and Claude on this design decision"*).
  3. The user mandates 100% offline local-only operation (*"Use Ollama for this query"*).
- All responses from external models return as structured data to Gemini. Gemini performs synthesis, validates claims, applies safety boundaries, and outputs the final speech through Edge-TTS (`en-IN-NeerjaNeural`).

---

## 2. Subsystem Architecture (`zye_ai_plugins/`)

The Day 25 Multi-AI Plugin Hub is organized into clean, single-responsibility modules:

| Module | Purpose |
| :--- | :--- |
| `provider_base.py` | Abstract base class `BaseAIProvider` with unified async connection pooling (`httpx.AsyncClient`) and non-billable health checks. |
| `provider_config.py` | Pydantic schemas (`AIPluginMasterConfig`, `SingleProviderConfig`) with declarative TOML loading and environment overrides. |
| `response_normalizer.py` | Standardized `AIResponse` and `AIUsage` data structures normalizing status, token consumption, latency, and metadata. |
| `plugin_security.py` | Zero-trust security layer providing SSRF private subnet defense, HTTPS enforcement, loopback isolation, API key masking, and prompt redaction. |
| `openai_adapter.py` | Dedicated adapter for OpenAI Chat Completions API (`POST /v1/chat/completions`) and dynamic model listing (`GET /v1/models`). |
| `anthropic_adapter.py` | Dedicated adapter for Anthropic Messages API (`POST /v1/messages`) with text block extraction and token accounting. |
| `ollama_adapter.py` | Dedicated adapter for Local Ollama REST API (`POST /api/chat`, `GET /api/tags`), zero cloud exposure, 100% private. |
| `openai_compatible_adapter.py`| Universal REST adapter powering Perplexity, DeepSeek, Groq, OpenRouter, and user-defined endpoints with SSRF guards. |
| `ai_council.py` | `AICouncilEngine` orchestrating concurrent multi-model queries, partial failure recovery, and synthesis prompt generation. |
| `provider_health.py` | Non-billable health inspector executing diagnostic latency and availability pings across providers without consuming completion tokens. |
| `usage_tracker.py` | Thread-safe in-memory telemetry engine tracking request counts, success rates, token usage, and latency statistics. |
| `provider_registry.py` | Dynamic provider lifecycle registry managing alias resolution (`chatgpt` -> `openai`), discovery, and custom registration. |
| `ai_plugins_mcp.py` | Unified FastMCP server exposing 16 specialized tools to Gemini and the MCP Orchestrator. |

---

## 3. High-Performance Async REST Engine

All external and local network requests are powered by `httpx.AsyncClient` with persistent connection pooling:
- **Connection Reuse:** Max 5 keepalive connections per provider, up to 10 total connections, eliminating TCP handshake overhead.
- **Granular Timeouts:** 10-second connect timeout and configurable read/write timeouts (default 45-60s) to prevent thread exhaustion.
- **Non-Blocking Execution:** Completely asynchronous `asyncio` implementation compatible with FastMCP and the Zye Master MCP Orchestrator.

---

## 4. Zero-Trust Security & SSRF Protection

1. **Private Subnet Blocking:** The `validate_endpoint_url()` validator strictly blocks all private RFC1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS/GCP cloud metadata endpoints (`metadata.google.internal`).
2. **Loopback Isolation:** Loopback addresses (`127.0.0.1`, `localhost`, `::1`) are forbidden for all external/custom cloud providers and permitted *strictly* for the local Ollama adapter.
3. **HTTPS Mandatory for Cloud:** All remote AI endpoints must use encrypted HTTPS connections; plain HTTP is rejected.
4. **Credential Protection:** Secrets are masked via `mask_secret()` (exposing only prefix and last 4 characters, e.g. `sk-...7890`), preventing API key leakage in logs or chat artifacts.
5. **Prompt Redaction:** Outbound prompts pass through `sanitize_prompt()`, stripping exposed API keys (`AIzaSy...`, `sk-...`) before sending to external third-party models.
