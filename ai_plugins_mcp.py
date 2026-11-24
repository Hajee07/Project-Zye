"""Zye AI Multi-AI Plugin Hub MCP Server (Day 25).

Unified FastMCP server providing safe delegation and deliberation across external and local AI providers:
- ChatGPT (OpenAI API)
- Claude (Anthropic Messages API)
- Local Ollama (Ollama REST API, 100% offline & private)
- Perplexity, DeepSeek, Groq, OpenRouter
- Custom user endpoints
- AI Council parallel deliberation engine
- Non-billable health checks and usage telemetry
- Gemini Master Brain remains the unchallenged supreme arbiter.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union

# FastMCP Server initialization
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except ImportError:
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

            async def list_tools(self) -> list[Any]:
                class _Stub:
                    def __init__(self, n: str):
                        self.name = n
                return [_Stub(n) for n in self._tools]

# Configure logging: write strictly to stderr so MCP stdio protocol is not corrupted
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("zye.ai_plugins.mcp")

# Import safety guard if available
try:
    from zye_guard import zye_safe_skill
    _GUARD_AVAILABLE = True
except ImportError:
    _GUARD_AVAILABLE = False
    def zye_safe_skill(*args: Any, **kwargs: Any) -> Any:
        def decorator(f: Any) -> Any:
            return f
        return decorator

# Subsystem Imports
from zye_ai_plugins import (
    AICouncilEngine,
    AIPluginMasterConfig,
    AIResponse,
    AIUsage,
    BaseAIProvider,
    NormalizedClaim,
    ProviderRegistry,
    SingleProviderConfig,
    UsageTracker,
    analyze_consensus,
    detect_disagreements,
    extract_response_claims,
    generate_ai_council_report,
    generate_disagreement_report,
    get_provider_registry,
    inspect_all_providers,
    inspect_provider_health,
    load_master_config,
    mask_secret,
    normalize_claims,
    rank_candidate_solutions,
    sanitize_prompt,
    usage_tracker,
    validate_endpoint_url,
    # Day 27 Subsystems
    get_circuit_breaker,
    get_rate_limiter,
    get_concurrency_controller,
    get_bulkhead_manager,
    select_best_provider,
    select_fallback_provider,
    estimate_request_cost,
    calculate_actual_cost,
    compare_provider_costs,
    check_provider_health,
    inspect_all_provider_health,
    get_telemetry_registry,
    benchmark_single_provider,
    run_suite_benchmarks,
)
from zye_ai_plugins.benchmarking import format_benchmark_markdown_report


# Instantiate Server
mcp = FastMCP("ai-plugins-mcp")

# Lazy Subsystems
_registry: Optional[ProviderRegistry] = None
_council: Optional[AICouncilEngine] = None


def _get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = get_provider_registry()
    return _registry


def _get_council() -> AICouncilEngine:
    global _council
    if _council is None:
        _council = AICouncilEngine(_get_registry())
    return _council


# =============================================================================
# 1. Discovery & Metadata Tools
# =============================================================================

@mcp.tool()
async def list_active_ai_plugins() -> Dict[str, Any]:
    """List all currently active and configured AI provider plugins available for delegation."""
    try:
        reg = _get_registry()
        active = reg.get_active_providers()
        all_providers = reg.list_all_providers()
        return {
            "status": "success",
            "active_providers_count": len(active),
            "active_providers": active,
            "total_registered": len(all_providers),
            "supreme_brain": "Gemini Master Brain (Active)",
        }
    except Exception as exc:
        logger.exception("list_active_ai_plugins failed: %s", exc)
        return {"status": "error", "message": str(exc), "active_providers": []}


@mcp.tool()
async def get_ai_plugin_status() -> Dict[str, Any]:
    """Retrieve operational status, configuration state, and connectivity summary for all AI plugins."""
    try:
        reg = _get_registry()
        providers_info = reg.list_all_providers()
        active_ids = reg.get_active_providers()
        return {
            "status": "success",
            "providers": providers_info,
            "active_count": len(active_ids),
            "unconfigured_count": len(providers_info) - len(active_ids),
            "telemetry_active": True,
        }
    except Exception as exc:
        logger.exception("get_ai_plugin_status failed: %s", exc)
        return {"status": "error", "message": str(exc), "providers": []}


@mcp.tool()
async def get_provider_models(provider_name: str) -> Dict[str, Any]:
    """Fetch the list of supported and discovered models for a specific AI provider."""
    try:
        reg = _get_registry()
        provider = reg.get_provider(provider_name)
        if not provider:
            return {
                "status": "error",
                "provider_name": provider_name,
                "message": f"Provider '{provider_name}' is not registered.",
                "models": [],
            }

        models = await provider.list_models()
        return {
            "status": "success",
            "provider_id": provider.provider_id,
            "default_model": provider.config.default_model,
            "models_count": len(models),
            "models": models,
        }
    except Exception as exc:
        logger.exception("get_provider_models failed for %s: %s", provider_name, exc)
        return {"status": "error", "provider_name": provider_name, "message": str(exc), "models": []}


@mcp.tool()
async def get_provider_metadata(provider_name: str) -> Dict[str, Any]:
    """Retrieve detailed architectural metadata, security profile, and limits for a provider."""
    try:
        reg = _get_registry()
        provider = reg.get_provider(provider_name)
        if not provider:
            return {"status": "error", "message": f"Provider '{provider_name}' not found."}

        cfg = provider.config
        return {
            "status": "success",
            "provider_id": provider.provider_id,
            "display_name": cfg.provider_name.capitalize(),
            "base_url": cfg.base_url,
            "default_model": cfg.default_model,
            "is_configured": provider.is_configured,
            "is_enabled": cfg.enabled,
            "is_local": getattr(provider, "allow_loopback", False),
            "timeout_seconds": cfg.timeout_seconds,
            "temperature_default": cfg.temperature,
            "max_tokens_default": cfg.max_tokens,
            "masked_key": mask_secret(cfg.api_key),
        }
    except Exception as exc:
        logger.exception("get_provider_metadata failed: %s", exc)
        return {"status": "error", "message": str(exc)}


@mcp.tool()
async def check_provider_health(provider_name: str = "all") -> Dict[str, Any]:
    """Run non-billable latency and health checks on a specific provider or across all providers."""
    try:
        reg = _get_registry()
        if provider_name.lower().strip() in ("all", "*"):
            results = await inspect_all_providers(reg._providers)
            return {"status": "success", "health_summary": results}
        else:
            provider = reg.get_provider(provider_name)
            if not provider:
                return {"status": "error", "message": f"Provider '{provider_name}' not found."}
            res = await inspect_provider_health(provider)
            return {"status": "success", "provider_health": res}
    except Exception as exc:
        logger.exception("check_provider_health failed: %s", exc)
        return {"status": "error", "message": str(exc)}


# =============================================================================
# 2. Individual AI Delegation Tools
# =============================================================================

@mcp.tool()
async def ask_chatgpt(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Delegate a specialized question or task to ChatGPT (OpenAI API)."""
    reg = _get_registry()
    provider = reg.get_provider("openai")
    if not provider:
        return {"status": "error", "error": "OpenAI provider is not loaded in registry."}

    resp = await provider.generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    usage_tracker.record_usage(
        provider_id="openai",
        success=resp.is_success,
        usage=resp.usage,
        is_timeout=(resp.status == "timeout"),
        error=resp.error_message,
    )
    return resp.to_dict()


