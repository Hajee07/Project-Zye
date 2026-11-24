# Zye AI — Day 25 to Day 26 Continuity & Architecture Audit

**Project:** Zye AI Hybrid Personal Assistant  
**Milestone:** Day 26 — Advanced Multi-AI Council Intelligence Engine  
**Auditor:** Principal Multi-Agent AI Architect & Systems Specialist  
**Date:** 2026-11-21  
**Status:** Audit Complete — Pre-Implementation Blueprint Established  

---

## 1. Audit Objective

Prior to writing code for Day 26, this audit reviews the complete implementation of the Day 25 Multi-AI Plugin Hub (`zye_ai_plugins/` and `ai_plugins_mcp.py`), the existing Gemini Master Brain integration, and orchestrator hooks to ensure:
1. Zero duplication of existing provider infrastructure.
2. Uncompromised preservation of Gemini's Supreme Arbiter authority.
3. Clean, modular reuse of Day 25 connections, adapters, normalizers, and security layers.
4. Seamless integration of the multi-round AI Council, claim extraction, cross-critique, disagreement detection, and weighted decision evaluation.

---

## 2. Review of Existing Day 25 Components

### 2.1 Provider Adapters & Base Subsystems
- **`provider_base.py`:**
  - Implements `BaseAIProvider` with unified async connection pooling (`httpx.AsyncClient`).
  - Standardized `generate_response()`, non-billable `check_health()`, and `list_models()`.
  - Reusable: 100% directly usable by all Council rounds.
- **`provider_config.py`:**
  - Pydantic models: `SingleProviderConfig`, `AIPluginMasterConfig`.
  - Supports TOML configuration and `.env` credentials with `get_provider(name)` lookup and alias resolution (`chatgpt` -> `openai`, `claude` -> `anthropic`).
  - Reusable: Master config already holds council settings (`default_members`, `min_quorum`).
- **`response_normalizer.py`:**
  - `AIResponse` and `AIUsage` data structures normalizing `status`, `content`, `model`, `finish_reason`, `latency_ms`, `input_tokens`, `output_tokens`, `total_tokens`, and `metadata`.
  - Reusable: Every Council member's output in every round normalizes to `AIResponse`.
- **`plugin_security.py`:**
  - `validate_endpoint_url()` enforces SSRF protection against RFC1918 private subnets and metadata services, requires HTTPS for cloud providers, and isolates loopback for local Ollama.
  - `mask_secret()` redacts credentials.
  - `sanitize_prompt()` redacts API keys (`AIzaSy...`, `sk-...`) from prompts.
  - Reusable: Security gate for all multi-round prompts and custom endpoints.
- **`usage_tracker.py`:**
  - Singleton `usage_tracker` thread-safely tracks requests, successes, failures, tokens, and latency statistics across providers.
  - Reusable: Directly tracks token budget consumption across council rounds.
- **`provider_registry.py`:**
  - Central manager for all configured providers: OpenAI, Anthropic, Ollama, Perplexity, DeepSeek, Groq, OpenRouter, and custom endpoints.
  - Reusable: `get_provider_registry()` provides dynamic provider lookup and lifecycle control.
- **`ai_plugins_mcp.py`:**
  - Production FastMCP server exposing 16 Day 25 tools.
  - Basic `ai_council_compare` and `get_ai_council_status` currently exist as a single-turn parallel query baseline.

---

## 3. Gap Analysis: Day 25 Baseline vs Day 26 Requirements

| Capability | Day 25 Baseline | Day 26 Advanced Council Target |
| :--- | :--- | :--- |
| **Deliberation Rounds** | Single round parallel query only. | 4-round pipeline: (1) Independent Analysis, (2) Cross-Examination, (3) Revised Position, (4) Gemini Verdict. |
| **Operating Modes** | Fixed single mode. | 3 distinct modes: `QUICK_COUNCIL`, `DEEP_COUNCIL`, `LOCAL_COUNCIL` (100% offline, privacy-first). |
| **Claim Extraction** | Raw text returned to caller. | Atomic claim extraction, classification (technical, factual, assumption, recommendation), and normalization. |
| **Cross-AI Critique** | No peer review. | Multi-agent challenge engine: peer weakness detection, counterarguments, accepted vs rejected critique. |
| **Disagreement Detection** | Simple text concat for Gemini. | Categorized disagreement engine: Factual, Technical, Assumption, Performance, Security, Implementation, Priority; severity ranking (`LOW` to `CRITICAL`). |
| **Consensus Analysis** | Informal text blocks. | Formal consensus analysis: Full, Partial, No Agreement, Contradictory, Minority vs Majority attribution, avoiding false-consensus bias. |
| **Technical Evaluation** | No scoring logic. | Domain-specific criteria profiles (Software, Architecture, Research, Engineering, Business, General). |
| **Decision Engine** | Human/Gemini subjective read. | Multi-criteria weighted decision engine (`calculate_weighted_scores()`, `rank_candidate_solutions()`, 7 priority modes). |
| **Evidence & Uncertainty** | Unclassified. | Transparent evidence labeling (`HIGH`, `MODERATE`, `LOW`, `UNVERIFIED`) and assumptions cataloging. |
| **Gemini Final Arbiter** | Raw prompt handoff. | Structured Verdict engine with standard verdict categories: `SOLUTION_A`, `SOLUTION_B`, `HYBRID`, `NO_CLEAR_WINNER`, `MORE_INFO_REQUIRED`, `UNSUITABLE`. |
| **Reporting & Persistence** | Ephemeral JSON dictionary. | Comprehensive Council session reporting (JSON, Markdown) with session ID and retrieval tools. |
| **MCP Tools** | 16 general provider tools. | Extended to 26 tools total (adding 10 dedicated Council tools: `run_ai_council`, `run_quick_council`, `run_deep_council`, etc.). |

