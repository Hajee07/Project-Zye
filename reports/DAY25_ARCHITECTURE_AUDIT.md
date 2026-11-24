# ZYE AI — DAY 25 ARCHITECTURAL AUDIT & PRE-IMPLEMENTATION REPORT
**Document Reference:** `reports/DAY25_ARCHITECTURE_AUDIT.md`  
**System:** Zye AI Hybrid Autonomous Personal Assistant  
**Platform:** Windows 10 / Windows 11 x64  
**Date:** 2026-11-21  
**Auditor / Architect:** Principal Multi-Agent AI Architect & Systems Engineer  
**Status:** COMPLETE & CERTIFIED  

---

## 1. Executive Summary & Non-Negotiable Architecture Preservation Guarantee

An in-depth inspection of the existing Zye AI repository (`d:\Zye`) was performed to design and integrate the **Universal Multi-AI Plugin Hub** for Day 25.

### Absolute Architectural Rule
**GEMINI REMAINS THE UNCHALLENGED MASTER BRAIN.**  
All other AI providers (ChatGPT, Claude, Local Ollama, Perplexity, DeepSeek, Groq, OpenRouter, Custom Providers) are **optional sub-agents** accessed strictly as external tools through the FastMCP protocol.

Under **no circumstances** will any existing architectural layer be replaced or redesigned:
1. **Gemini Master Brain Preserved:** `zye_brain/gemini_agent.py` remains the primary reasoning, natural language understanding, and decision authority.
2. **Gemini Key Manager Preserved:** `gemini_gateway.py` with 7-project Google Cloud API key rotation remains exclusively dedicated to Gemini. No external keys (OpenAI, Anthropic, etc.) will ever be mixed into the Gemini key manager.
3. **Voice Engine & Persona Preserved:** Microsoft Edge-TTS (`en-IN-NeerjaNeural`) with Pygame audio playback remains the sole voice output. External AI responses are synthesized exclusively through Zye's voice.
4. **Microphone Hearing Preserved:** `zye_audio_ear.py` (PortAudio, Silero Neural VAD ONNX, AGC) remains the sole acoustic perception engine.
5. **MCP Orchestrator Preserved:** `zye_orchestrator/` and `main.py` remain the central tool execution, hot reload, and safety gateway. The new Multi-AI Hub integrates seamlessly as `ai_plugins_mcp.py`.

---

## 2. Complete Inventory of Existing Subsystems

| Subsystem | Primary Files | Status | Role in Day 25 Integration |
|---|---|---|---|
| **Host Orchestrator** | `main.py` | `PRESERVED & EXTENDED` | Hosts `ZyeMasterAgent` and server allowlist. `ai_plugins` registered in `MCP_SERVERS`. |
| **System Diagnostics** | `doctor.py` | `PRESERVED & EXTENDED` | Comprehensive diagnostic engine. Stage 21 added for Day 25 multi-AI verification. |
| **Gemini AI Brain** | `zye_brain/gemini_agent.py` | `PRESERVED & EXTENDED` | Master decision-maker. Receives external AI responses, performs synthesis, and outputs to voice. |
| **Gemini 7-Key Gateway** | `gemini_gateway.py` | `PRESERVED UNCHANGED` | 7-project rotation for Gemini API. Completely isolated from third-party provider keys. |
| **Voice Synthesis & Playback** | `zye_voice/`, `zye_tts.py` | `PRESERVED UNCHANGED` | Edge-TTS `en-IN-NeerjaNeural` speaks all synthesized outputs. |
| **Neural Audio Ear** | `zye_audio_ear.py` | `PRESERVED UNCHANGED` | 16 kHz Mono capture, Silero Neural VAD, 0.64s pre-roll buffer, AGC peak normalization. |
| **Safety Guard Engine** | `zye_guard.py` | `PRESERVED & REUSED` | Decorates all AI plugin FastMCP tools with `@zye_safe_skill`. |
| **Windows Desktop Control** | `windows_control_mcp.py` | `PRESERVED UNCHANGED` | Windows UI, workspace, virtual desktops, window management. |
| **Office COM Automation** | `office_master_mcp.py` | `PRESERVED UNCHANGED` | Live Word, Excel, PowerPoint, Outlook COM automation. |
| **Browser Intelligence** | `browser_accounts_mcp.py` | `PRESERVED UNCHANGED` | Persistent Chrome profile management, Playwright automation, DOM extraction. |
| **Multi-AI Plugin Hub (NEW)**| `ai_plugins_mcp.py`, `zye_ai_plugins/`| `NEW DAY 25 MODULE` | Lightweight async REST engine connecting ChatGPT, Claude, Ollama, Perplexity, DeepSeek, Groq, OpenRouter. |

---

## 3. Workflow Integration Architecture

### Normal Interaction Mode (Default)
```
User Speech ──> SmartAudioEar ──> ClarityGuard ──> Gemini Master Brain ──> Edge-TTS Voice
(No external third-party AI APIs called; 0 additional cost, 0 latency overhead)
```

### Individual AI Delegation Mode
```
User: "Zye, ChatGPT kitta indha code analyze panna sollu"
           │
           ▼
Gemini Master Brain (Identifies user intent to delegate to ChatGPT)
           │
           ▼ calls MCP tool: ask_chatgpt(prompt, system_role, model)
ai_plugins_mcp.py (OpenAI Adapter)
           │
           ▼ HTTPS REST POST /chat/completions
OpenAI API (ChatGPT)
           │
           ▼ JSON Response Normalized
ai_plugins_mcp.py
           │
           ▼ returns structured AI response
Gemini Master Brain (Interprets, verifies, and frames response)
           │
           ▼
Edge-TTS Voice Output (en-IN-NeerjaNeural)
```

