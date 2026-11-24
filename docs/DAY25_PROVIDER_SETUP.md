# Zye AI — Day 25: AI Provider Configuration & Setup Guide

This guide details how to configure API credentials, local models, and settings for each supported AI provider in the Zye Multi-AI Plugin Hub.

---

## 1. Supported Providers Overview

| Provider | ID | Default Model | Base URL | Auth Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **OpenAI / ChatGPT** | `openai` / `chatgpt` | `gpt-4o` | `https://api.openai.com/v1` | Bearer Token (`OPENAI_API_KEY`) |
| **Anthropic / Claude** | `anthropic` / `claude` | `claude-3-5-sonnet-20241022` | `https://api.anthropic.com/v1` | Header `x-api-key` (`ANTHROPIC_API_KEY`) |
| **Local Ollama** | `ollama` | `llama3.2` | `http://127.0.0.1:11434` | None (Local REST API) |
| **Perplexity** | `perplexity` | `sonar-pro` | `https://api.perplexity.ai` | Bearer Token (`PERPLEXITY_API_KEY`) |
| **DeepSeek** | `deepseek` | `deepseek-chat` | `https://api.deepseek.com` | Bearer Token (`DEEPSEEK_API_KEY`) |
| **Groq** | `groq` | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1` | Bearer Token (`GROQ_API_KEY`) |
| **OpenRouter** | `openrouter` | `anthropic/claude-3.5-sonnet`| `https://openrouter.ai/api/v1` | Bearer Token (`OPENROUTER_API_KEY`) |
| **Custom Provider** | `custom` | User Defined | User Defined (HTTPS) | Bearer Token (`CUSTOM_AI_API_KEY`) |

---

## 2. Environment Variables Setup (`.env`)

Add desired provider credentials to your `d:\Zye\.env` file:

```bash
# --- Optional Cloud AI Providers ---
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
PERPLEXITY_API_KEY=pplx-your-perplexity-key-here
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
GROQ_API_KEY=gsk_your-groq-key-here
OPENROUTER_API_KEY=sk-or-your-openrouter-key-here

# --- Local AI (Ollama - 100% Offline & Private) ---
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2

# --- Custom External AI Endpoint (Optional) ---
CUSTOM_AI_ENABLED=false
CUSTOM_AI_API_KEY=
CUSTOM_AI_BASE_URL=https://api.your-custom-endpoint.com/v1
CUSTOM_AI_MODEL=custom-model
```

---

## 3. Declarative TOML Configuration (`zye_config.toml`)

Granular timeouts, default models, and provider states can be tuned in `d:\Zye\zye_config.toml`:

```toml
[ai_plugins]
enabled = true
default_timeout_seconds = 60.0
ssrf_protection = true

[ai_plugins.chatgpt]
enabled = true
base_url = "https://api.openai.com/v1"
default_model = "gpt-4o"
timeout_seconds = 60.0

[ai_plugins.claude]
enabled = true
base_url = "https://api.anthropic.com/v1"
default_model = "claude-3-5-sonnet-20241022"
timeout_seconds = 60.0

[ai_plugins.ollama]
enabled = true
base_url = "http://127.0.0.1:11434"
default_model = "llama3.2"
timeout_seconds = 90.0

[ai_plugins.perplexity]
enabled = true
base_url = "https://api.perplexity.ai"
default_model = "sonar-pro"
timeout_seconds = 60.0

[ai_plugins.deepseek]
enabled = true
base_url = "https://api.deepseek.com"
default_model = "deepseek-chat"
timeout_seconds = 60.0

[ai_plugins.groq]
enabled = true
base_url = "https://api.groq.com/openai/v1"
default_model = "llama-3.3-70b-versatile"
timeout_seconds = 45.0

[ai_plugins.openrouter]
enabled = true
base_url = "https://openrouter.ai/api/v1"
default_model = "anthropic/claude-3.5-sonnet"
timeout_seconds = 60.0

[ai_plugins.council]
enabled = true
default_members = ["chatgpt", "claude"]
min_quorum = 2
```

---

## 4. Privacy-First Local Execution (Ollama Setup)

For 100% offline, cloud-free, zero-token cost execution:
1. Download and install Ollama from [https://ollama.com](https://ollama.com).
2. Pull desired models in your terminal:
   ```bash
   ollama pull llama3.2
   ollama pull mistral
   ollama pull deepseek-r1
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```
4. Zye AI automatically connects to `http://127.0.0.1:11434` and queries local models whenever `ask_local_ollama()` is invoked. No API key is required.
