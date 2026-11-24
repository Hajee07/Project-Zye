"""
ZYE AI — Real-Time Tactical Intelligence MCP Server (Day 35, Day 36, Day 37 & Day 38 / Phase 3).
High-Speed In-Memory Ring-Buffer Telemetry Stream, Sliding Window Analytics,
Velocity & Acceleration Calculator, Z-Score Anomaly Detection,
First/Second-Order Markov Opponent Pattern Recognition, Empirical Next-Action Prediction,
Advanced Kinematic Collision Risk Mathematics, Vectorized Monte Carlo Simulation Engine,
and Multi-Source Independent Real-Time News Verification Engine.

Exposes 19 FastMCP tools (5 Telemetry + 5 Opponent Behaviour + 5 Kinematic & Simulation + 4 News Intelligence):
1. analyze_realtime_stream
2. get_telemetry_stream_status
3. list_telemetry_streams
4. reset_telemetry_stream
5. get_telemetry_performance_metrics
6. predict_opponent_attack
7. get_opponent_sequence_status
8. list_tracked_opponents
9. reset_opponent_sequence
10. get_opponent_pattern_summary
11. calculate_kinematic_risk
12. run_monte_carlo_risk_simulation
13. validate_kinematic_scenario
14. compare_trajectory_scenarios
15. get_tactical_simulation_status
16. fetch_verified_live_updates
17. verify_specific_news_claim
18. analyze_news_source_independence
19. get_news_verification_status
"""

from __future__ import annotations

import logging
import sys
from typing import Any, List, Optional

# Initialize FastMCP Server (compatible with mcp 1.x, 2.x, or fallback shim)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
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

from zye_guard import zye_safe_skill
from zye_realtime_tactical.telemetry.telemetry_analyzer import TelemetryAnalyzer
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager
from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager
from zye_realtime_tactical.opponent.opponent_prediction_engine import OpponentPredictionEngine
from zye_realtime_tactical.opponent.bigram_pattern_detector import BigramPatternDetector
from zye_realtime_tactical.opponent.trigram_pattern_detector import TrigramPatternDetector
from zye_realtime_tactical.opponent.pattern_ranking_engine import PatternRankingEngine
from zye_realtime_tactical.opponent.opponent_state_analyzer import OpponentStateAnalyzer
from zye_realtime_tactical.opponent.first_order_markov import FirstOrderMarkov
from zye_realtime_tactical.opponent.second_order_markov import SecondOrderMarkov
from zye_realtime_tactical.kinematics.kinematic_engine import KinematicEngine
from zye_realtime_tactical.kinematics.monte_carlo_engine import MonteCarloSimulationEngine
from zye_realtime_tactical.kinematics.scenario_manager import ScenarioManager
from zye_realtime_tactical.kinematics.simulation_status_tracker import SimulationStatusTracker
from zye_realtime_tactical.kinematics.kinematic_models import (
    KinematicState,
    SafetyEnvelope,
    UncertaintyConfig,
)
from zye_realtime_tactical.news.news_models import (
    IndependenceClassification,
    NewsArticle,
)
from zye_realtime_tactical.news.publisher_registry import PublisherRegistry
from zye_realtime_tactical.news.syndication_detector import SyndicationDetector
from zye_realtime_tactical.news.verification_engine import NewsVerificationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zye.realtime_tactical.mcp")

mcp = FastMCP("realtime_tactical")
_buffer_manager = TelemetryBufferManager.get_instance()
_analyzer = TelemetryAnalyzer(buffer_manager=_buffer_manager)

_opponent_buffer_manager = OpponentBufferManager.get_instance()
_opponent_engine = OpponentPredictionEngine(buffer_manager=_opponent_buffer_manager)

_status_tracker = SimulationStatusTracker.get_instance()