@mcp.tool()
async def ask_claude(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Delegate a specialized question or task to Claude (Anthropic Messages API)."""
    reg = _get_registry()
    provider = reg.get_provider("anthropic")
    if not provider:
        return {"status": "error", "error": "Anthropic provider is not loaded in registry."}

    resp = await provider.generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    usage_tracker.record_usage(
        provider_id="anthropic",
        success=resp.is_success,
        usage=resp.usage,
        is_timeout=(resp.status == "timeout"),
        error=resp.error_message,
    )
    return resp.to_dict()


@mcp.tool()
async def ask_local_ollama(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Query a local Ollama instance (100% offline, zero cloud exposure, privacy-first)."""
    reg = _get_registry()
    provider = reg.get_provider("ollama")
    if not provider:
        return {"status": "error", "error": "Ollama provider is not loaded in registry."}

    resp = await provider.generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    usage_tracker.record_usage(
        provider_id="ollama",
        success=resp.is_success,
        usage=resp.usage,
        is_timeout=(resp.status == "timeout"),
        error=resp.error_message,
    )
    return resp.to_dict()


@mcp.tool()
async def ask_custom_ai_plugin(
    provider_name: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Delegate to any registered or custom AI provider (Perplexity, DeepSeek, Groq, OpenRouter, or custom)."""
    reg = _get_registry()
    target_id = provider_name.lower().strip()

    # If an ad-hoc endpoint was supplied and doesn't exist, register it safely
    if base_url:
        reg_res = reg.register_custom_provider(
            name=target_id,
            base_url=base_url,
            api_key=api_key,
            default_model=model or "default",
        )
        if not reg_res.get("success"):
            return {"status": "error", "error": reg_res.get("error")}

    provider = reg.get_provider(target_id)
    if not provider:
        return {
            "status": "error",
            "error": f"Provider '{provider_name}' not found. Register with base_url or use a known provider.",
        }

    resp = await provider.generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    usage_tracker.record_usage(
        provider_id=target_id,
        success=resp.is_success,
        usage=resp.usage,
        is_timeout=(resp.status == "timeout"),
        error=resp.error_message,
    )
    return resp.to_dict()


# =============================================================================
# 3. AI Council Deliberation Tools (Day 25 Foundation + Day 26 Advanced Intelligence)
# =============================================================================

@mcp.tool()
async def run_ai_council(
    question: str,
    providers: Optional[List[str]] = None,
    council_mode: str = "quick",
    priority_mode: str = "balanced",
    max_rounds: int = 1,
    timeout: float = 60.0,
    context: Optional[str] = None,
    privacy_mode: bool = False,
    evaluation_profile: str = "general",
) -> Dict[str, Any]:
    """Execute complete Multi-AI Council session across independent models with decision synthesis."""
    council = _get_council()
    result = await council.run_ai_council(
        question=question,
        providers=providers,
        council_mode=council_mode,
        priority_mode=priority_mode,
        max_rounds=max_rounds,
        evaluation_profile=evaluation_profile,
        context=context,
        privacy_mode=privacy_mode,
    )
    return result


@mcp.tool()
async def run_quick_council(
    question: str,
    providers: Optional[List[str]] = None,
    timeout: float = 45.0,
) -> Dict[str, Any]:
    """Execute fast independent comparison between ChatGPT and Claude with Gemini synthesis."""
    council = _get_council()
    return await council.run_quick_council(
        question=question,
        providers=providers,
        timeout=timeout,
    )


@mcp.tool()
async def run_deep_council(
    question: str,
    providers: Optional[List[str]] = None,
    max_rounds: int = 2,
    priority_mode: str = "balanced",
    evaluation_criteria: str = "general",
    timeout: float = 90.0,
) -> Dict[str, Any]:
    """Execute deep multi-round Council deliberation with cross-AI critique and weighted decision ranking."""
    council = _get_council()
    return await council.run_deep_council(
        question=question,
        providers=providers,
        max_rounds=max_rounds,
        priority_mode=priority_mode,
        evaluation_criteria=evaluation_criteria,
        timeout=timeout,
    )


@mcp.tool()
async def compare_ai_responses(
    question: str,
    provider_responses: Dict[str, str],
) -> Dict[str, Any]:
    """Extract claims, identify contradictions, and compare arbitrary AI response texts."""
    provider_claims = {}
    for pid, content in provider_responses.items():
        claims = extract_response_claims(pid, content)
        provider_claims[pid] = normalize_claims(claims)

    disagreements = detect_disagreements(provider_claims)
    consensus = analyze_consensus(provider_claims, disagreements)

    return {
        "status": "success",
        "question": question,
        "total_providers_compared": len(provider_responses),
        "disagreements": [d.to_dict() for d in disagreements],
        "consensus": consensus,
    }


@mcp.tool()
async def detect_ai_disagreements(
    provider_responses: Dict[str, str],
) -> Dict[str, Any]:
    """Detect and rank factual, technical, and architectural contradictions across AI responses."""
    provider_claims = {}
    for pid, content in provider_responses.items():
        claims = extract_response_claims(pid, content)
        provider_claims[pid] = normalize_claims(claims)

    disagreements = detect_disagreements(provider_claims)
    summary = generate_disagreement_report(disagreements)
    return {"status": "success", "disagreement_report": summary}


@mcp.tool()
async def analyze_ai_consensus(
    provider_responses: Dict[str, str],
) -> Dict[str, Any]:
    """Analyze shared conclusions, agreement score, and isolated minority perspectives."""
    provider_claims = {}
    for pid, content in provider_responses.items():
        claims = extract_response_claims(pid, content)
        provider_claims[pid] = normalize_claims(claims)

    disagreements = detect_disagreements(provider_claims)
    consensus = analyze_consensus(provider_claims, disagreements)
    return {"status": "success", "consensus_analysis": consensus}


@mcp.tool()
async def evaluate_candidate_solutions(
    problem_statement: str,
    candidate_solutions: Dict[str, Dict[str, Any]],
    priority_mode: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Perform multi-criteria weighted scoring and rank competing architecture/code solutions."""
    ranking = rank_candidate_solutions(
        candidate_solutions=candidate_solutions,
        priority_mode=priority_mode,
        custom_weights=custom_weights,
    )
    return {
        "status": "success",
        "problem_statement": problem_statement,
        "decision_ranking": ranking,
    }


@mcp.tool()
async def get_ai_council_report(
    council_id: str,
    format: str = "json",
) -> Dict[str, Any]:
    """Retrieve full deliberation report for a completed Council session in JSON or Markdown."""
    council = _get_council()
    session = council.get_council_report(council_id)
    if not session:
        return {"status": "error", "message": f"Council session '{council_id}' not found in cache."}

    report = generate_ai_council_report(session, format=format)
    return {"status": "success", "council_id": council_id, "format": format, "report": report}


@mcp.tool()
async def cancel_ai_council(council_id: str) -> Dict[str, Any]:
    """Cancel an active in-flight Council session."""
    council = _get_council()
    return council.cancel_council(council_id)


@mcp.tool()
async def ai_council_compare(
    question: str,
    providers: Optional[List[str]] = None,
    focus_area: str = "general",
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """Query multiple AI providers in parallel, gather diverse perspectives, and structure consensus for Gemini."""
    council = _get_council()
    result = await council.deliberate(
        question=question,
        providers=providers or ["chatgpt", "claude"],
        focus_area=focus_area,
        max_tokens=max_tokens,
    )
    return result


@mcp.tool()
async def get_ai_council_status() -> Dict[str, Any]:
    """Check readiness of the AI Council, active deliberation members, and quorum availability."""
    council = _get_council()
    return await council.get_council_status()



# =============================================================================
# 4. Configuration & Validation Tools
# =============================================================================

@mcp.tool()
async def validate_ai_plugin_configuration(provider_name: str) -> Dict[str, Any]:
    """Validate configuration parameters, API key presence, and endpoint safety for a provider."""
    reg = _get_registry()
    provider = reg.get_provider(provider_name)
    if not provider:
        return {"status": "error", "valid": False, "message": f"Provider '{provider_name}' not found"}

    cfg = provider.config
    is_safe, err_msg = validate_endpoint_url(cfg.base_url, allow_loopback=getattr(provider, "allow_loopback", False))
    return {
        "status": "success",
        "provider_id": provider.provider_id,
        "valid": is_safe and (provider.is_configured or getattr(provider, "allow_loopback", False)),
        "is_configured": provider.is_configured,
        "is_endpoint_safe": is_safe,
        "endpoint_error": err_msg,
        "has_api_key": bool(cfg.api_key),
        "base_url": cfg.base_url,
    }


@mcp.tool()
async def validate_provider_model(provider_name: str, model_name: str) -> Dict[str, Any]:
    """Check whether a specific model name is valid and supported by a given provider."""
    reg = _get_registry()
    provider = reg.get_provider(provider_name)
    if not provider:
        return {"status": "error", "valid": False, "message": f"Provider '{provider_name}' not found"}

    models = await provider.list_models()
    is_valid = (model_name.strip() in models) or (model_name.lower().strip() == provider.config.default_model.lower().strip())
    return {
        "status": "success",
        "provider_id": provider.provider_id,
        "model_requested": model_name,
        "is_valid": is_valid,
        "available_models": models,
    }


@mcp.tool()
async def get_ai_plugin_configuration_status() -> Dict[str, Any]:
    """Retrieve global configuration diagnostics across all AI plugins and environment status."""
    reg = _get_registry()
    summary = []
    for pid, provider in reg._providers.items():
        if id(provider) in [id(p) for p in reg._providers.values() if p.provider_id != pid]:
            continue
        cfg = provider.config
        summary.append({
            "provider_id": provider.provider_id,
            "enabled": cfg.enabled,
            "configured": provider.is_configured,
            "is_local": getattr(provider, "allow_loopback", False),
            "base_url": cfg.base_url,
        })
    return {
        "status": "success",
        "total_providers": len(summary),
        "configured_count": len([s for s in summary if s["configured"]]),
        "providers_config": summary,
    }


# =============================================================================
# 5. Usage Telemetry & Accounting Tools
# =============================================================================

@mcp.tool()
async def get_provider_usage(provider_name: str) -> Dict[str, Any]:
    """Retrieve token metrics, call counts, latency statistics, and error rates for a specific provider."""
    target_id = provider_name.lower().strip()
    data = usage_tracker.get_provider_usage(target_id)
    return {"status": "success", "usage": data}


@mcp.tool()
async def get_provider_usage_summary() -> Dict[str, Any]:
    """Retrieve aggregated token consumption and performance metrics across all AI providers."""
    summary = usage_tracker.get_all_usage()
    return {"status": "success", "summary": summary}


# =============================================================================
# 6. Day 27 Infrastructure Optimization, Routing & Reliability Tools
# =============================================================================

_current_global_routing_policy: str = "BALANCED"
_latest_benchmark_result: Optional[Dict[str, Any]] = None


@mcp.tool()
async def get_provider_health(provider_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve comprehensive health states across providers (AVAILABLE, DEGRADED, RATE_LIMITED, CIRCUIT_OPEN)."""
    reg = _get_registry()
    if provider_name:
        provider = reg.get_provider(provider_name)
        if not provider:
            return {"status": "error", "message": f"Provider '{provider_name}' not found"}
        health = await check_provider_health(provider)
        return {"status": "success", "provider_id": provider.provider_id, "health": health}

    summary = await inspect_all_provider_health(reg._providers)
    return {"status": "success", "health_summary": summary}


@mcp.tool()
async def get_all_provider_metrics() -> Dict[str, Any]:
    """Retrieve rolling performance metrics, percentiles (p50, p95), call counts, and success rates."""
    telemetry = get_telemetry_registry()
    rankings = telemetry.rank_providers_by_reliability()
    return {"status": "success", "provider_metrics": rankings}


@mcp.tool()
async def get_provider_reliability_ranking() -> Dict[str, Any]:
    """Retrieve empirical reliability rankings with sample-size confidence labels."""
    telemetry = get_telemetry_registry()
    rankings = telemetry.rank_providers_by_reliability()
    return {
        "status": "success",
        "rankings": rankings,
        "total_monitored": len(rankings),
    }


@mcp.tool()
async def get_routing_decision(
    task: str = "",
    routing_mode: Optional[str] = None,
    user_preferred_provider: Optional[str] = None,
    privacy_restricted: bool = False,
) -> Dict[str, Any]:
    """Evaluate candidate providers dynamically and explain the routing decision."""
    mode = routing_mode or _current_global_routing_policy
    decision = select_best_provider(
        task=task,
        routing_mode=mode,
        user_preferred_provider=user_preferred_provider,
        privacy_restricted=privacy_restricted,
    )
    return {"status": "success", "decision": decision.to_dict()}


@mcp.tool()
async def get_provider_status(provider_name: str) -> Dict[str, Any]:
    """Inspect active availability, circuit-breaker state, and current concurrency load for a provider."""
    pid = provider_name.lower().strip()
    cb = get_circuit_breaker().get_circuit(pid)
    cc = get_concurrency_controller().get_pool(pid)
    rl = get_rate_limiter().get_limiter(pid)

    return {
        "status": "success",
        "provider_id": pid,
        "circuit_breaker": cb.to_dict(),
        "concurrency": cc.to_dict(),
        "rate_limiter": rl.to_dict(),
    }


@mcp.tool()
async def get_provider_cost_estimate(
    provider_name: str,
    model_name: Optional[str] = None,
    estimated_input_tokens: int = 500,
    estimated_output_tokens: int = 300,
) -> Dict[str, Any]:
    """Estimate request cost using configured model rate cards."""
    reg = _get_registry()
    provider = reg.get_provider(provider_name)
    model = model_name or (getattr(provider.config, "default_model", provider_name) if provider else provider_name)

    est = estimate_request_cost(
        provider_id=provider_name,
        model=model,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
    )
    return {"status": "success", "estimate": est}


@mcp.tool()
async def get_provider_usage_report() -> Dict[str, Any]:
    """Generate comprehensive token usage and cost accounting report across all external providers."""
    summary = usage_tracker.get_all_usage()
    cost_comparisons = compare_provider_costs()
    return {
        "status": "success",
        "usage_telemetry": summary,
        "model_rate_cards": cost_comparisons[:8],
    }


@mcp.tool()
async def run_provider_benchmark(
    provider_name: Optional[str] = None,
    workload_type: str = "QUICK",
) -> Dict[str, Any]:
    """Execute synthetic non-intrusive latency and reliability benchmark."""
    global _latest_benchmark_result
    if provider_name:
        res = await benchmark_single_provider(provider_name, workload_type)
        return {"status": "success", "benchmark": res}

    suite = await run_suite_benchmarks(workload_type=workload_type)
    _latest_benchmark_result = suite
    return {"status": "success", "benchmark_suite": suite}


@mcp.tool()
async def get_provider_benchmark_report() -> Dict[str, Any]:
    """Retrieve the latest performance benchmark report in structured and markdown format."""
    global _latest_benchmark_result
    if not _latest_benchmark_result:
        suite = await run_suite_benchmarks(workload_type="QUICK")
        _latest_benchmark_result = suite

    md_report = format_benchmark_markdown_report(_latest_benchmark_result)
    return {
        "status": "success",
        "benchmark_data": _latest_benchmark_result,
        "markdown_report": md_report,
    }


@mcp.tool()
async def get_circuit_breaker_status(provider_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve 3-state circuit breaker statuses (CLOSED, OPEN, HALF_OPEN) across all providers."""
    cb_reg = get_circuit_breaker()
    if provider_name:
        return {"status": "success", "circuit": cb_reg.get_circuit(provider_name).to_dict()}
    return {"status": "success", "circuits": cb_reg.get_all_states()}


@mcp.tool()
async def get_failover_history(limit: int = 20) -> Dict[str, Any]:
    """Retrieve recent graceful provider failover events and reasons."""
    bulkhead = get_bulkhead_manager()
    history = bulkhead.get_failover_history(limit)
    return {"status": "success", "total_recorded": len(history), "history": history}


@mcp.tool()
async def get_concurrency_status(provider_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve active requests, queue limits, and pressure percent across provider bulkheads."""
    cc_reg = get_concurrency_controller()
    if provider_name:
        return {"status": "success", "concurrency": cc_reg.get_pool(provider_name).to_dict()}
    return {"status": "success", "concurrency_pools": cc_reg.get_all_statuses()}


@mcp.tool()
async def set_routing_policy(routing_mode: str) -> Dict[str, Any]:
    """Update global AI provider routing policy (BALANCED, QUALITY_FIRST, SPEED_FIRST, COST_FIRST, RELIABILITY_FIRST, LOCAL_ONLY)."""
    global _current_global_routing_policy
    clean_mode = routing_mode.upper().strip().replace("-", "_")
    from zye_ai_plugins.routing import ALL_ROUTING_MODES
    if clean_mode not in ALL_ROUTING_MODES:
        return {
            "status": "error",
            "message": f"Invalid routing mode '{routing_mode}'. Permitted: {ALL_ROUTING_MODES}",
        }

    _current_global_routing_policy = clean_mode
    logger.info("Global AI routing policy updated to '%s'", clean_mode)
    return {
        "status": "success",
        "previous_policy": _current_global_routing_policy,
        "active_policy": clean_mode,
    }


@mcp.tool()
async def reset_provider_health(provider_name: str) -> Dict[str, Any]:
    """Administrative reset for a tripped circuit breaker or rate-limit cooldown."""
    pid = provider_name.lower().strip()
    get_circuit_breaker().reset_circuit(pid)
    get_rate_limiter().get_limiter(pid).cooldown_until = 0.0
    logger.info("Admin reset executed for provider '%s' (Circuit CLOSED, Cooldown cleared)", pid)
    return {
        "status": "success",
        "provider_id": pid,
        "message": f"Circuit breaker for '{pid}' reset to CLOSED and rate-limit cooldown cleared",
    }


@mcp.tool()
async def get_ai_infrastructure_report() -> Dict[str, Any]:
    """Generate consolidated operational report (Circuits, Rate Limits, Health, Concurrency, and Routing)."""
    reg = _get_registry()
    cb_states = get_circuit_breaker().get_all_states()
    cc_states = get_concurrency_controller().get_all_statuses()
    rl_states = get_rate_limiter().get_all_statuses()
    rel_ranks = get_telemetry_registry().rank_providers_by_reliability()

    open_circuits = [pid for pid, c in cb_states.items() if c["state"] == "OPEN"]
    throttled = [pid for pid, r in rl_states.items() if r["in_cooldown"]]

    return {
        "status": "success",
        "active_routing_policy": _current_global_routing_policy,
        "total_providers_configured": len(reg._providers),
        "circuit_breakers": {
            "total_monitored": len(cb_states),
            "open_circuits_count": len(open_circuits),
            "open_providers": open_circuits,
        },
        "rate_limiting": {
            "throttled_count": len(throttled),
            "throttled_providers": throttled,
        },
        "concurrency_pools": len(cc_states),
        "reliability_rankings": rel_ranks[:5],
    }


# =============================================================================
# Standalone CLI / FastMCP stdio Runner
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Zye AI Multi-AI Plugin Hub MCP Server...")
    mcp.run()
