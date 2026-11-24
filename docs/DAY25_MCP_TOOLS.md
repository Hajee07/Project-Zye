# Zye AI — Day 25: Multi-AI Plugin Hub MCP Tool Reference

`ai_plugins_mcp.py` provides 16 production FastMCP tools organized into 5 functional categories:

---

## 1. Discovery & Metadata Tools

### `list_active_ai_plugins()`
Lists all currently active, configured, and enabled AI provider plugins available for delegation.
- **Returns:** `{status, active_providers_count, active_providers, total_registered, supreme_brain}`

### `get_ai_plugin_status()`
Retrieves operational status, configuration state, and connectivity summary for all known AI plugins.
- **Returns:** `{status, providers: [...], active_count, unconfigured_count, telemetry_active}`

### `get_provider_models(provider_name: str)`
Fetches the list of supported and dynamically discovered models for a specific AI provider.
- **Arguments:** `provider_name` (e.g., `"chatgpt"`, `"claude"`, `"ollama"`)
- **Returns:** `{status, provider_id, default_model, models_count, models: [...]}`

### `get_provider_metadata(provider_name: str)`
Retrieves architectural metadata, security profile, timeout, and masked credentials for a provider.
- **Arguments:** `provider_name`
- **Returns:** `{status, provider_id, display_name, base_url, default_model, is_configured, is_enabled, is_local, timeout_seconds, masked_key}`

### `check_provider_health(provider_name: str = "all")`
Runs low-overhead, non-billable latency and health checks on a specific provider or across all providers.
- **Arguments:** `provider_name` (default: `"all"`)
- **Returns:** `{status, health_summary / provider_health}`

---

## 2. Individual AI Delegation Tools

### `ask_chatgpt(prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None)`
Delegates a specialized question or task directly to ChatGPT (OpenAI API).
- **Arguments:**
  - `prompt`: The user's input prompt or instruction.
  - `system_prompt`: Optional system instruction.
  - `model`: Optional model override (defaults to `gpt-4o`).
  - `temperature`: Optional sampling temperature (defaults to 0.7).
  - `max_tokens`: Optional token limit.
- **Returns:** `AIResponse` dictionary `{provider_id, model, status, content, usage, latency_ms, error}`

### `ask_claude(prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None)`
Delegates a specialized question or task to Claude (Anthropic Messages API).
- **Arguments:** Same as `ask_chatgpt`, default model: `claude-3-5-sonnet-20241022`.
- **Returns:** `AIResponse` dictionary.

### `ask_local_ollama(prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None)`
Queries a locally running Ollama instance (100% offline, zero cloud exposure, privacy-first).
- **Arguments:** Same as `ask_chatgpt`, default model: `llama3.2`.
- **Returns:** `AIResponse` dictionary with `metadata.local = True`.

### `ask_custom_ai_plugin(provider_name: str, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, base_url: Optional[str] = None, api_key: Optional[str] = None)`
Delegates to any registered or custom AI provider (Perplexity, DeepSeek, Groq, OpenRouter, or custom URL) with SSRF checks.
- **Arguments:**
  - `provider_name`: Target provider (`"perplexity"`, `"deepseek"`, `"groq"`, `"openrouter"`, `"my_custom_llm"`).
  - `base_url`: Optional ad-hoc endpoint URL (must pass SSRF validation).
  - `api_key`: Optional ad-hoc bearer token.
- **Returns:** `AIResponse` dictionary.

---

## 3. AI Council Deliberation Tools

### `ai_council_compare(question: str, providers: Optional[List[str]] = None, focus_area: str = "general", max_tokens: int = 1024)`
Queries multiple AI providers in parallel, gathers diverse perspectives, and formats structured consensus report for Gemini.
- **Arguments:**
  - `question`: The subject matter or design problem to deliberate.
  - `providers`: List of providers to convene (defaults to `["chatgpt", "claude"]`).
  - `focus_area`: One of `"general"`, `"code"`, `"security"`, `"creative"`, `"fact_check"`.
  - `max_tokens`: Max tokens per member.
- **Returns:** `{success, question, focus_area, total_queried, successful_count, execution_time_ms, perspectives, synthesis_prompt_ready, supreme_arbiter}`

### `get_ai_council_status()`
Checks readiness of the AI Council, active members, quorum, and supreme arbiter status.
- **Returns:** `{council_ready, min_members_for_comparison, has_multimodal_consensus, active_members_count, available_members, unconfigured_members, supreme_arbiter}`

---

## 4. Configuration & Validation Tools

### `validate_ai_plugin_configuration(provider_name: str)`
Validates configuration parameters, credential presence, and SSRF safety for a provider.
- **Returns:** `{status, provider_id, valid, is_configured, is_endpoint_safe, has_api_key, base_url}`

### `validate_provider_model(provider_name: str, model_name: str)`
Checks whether a specific model name is recognized or supported by a given provider.
- **Returns:** `{status, provider_id, model_requested, is_valid, available_models}`

### `get_ai_plugin_configuration_status()`
Retrieves global configuration diagnostics across all AI plugins and environment status.
- **Returns:** `{status, total_providers, configured_count, providers_config: [...]}`

---

## 5. Usage Telemetry & Accounting Tools

### `get_provider_usage(provider_name: str)`
Retrieves token metrics, call counts, latency statistics, and error rates for a specific provider.
- **Returns:** `{status, usage: {provider_id, request_count, success_count, failure_count, success_rate, prompt_tokens, completion_tokens, total_tokens, avg_latency_ms, min_latency_ms, max_latency_ms}}`

### `get_provider_usage_summary()`
Retrieves aggregated token consumption and performance metrics across all AI providers.
- **Returns:** `{status, summary: {total_requests, total_success, total_failures, total_tokens_consumed, providers: {...}}}`