# ===========================================================================
# TELEMETRY STREAM TOOLS (01 - 05)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 01: Analyze Realtime Stream
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=10.0)
def analyze_realtime_stream(
    stream_name: str,
    new_readings: list[float],
    timestamps: Optional[list[float]] = None,
    window_size: Optional[int] = None,
    anomaly_threshold: Optional[float] = None,
    buffer_capacity: Optional[int] = None,
) -> dict[str, Any]:
    """
    Ingests numerical readings into a bounded in-memory ring buffer (default 5,000 samples)
    and computes rolling mean, standard deviation, velocity (units/sec), acceleration (units/sec^2),
    and Z-score statistical anomaly detection.
    Zero disk lag: Operates entirely in RAM with atomic batch validation.
    """
    try:
        res = _analyzer.analyze_realtime_stream(
            stream_name=stream_name,
            new_readings=new_readings,
            timestamps=timestamps,
            window_size=window_size,
            anomaly_threshold=anomaly_threshold,
            buffer_capacity=buffer_capacity,
        )
        return res.model_dump()
    except Exception as exc:
        logger.error("analyze_realtime_stream error on '%s': %s", stream_name, exc, exc_info=True)
        return {
            "status": "ERROR",
            "stream": stream_name,
            "sample_count": 0,
            "total_samples_ingested": 0,
            "overwritten_samples": 0,
            "error_message": f"Tool execution failure: {exc}",
        }


# ---------------------------------------------------------------------------
# Tool 02: Get Telemetry Stream Status
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_telemetry_stream_status(stream_name: str) -> dict[str, Any]:
    """
    Returns current sample count, buffer capacity, total ingested samples,
    overwritten samples, activity timestamp, and timestamp mode for a stream.
    """
    status = _buffer_manager.stream_manager.get_stream_status(stream_name)
    if not status:
        return {
            "status": "NOT_FOUND",
            "stream_name": stream_name,
            "message": f"Stream '{stream_name}' has not been initialized or is inactive.",
        }
    return {"status": "SUCCESS", "stream_status": status.model_dump()}


# ---------------------------------------------------------------------------
# Tool 03: List Telemetry Streams
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def list_telemetry_streams() -> dict[str, Any]:
    """
    Lists all active in-memory telemetry streams with their current capacity and sample counts.
    """
    streams = _buffer_manager.stream_manager.list_active_streams()
    return {
        "status": "SUCCESS",
        "active_stream_count": len(streams),
        "streams": [s.model_dump() for s in streams],
    }


# ---------------------------------------------------------------------------
# Tool 04: Reset Telemetry Stream
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=5.0)
def reset_telemetry_stream(stream_name: str) -> dict[str, Any]:
    """
    Clears all buffered observations and sample counters for a stream.
    Safe reset operation requiring explicit stream identifier.
    """
    success = _buffer_manager.stream_manager.reset_stream(stream_name)
    if not success:
        return {
            "status": "NOT_FOUND",
            "stream_name": stream_name,
            "message": f"Stream '{stream_name}' does not exist.",
        }
    return {
        "status": "SUCCESS",
        "stream_name": stream_name,
        "action": "STREAM_RESET_COMPLETED",
    }


# ---------------------------------------------------------------------------
# Tool 05: Get Telemetry Performance Metrics
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_telemetry_performance_metrics() -> dict[str, Any]:
    """
    Returns global telemetry performance metrics including total analyses executed,
    average computation latency in milliseconds, active streams count, and total samples in RAM.
    """
    metrics = _buffer_manager.get_performance_metrics()
    return {"status": "SUCCESS", "metrics": metrics}