---

## 4. Architectural Design & Logical Submodules

To keep the codebase maintainable without bloat, we introduce focused modules in `zye_ai_plugins/`:

1. **`claim_extractor.py`**:
   - Parses unstructured AI responses into atomic statements.
   - Categorizes claims: `TECHNICAL`, `FACTUAL`, `ASSUMPTION`, `RECOMMENDATION`, `NUMERICAL`.
2. **`disagreement_detector.py`**:
   - Compares claim sets across providers.
   - Detects contradictions, divergent recommendations, conflicting technical numbers.
   - Assigns severity: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
3. **`consensus_analyzer.py`**:
   - Computes shared consensus points and identifies isolated minority arguments.
   - Explicitly checks for correlated-model bias.
4. **`council_evaluator.py`**:
   - Applies task-specific evaluation profiles (Software Development, Architecture, Research, Engineering, Business, General).
   - Validates feasibility, security, reliability, and architectural complexity.
5. **`decision_engine.py`**:
   - Multi-criteria weighted decision analysis engine with 7 priority modes (`BALANCED`, `SPEED_CRITICAL`, `MAXIMUM_SAFETY`, `LOW_RESOURCE`, `HIGH_RELIABILITY`, `MAINTAINABILITY_FIRST`, `USER_CUSTOM`).
   - Normalizes scores, ranks candidate solutions, and surfaces unresolved risks.
6. **`evidence_analyzer.py`**:
   - Examines claim support, classifies uncertainty (`HIGH_EVIDENCE`, `MODERATE`, `LOW`, `UNVERIFIED`), and surfaces unsupported assumptions.
7. **`council_report.py`**:
   - Formats comprehensive session reports in structured JSON and Markdown, handling session persistence and export.
8. **`ai_council.py` (Major Upgrade)**:
   - Orchestrates the full lifecycle: Council planning, Provider selection, Round 1 (Independent), Round 2 (Cross-Critique), Round 3 (Revision), Decision Engine scoring, and Round 4 (Gemini Final Verdict synthesis).
   - Manages Council modes: `QUICK`, `DEEP`, `LOCAL`.

---

## 5. Security & Safety Principles

1. **Untrusted Sub-Agent Boundary:** External AI responses are treated strictly as untrusted user-level data. No external model can inject prompt commands, modify files, or execute tools directly.
2. **Local-Only Privacy Enforcement:** When `LOCAL_COUNCIL` or privacy mode is invoked, external networks are barred; only local Ollama endpoints are queried.
3. **Budget & Concurrency Bounds:** Maximum participants (default 4), maximum rounds (default 2), timeout enforcement (30-90s), and cost limits prevent runaway API consumption.
4. **Gemini Supremacy:** Gemini alone renders the final recommendation and speaks to the user.

---

## 6. Implementation Checklist

- [ ] Submodule 1: `zye_ai_plugins/claim_extractor.py`
- [ ] Submodule 2: `zye_ai_plugins/disagreement_detector.py`
- [ ] Submodule 3: `zye_ai_plugins/consensus_analyzer.py`
- [ ] Submodule 4: `zye_ai_plugins/council_evaluator.py`
- [ ] Submodule 5: `zye_ai_plugins/decision_engine.py`
- [ ] Submodule 6: `zye_ai_plugins/evidence_analyzer.py`
- [ ] Submodule 7: `zye_ai_plugins/council_report.py`
- [ ] Submodule 8: `zye_ai_plugins/ai_council.py` (Full Multi-Round Orchestration)
- [ ] Package exports: `zye_ai_plugins/__init__.py`
- [ ] FastMCP Tools: Add 10 Council tools to `ai_plugins_mcp.py`
- [ ] Orchestration & Routing: Update `main.py` tool dispatching
- [ ] Voice Understanding: Update `zye_brain/gemini_agent.py` SYSTEM_PERSONA for Tamil/Tanglish/English council commands
- [ ] System Health: Add Stage 22 diagnostics and `--day26-check` to `doctor.py`
- [ ] Unit & Integration Test Suite: 20+ comprehensive tests in `tests/test_day26_*.py`
- [ ] Certification Reports & Documentation in `docs/` and `reports/`
