"""Zye AI Multi-AI Plugin Hub & Advanced AI Council Package (Day 25 & Day 26).

Provides universal integration with external and local AI providers:
- ChatGPT (OpenAI API)
- Claude (Anthropic Messages API)
- Local Ollama (REST API, 100% offline & private)
- Perplexity, DeepSeek, Groq, OpenRouter, Custom
- Advanced AI Council parallel deliberation engine
- Claim extraction & normalization
- Cross-AI critique & multi-round debate
- Disagreement detection & ranking
- Consensus analysis & minority perspective protection
- Domain evaluation profiles (Software, Architecture, Engineering, Research, Business)
- Multi-criteria weighted decision engine (7 priority modes)
- Evidence verification & uncertainty analysis
- Gemini Master Brain Supreme Arbiter synthesis
"""

from .ai_council import AICouncilEngine
from .anthropic_adapter import AnthropicAdapter
from .claim_extractor import (
    NormalizedClaim,
    classify_claims,
    compare_claims,
    extract_response_claims,
    normalize_claims,
)
from .consensus_analyzer import analyze_consensus
from .council_evaluator import (
    EVALUATION_PROFILES,
    evaluate_reasoning_quality,
    evaluate_security_risks,
    evaluate_technical_claims,
    get_evaluation_profile,
)
from .council_report import generate_ai_council_report, save_ai_council_report
from .decision_engine import (
    PRIORITY_MODES,
    calculate_weighted_scores,
    get_priority_mode_weights,
    rank_candidate_solutions,
)
from .disagreement_detector import (
    DisagreementItem,
    classify_disagreement,
    detect_disagreements,
    generate_disagreement_report,
    rank_disagreement_severity,
)
from .evidence_analyzer import (
    analyze_answer_uncertainty,
    evaluate_evidence_coverage,
    identify_unsupported_assumptions,
)
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter
from .openai_compatible_adapter import OpenAICompatibleAdapter
from .plugin_security import mask_secret, sanitize_prompt, validate_endpoint_url
from .provider_base import BaseAIProvider
from .provider_config import AIPluginMasterConfig, SingleProviderConfig, load_master_config
from .provider_health import inspect_all_providers, inspect_provider_health
from .provider_registry import ProviderRegistry, get_provider_registry
from .response_normalizer import AIResponse, AIUsage
from .usage_tracker import UsageTracker, usage_tracker

# Day 27 Subsystems
from .benchmarking import benchmark_single_provider, run_suite_benchmarks
from .resilience import (
    BulkheadManager,
    CircuitBreakerRegistry,
    ConcurrencyControllerRegistry,
    RateLimiterRegistry,
    classify_provider_error,
    execute_with_retry,
    get_bulkhead_manager,
    get_circuit_breaker,
    get_concurrency_controller,
    get_rate_limiter,
)
from .routing import (
    RoutingDecision,
    select_best_provider,
    select_fallback_provider,
)
from .telemetry import (
    TelemetryRegistry,
    calculate_actual_cost,
    check_provider_health,
    compare_provider_costs,
    estimate_request_cost,
    get_telemetry_registry,
    inspect_all_provider_health,
)

__all__ = [
    # Base & Core
    "BaseAIProvider",
    "AIResponse",
    "AIUsage",
    "AIPluginMasterConfig",
    "SingleProviderConfig",
    "load_master_config",
    # Adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OllamaAdapter",
    "OpenAICompatibleAdapter",
    # Registry & Health
    "ProviderRegistry",
    "get_provider_registry",
    "inspect_provider_health",
    "inspect_all_providers",
    # Security
    "mask_secret",
    "validate_endpoint_url",
    "sanitize_prompt",
    # Telemetry
    "UsageTracker",
    "usage_tracker",
    # Council Engine & Subsystems (Day 26)
    "AICouncilEngine",
    "NormalizedClaim",
    "extract_response_claims",
    "normalize_claims",
    "classify_claims",
    "compare_claims",
    "DisagreementItem",
    "detect_disagreements",
    "classify_disagreement",
    "rank_disagreement_severity",
    "generate_disagreement_report",
    "analyze_consensus",
    "EVALUATION_PROFILES",
    "get_evaluation_profile",
    "evaluate_reasoning_quality",
    "evaluate_security_risks",
    "evaluate_technical_claims",
    "PRIORITY_MODES",
    "get_priority_mode_weights",
    "calculate_weighted_scores",
    "rank_candidate_solutions",
    "analyze_answer_uncertainty",
    "evaluate_evidence_coverage",
    "identify_unsupported_assumptions",
    "generate_ai_council_report",
    "save_ai_council_report",
    # Day 27 Routing & Resilience
    "CircuitBreakerRegistry",
    "get_circuit_breaker",
    "execute_with_retry",
    "classify_provider_error",
    "RateLimiterRegistry",
    "get_rate_limiter",
    "ConcurrencyControllerRegistry",
    "get_concurrency_controller",
    "BulkheadManager",
    "get_bulkhead_manager",
    "select_best_provider",
    "select_fallback_provider",
    "RoutingDecision",
    "estimate_request_cost",
    "calculate_actual_cost",
    "compare_provider_costs",
    "check_provider_health",
    "inspect_all_provider_health",
    "TelemetryRegistry",
    "get_telemetry_registry",
    "benchmark_single_provider",
    "run_suite_benchmarks",
]