# ===========================================================================
# OPPONENT BEHAVIOUR INTELLIGENCE TOOLS (06 - 10)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 06: Predict Opponent Attack
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=10.0)
def predict_opponent_attack(
    opponent_id: str,
    observed_actions: list[str],
    action_timestamps: Optional[list[float]] = None,
) -> dict[str, Any]:
    """
    Ingests observed opponent actions into an in-memory circular buffer (maxlen 1,000)
    and predicts next actions using First-Order and Second-Order Markov Chain models.
    Identifies top fighting patterns (bigrams and trigrams) and expected attack timing.
    Zero-fabrication: returns empirical probabilities strictly from observed data.
    Minimum evidence required: 6 actions.
    """
    try:
        res = _opponent_engine.predict_opponent_attack(
            opponent_id=opponent_id,
            observed_actions=observed_actions,
            action_timestamps=action_timestamps,
        )
        return res.model_dump()
    except Exception as exc:
        logger.error("predict_opponent_attack error on '%s': %s", opponent_id, exc, exc_info=True)
        return {
            "status": "ERROR",
            "opponent_id": opponent_id,
            "total_observed_actions": 0,
            "error_message": f"Tool execution failure: {exc}",
            "compute_time_ms": 0.0,
        }


# ---------------------------------------------------------------------------
# Tool 07: Get Opponent Sequence Status
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_opponent_sequence_status(opponent_id: str) -> dict[str, Any]:
    """
    Returns buffer state, current action count, capacity, total ingested actions,
    overwritten actions count, and activity timestamp for an opponent.
    """
    status = _opponent_buffer_manager.sequence_manager.get_status(opponent_id)
    if not status:
        return {
            "status": "NOT_FOUND",
            "opponent_id": opponent_id,
            "message": f"Opponent '{opponent_id}' has not been initialized or is inactive.",
        }
    return {"status": "SUCCESS", "opponent_status": status.model_dump()}


# ---------------------------------------------------------------------------
# Tool 08: List Tracked Opponents
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def list_tracked_opponents() -> dict[str, Any]:
    """
    Lists all active tracked opponents in RAM with current action counts and buffer capacities.
    """
    opponents = _opponent_buffer_manager.sequence_manager.list_opponents()
    return {
        "status": "SUCCESS",
        "active_opponent_count": len(opponents),
        "opponents": [o.model_dump() for o in opponents],
    }


# ---------------------------------------------------------------------------
# Tool 09: Reset Opponent Sequence
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=5.0)
def reset_opponent_sequence(opponent_id: str) -> dict[str, Any]:
    """
    Clears all buffered observations and sample counters for an opponent.
    Requires explicit opponent identifier.
    """
    success = _opponent_buffer_manager.sequence_manager.reset_opponent(opponent_id)
    if not success:
        return {
            "status": "NOT_FOUND",
            "opponent_id": opponent_id,
            "message": f"Opponent '{opponent_id}' does not exist.",
        }
    return {
        "status": "SUCCESS",
        "opponent_id": opponent_id,
        "action": "SEQUENCE_RESET_COMPLETED",
    }


# ---------------------------------------------------------------------------
# Tool 10: Get Opponent Pattern Summary
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_opponent_pattern_summary(opponent_id: str) -> dict[str, Any]:
    """
    Analyzes all currently buffered actions for an opponent without appending new actions.
    Returns recurring bigram/trigram patterns, current action state, and transition matrix metrics.
    """
    buf = _opponent_buffer_manager.sequence_manager.get_buffer(opponent_id)
    if not buf or buf.size == 0:
        return {
            "status": "NOT_FOUND",
            "opponent_id": opponent_id,
            "message": f"Opponent '{opponent_id}' has no buffered actions.",
        }

    actions = buf.get_all_actions()
    bigrams = BigramPatternDetector.detect(actions)
    trigrams = TrigramPatternDetector.detect(actions)
    ranked = PatternRankingEngine.rank(bigrams, trigrams, top_n=4)

    state_tuple = OpponentStateAnalyzer.get_current_state(actions)
    state_str = OpponentStateAnalyzer.format_state_string(state_tuple)

    first_matrix = FirstOrderMarkov.build_transition_matrix(actions)
    second_matrix = SecondOrderMarkov.build_transition_matrix(actions)

    return {
        "status": "SUCCESS",
        "opponent_id": opponent_id,
        "total_actions": buf.size,
        "current_state": state_str,
        "detected_patterns": [p.model_dump() for p in ranked],
        "first_order_unique_states": len(first_matrix),
        "second_order_unique_contexts": len(second_matrix),
    }