### AI Council Mode (Parallel Multi-AI Comparison)
```
User: "ChatGPT and Claude rendu peraiyum kettu compare pannu"
           │
           ▼
Gemini Master Brain (Identifies multi-AI consensus request)
           │
           ▼ calls MCP tool: ai_council_compare(question, providers=["chatgpt", "claude"])
ai_plugins_mcp.py (AI Council Engine)
           ├── (Parallel Task 1) ──> OpenAI API (ChatGPT) ──> Response 1
           └── (Parallel Task 2) ──> Anthropic API (Claude) ──> Response 2
           │
           ▼ Aggregates, attributes, measures latencies & handles partial failures
ai_plugins_mcp.py
           │
           ▼ returns structured Council JSON
Gemini Master Brain (Synthesizes: agreements, disagreements, technical validation, final verdict)
           │
           ▼
Edge-TTS Voice Output (en-IN-NeerjaNeural)
```

### Local-Only Privacy Mode (Ollama Guarantee)
```
User: "Internet use pannaama Local Ollama-la indha text summarize pannu"
           │
           ▼
Gemini Master Brain (Recognizes local-only confidentiality constraint)
           │
           ▼ calls MCP tool: ask_local_ollama(prompt, model)
ai_plugins_mcp.py (Ollama Adapter)
           │
           ▼ HTTP REST POST http://127.0.0.1:11434/api/chat
Local Ollama Service (100% Local Device Execution)
           │ (Zero bytes transmitted outside localhost; external AI APIs strictly blocked)
           ▼
ai_plugins_mcp.py ──> Gemini Master Brain ──> Edge-TTS Voice
```

---

## 4. API Key & Security Isolation Architecture

| Key Identifier | Purpose | Storage & Management | Isolation Guarantee |
|---|---|---|---|
| `GEMINI_API_KEY_01` to `_07` | Google Gemini 7-Project Rotation | `gemini_gateway.py` / `gemini_key_manager.py` | **Strictly isolated.** Never shared with any third-party provider. |
| `OPENAI_API_KEY` | OpenAI ChatGPT API | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by `OpenAIAdapter`. Redacted from all logs and output. |
| `ANTHROPIC_API_KEY` | Anthropic Claude Messages API | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by `AnthropicAdapter`. Redacted from all logs and output. |
| `PERPLEXITY_API_KEY` | Perplexity Online Search AI | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by OpenAI-compatible adapter for Perplexity. |
| `DEEPSEEK_API_KEY` | DeepSeek AI API | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by OpenAI-compatible adapter for DeepSeek. |
| `GROQ_API_KEY` | Groq Ultra-Fast LPU Inference | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by OpenAI-compatible adapter for Groq. |
| `OPENROUTER_API_KEY` | OpenRouter Multi-Model Router | `.env` / Environment / `zye_ai_plugins/plugin_security.py` | Used only by OpenAI-compatible adapter for OpenRouter. |
| `OLLAMA_URL` | Local Ollama REST URL | `zye_config.toml` / `.env` (Default: `http://127.0.0.1:11434`) | No external keys; local connection only. |

### SSRF Protection Rules
- Custom providers require **HTTPS** unless explicitly targeting approved loopback addresses (`127.0.0.1`, `localhost`).
- Private IP subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and cloud metadata endpoints (`169.254.169.254`) are blocked for custom endpoints.

---

## 5. Lightweight Asynchronous REST Engine Architecture

To avoid bloated, conflicting vendor SDKs:
- Uses **`httpx.AsyncClient`** with connection pooling.
- Configurable per-provider timeouts:
  - OpenAI: 45.0s default
  - Anthropic: 45.0s default
  - Local Ollama: 60.0s default
  - Custom Providers: 30.0s – 60.0s configurable
- Bounded retries with exponential backoff and jitter for transient errors (HTTP 429, 500, 502, 503, 504).
- Safe cancellation without resource leaks.

---

## 6. Implementation Plan & Target Files

1. `zye_ai_plugins/`:
   - `provider_base.py`: Abstract base class and standard provider metadata.
   - `provider_config.py`: TOML/Environment configuration reader and validator.
   - `response_normalizer.py`: Uniform `AIResponse` dataclass/Pydantic schema across all providers.
   - `plugin_security.py`: Secret masking, SSRF validation, and sensitive data sanitization.
   - `openai_adapter.py`: Official OpenAI Chat Completions REST client.
   - `anthropic_adapter.py`: Official Anthropic Messages REST client.
   - `ollama_adapter.py`: Local Ollama REST client with model discovery.
   - `openai_compatible_adapter.py`: Generalized adapter for Perplexity, DeepSeek, Groq, OpenRouter, and Custom endpoints.
   - `provider_registry.py`: Dynamic registry managing active/disabled providers.
   - `provider_health.py`: Non-billable health checks and latency monitoring.
   - `usage_tracker.py`: Token usage, request metadata, and latency telemetry.
   - `ai_council.py`: Parallel multi-provider execution engine with partial failure resilience.
   - `__init__.py`: Package entry and exports.
2. `ai_plugins_mcp.py`: FastMCP server exposing all 16 MCP tools decorated with `@zye_safe_skill`.
3. `main.py`: Registration of `ai_plugins` in `MCP_SERVERS` and dispatcher.
4. `zye_config.toml`: `[ai_plugins]` configuration section.
5. `doctor.py`: Stage 21 diagnostic verification checks.
6. `tests/test_day25_*.py`: Comprehensive unit and mock integration test suite.
7. Documentation and final reports.