# ===========================================================================
# KINEMATIC RISK & MONTE CARLO SIMULATION TOOLS (11 - 15)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 11: Calculate Kinematic Risk
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=10.0)
def calculate_kinematic_risk(
    entity_a: dict[str, Any],
    entity_b: dict[str, Any],
    dimension: int = 2,
    horizon_seconds: float = 10.0,
    safety_envelope: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Performs deterministic 2D or 3D kinematic collision risk analysis between two moving entities.
    Calculates relative position, velocity, and acceleration vectors, closing speed,
    Closest Point of Approach (CPA), Time to CPA (TCPA), and exact Time to Collision (TTC).
    """
    try:
        dim = int(dimension)
        state_a = KinematicState(**entity_a)
        state_b = KinematicState(**entity_b)
        env = SafetyEnvelope(**safety_envelope) if safety_envelope else None

        res = KinematicEngine.calculate_risk(
            entity_a=state_a,
            entity_b=state_b,
            horizon_seconds=float(horizon_seconds),
            safety_envelope=env,
            dimension=dim,
        )
        _status_tracker.record_deterministic_analysis(res.compute_time_ms)
        return res.model_dump()
    except Exception as exc:
        logger.error("calculate_kinematic_risk error: %s", exc, exc_info=True)
        _status_tracker.record_error()
        return {
            "status": "ERROR",
            "error_message": f"Kinematic calculation failure: {exc}",
            "verified": False,
        }


# ---------------------------------------------------------------------------
# Tool 12: Run Monte Carlo Risk Simulation
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=20.0)
def run_monte_carlo_risk_simulation(
    entity_a: dict[str, Any],
    entity_b: dict[str, Any],
    sample_count: int = 20000,
    horizon_seconds: float = 10.0,
    dimension: int = 2,
    uncertainty_a: Optional[dict[str, Any]] = None,
    uncertainty_b: Optional[dict[str, Any]] = None,
    safety_envelope: Optional[dict[str, Any]] = None,
    random_seed: Optional[int] = 42,
) -> dict[str, Any]:
    """
    Simulates thousands of stochastic trajectory outcomes (default 20,000 samples)
    under measurement and motion uncertainties.
    Calculates empirical collision probability, near-miss probability, separation percentiles
    (min, median, mean, p05, p95), Wilson Score 95% confidence intervals, and risk classification.
    """
    try:
        _status_tracker.record_job_start()
        dim = int(dimension)
        state_a = KinematicState(**entity_a)
        state_b = KinematicState(**entity_b)
        env = SafetyEnvelope(**safety_envelope) if safety_envelope else None
        unc_a = UncertaintyConfig(**uncertainty_a) if uncertainty_a else None
        unc_b = UncertaintyConfig(**uncertainty_b) if uncertainty_b else None

        res = MonteCarloSimulationEngine.run_simulation(
            entity_a=state_a,
            entity_b=state_b,
            sample_count=int(sample_count),
            horizon_seconds=float(horizon_seconds),
            uncertainty_a=unc_a,
            uncertainty_b=unc_b,
            safety_envelope=env,
            random_seed=random_seed,
            dimension=dim,
        )
        _status_tracker.record_job_end(res, res.execution_time_ms)
        return res.model_dump()
    except Exception as exc:
        logger.error("run_monte_carlo_risk_simulation error: %s", exc, exc_info=True)
        _status_tracker.record_error()
        return {
            "status": "ERROR",
            "error_message": f"Monte Carlo simulation failure: {exc}",
            "verified": False,
        }


# ---------------------------------------------------------------------------
# Tool 13: Validate Kinematic Scenario
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def validate_kinematic_scenario(
    scenario_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Validates kinematic scenario inputs before mathematical execution.
    Checks dimensional integrity, coordinate finite values, non-negative radii,
    simulation horizon bounds, and covariance matrix validity.
    """
    is_valid, errors = ScenarioManager.validate_scenario(scenario_data)
    return {
        "status": "VALID" if is_valid else "INVALID",
        "is_valid": is_valid,
        "error_count": len(errors),
        "validation_errors": errors,
        "message": "Scenario configuration is mathematically valid." if is_valid else "Validation errors detected.",
    }


# ---------------------------------------------------------------------------
# Tool 14: Compare Trajectory Scenarios
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=25.0)
def compare_trajectory_scenarios(
    baseline_scenario: dict[str, Any],
    comparison_scenarios: list[dict[str, Any]],
    sample_count: int = 10000,
    horizon_seconds: float = 10.0,
    dimension: int = 2,
) -> dict[str, Any]:
    """
    Simulates and ranks multiple kinematic scenarios against a baseline scenario.
    Identifies safer configurations, percentage point collision probability differences,
    separation shifts, and sensitivity observations.
    """
    try:
        dim = int(dimension)
        b_valid, b_err = ScenarioManager.validate_scenario(baseline_scenario)
        if not b_valid:
            return {"status": "INVALID_BASELINE", "validation_errors": b_err}

        b_state_a = KinematicState(**baseline_scenario["entity_a"])
        b_state_b = KinematicState(**baseline_scenario["entity_b"])
        b_env = SafetyEnvelope(**baseline_scenario.get("safety_envelope", {})) if "safety_envelope" in baseline_scenario else None

        base_res = MonteCarloSimulationEngine.run_simulation(
            entity_a=b_state_a,
            entity_b=b_state_b,
            sample_count=sample_count,
            horizon_seconds=horizon_seconds,
            safety_envelope=b_env,
            dimension=dim,
            random_seed=42,
        )
        base_res.scenario_id = baseline_scenario.get("scenario_id", "baseline")

        comp_results: list[MonteCarloResult] = []
        for idx, comp_data in enumerate(comparison_scenarios):
            c_valid, c_err = ScenarioManager.validate_scenario(comp_data)
            if not c_valid:
                return {"status": f"INVALID_COMPARISON_SCENARIO_{idx}", "validation_errors": c_err}
            c_state_a = KinematicState(**comp_data["entity_a"])
            c_state_b = KinematicState(**comp_data["entity_b"])
            c_env = SafetyEnvelope(**comp_data.get("safety_envelope", {})) if "safety_envelope" in comp_data else None

            c_res = MonteCarloSimulationEngine.run_simulation(
                entity_a=c_state_a,
                entity_b=c_state_b,
                sample_count=sample_count,
                horizon_seconds=horizon_seconds,
                safety_envelope=c_env,
                dimension=dim,
                random_seed=42,
            )
            c_res.scenario_id = comp_data.get("scenario_id", f"comparison_{idx + 1}")
            comp_results.append(c_res)

        cmp_res = ScenarioManager.compare_scenarios(base_res, comp_results)
        return cmp_res.model_dump()
    except Exception as exc:
        logger.error("compare_trajectory_scenarios error: %s", exc, exc_info=True)
        return {"status": "ERROR", "error_message": f"Scenario comparison failure: {exc}"}


# ---------------------------------------------------------------------------
# Tool 15: Get Tactical Simulation Status
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_tactical_simulation_status() -> dict[str, Any]:
    """
    Returns runtime engine availability, active simulation jobs, total simulations executed,
    average compute latency, and last completed Monte Carlo job snapshot.
    """
    status = _status_tracker.get_status()
    return {"status": "SUCCESS", "simulation_engine": status}


# ===========================================================================
# REAL-TIME NEWS INTELLIGENCE & VERIFICATION TOOLS (16 - 19)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 16: Fetch Verified Live Updates
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=15.0)
async def fetch_verified_live_updates(
    topic: str,
    max_results: int = 8,
    freshness_window_hours: float = 72.0,
    as_of_timestamp: Optional[float] = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Retrieves live news articles via non-blocking DuckDuckGo search, analyzes publisher ownership,
    validates publication timestamps in UTC, filters syndicated/wire reports, corroborates claims,
    and returns a structured verification report. Enforces fail-closed threshold: requires >= 2
    independent corroborating sources to qualify for proactive alerts.
    """
    try:
        engine = NewsVerificationEngine.get_instance()
        res = await engine.verify_topic(
            topic=topic,
            max_results=int(max_results),
            freshness_window_hours=float(freshness_window_hours),
            as_of_timestamp=as_of_timestamp,
            use_cache=use_cache,
        )
        return res.model_dump()
    except Exception as exc:
        logger.error("fetch_verified_live_updates error: %s", exc, exc_info=True)
        return {
            "status": "ERROR",
            "error_message": f"News verification failure: {exc}",
            "verified": False,
            "proactive_alert_eligible": False,
        }


# ---------------------------------------------------------------------------
# Tool 17: Verify Specific News Claim
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=False, timeout_seconds=15.0)
async def verify_specific_news_claim(
    claim: str,
    search_context: Optional[str] = None,
    freshness_window_hours: float = 72.0,
    max_results: int = 8,
) -> dict[str, Any]:
    """
    Verifies a specific factual claim against independent live news sources.
    Extracts atomic subject/predicate/number/date propositions, evaluates corroboration across
    independent publishers, detects numerical or temporal contradictions, and returns verification status.
    """
    try:
        engine = NewsVerificationEngine.get_instance()
        res = await engine.verify_specific_claim(
            claim=claim,
            search_context=search_context,
            freshness_window_hours=float(freshness_window_hours),
            max_results=int(max_results),
        )
        return res.model_dump()
    except Exception as exc:
        logger.error("verify_specific_news_claim error: %s", exc, exc_info=True)
        return {
            "status": "ERROR",
            "claim": claim,
            "explanation": f"Claim verification failure: {exc}",
            "verified": False,
            "proactive_alert_eligible": False,
        }


# ---------------------------------------------------------------------------
# Tool 18: Analyze News Source Independence
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=10.0)
def analyze_news_source_independence(
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Performs deterministic ownership registry matching, wire-attribution detection,
    and headline token fingerprinting across a set of article candidates to determine genuine
    editorial independence versus syndication or conglomerate co-ownership.
    """
    try:
        article_objs: list[NewsArticle] = []
        for art_dict in articles:
            article_objs.append(NewsArticle(**art_dict))

        detector = SyndicationDetector()
        res = detector.analyze_sources(article_objs)
        return res.model_dump()
    except Exception as exc:
        logger.error("analyze_news_source_independence error: %s", exc, exc_info=True)
        return {
            "status": "ERROR",
            "error_message": f"Source independence analysis failure: {exc}",
            "total_sources_evaluated": len(articles),
            "independent_publisher_count": 0,
        }


# ---------------------------------------------------------------------------
# Tool 19: Get News Verification Status
# ---------------------------------------------------------------------------
@mcp.tool()
@zye_safe_skill(retry_safe=True, timeout_seconds=5.0)
def get_news_verification_status() -> dict[str, Any]:
    """
    Returns runtime operational telemetry for the news verification engine, including total verifications,
    corroboration rate, cached query count, and active verification thresholds.
    """
    try:
        engine = NewsVerificationEngine.get_instance()
        status = engine.get_status()
        return {"status": "SUCCESS", "news_engine": status}
    except Exception as exc:
        logger.error("get_news_verification_status error: %s", exc, exc_info=True)
        return {"status": "ERROR", "error_message": f"Status retrieval failure: {exc}"}


if __name__ == "__main__":
    logger.info("Starting Real-Time Tactical FastMCP Server on stdio (19 Tools)...")
    mcp.run()
