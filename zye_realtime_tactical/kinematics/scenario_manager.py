"""
Scenario Management & Comparison Engine (Day 37 / Phase 3).
Validates kinematic scenario parameters, enforces boundary safety,
compares multiple simulated trajectories, and identifies safer configurations.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

from zye_realtime_tactical.kinematics.kinematic_models import (
    KinematicState,
    MonteCarloResult,
    RiskCategory,
    SafetyEnvelope,
    ScenarioComparisonResult,
    UncertaintyConfig,
)
from zye_realtime_tactical.kinematics.unit_converter import UnitConverter, UnitConversionError


class ScenarioValidationError(ValueError):
    """Raised when scenario inputs violate dimensional, physical, or numerical constraints."""
    pass


class ScenarioManager:
    """Manages kinematic scenario definitions, validation rules, and comparative evaluations."""

    @classmethod
    def validate_scenario(
        cls,
        scenario_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validates scenario dictionary against all mathematical and security requirements.
        Returns:
            (is_valid, validation_errors_list)
        """
        errors: List[str] = []

        if not isinstance(scenario_data, dict):
            return False, ["Scenario data must be a JSON object / dictionary."]

        # Check dimension
        dim = scenario_data.get("dimension", 2)
        if dim not in (2, 3):
            errors.append(f"Invalid dimension {dim}: must be 2 or 3.")

        # Check entity states
        for key in ("entity_a", "entity_b"):
            entity_dict = scenario_data.get(key)
            if not entity_dict or not isinstance(entity_dict, dict):
                errors.append(f"Missing or invalid '{key}' configuration.")
                continue

            # Position
            pos = entity_dict.get("position")
            if not pos or not isinstance(pos, (list, tuple)):
                errors.append(f"'{key}.position' must be a list of {dim} floats.")
            elif len(pos) != dim:
                errors.append(f"'{key}.position' length {len(pos)} does not match dimension {dim}.")
            else:
                for idx, v in enumerate(pos):
                    if not isinstance(v, (int, float)) or not math.isfinite(v):
                        errors.append(f"'{key}.position[{idx}]' must be a finite float, got: {v}")

            # Velocity
            vel = entity_dict.get("velocity")
            if not vel or not isinstance(vel, (list, tuple)):
                errors.append(f"'{key}.velocity' must be a list of {dim} floats.")
            elif len(vel) != dim:
                errors.append(f"'{key}.velocity' length {len(vel)} does not match dimension {dim}.")
            else:
                for idx, v in enumerate(vel):
                    if not isinstance(v, (int, float)) or not math.isfinite(v):
                        errors.append(f"'{key}.velocity[{idx}]' must be a finite float, got: {v}")

            # Acceleration (optional)
            accel = entity_dict.get("acceleration")
            if accel is not None:
                if not isinstance(accel, (list, tuple)) or len(accel) != dim:
                    errors.append(f"'{key}.acceleration' must be None or a list of {dim} floats.")
                else:
                    for idx, v in enumerate(accel):
                        if not isinstance(v, (int, float)) or not math.isfinite(v):
                            errors.append(f"'{key}.acceleration[{idx}]' must be a finite float, got: {v}")

            # Radius (must be >= 0)
            radius = entity_dict.get("radius", 1.0)
            if not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius < 0.0:
                errors.append(f"'{key}.radius' must be a non-negative finite float, got: {radius}")

        # Check horizon
        horizon = scenario_data.get("simulation_horizon_seconds", 10.0)
        if not isinstance(horizon, (int, float)) or not math.isfinite(horizon) or horizon <= 0.0 or horizon > 300.0:
            errors.append(f"simulation_horizon_seconds must be positive and <= 300.0, got: {horizon}")

        # Check sample count
        samples = scenario_data.get("sample_count", 20000)
        if not isinstance(samples, int) or samples <= 0 or samples > 200000:
            errors.append(f"sample_count must be an integer in [1, 200000], got: {samples}")

        return (len(errors) == 0), errors

    @classmethod
    def compare_scenarios(
        cls,
        baseline_result: MonteCarloResult,
        comparison_results: List[MonteCarloResult],
    ) -> ScenarioComparisonResult:
        """
        Ranks and compares simulation outcomes relative to a baseline run.
        Calculates delta collision probabilities, median separation shifts, and identifies the safest scenario.
        """
        rel_diffs: Dict[str, float] = {}
        sep_deltas: Dict[str, float] = {}
        observations: List[str] = []

        all_results = [baseline_result] + comparison_results
        # Sort by collision probability (ascending), then by median separation (descending)
        all_results.sort(key=lambda r: (r.collision_probability, -r.median_separation_m))

        safer_scenario = all_results[0].scenario_id

        for comp in comparison_results:
            diff_prob = round((comp.collision_probability - baseline_result.collision_probability) * 100.0, 4)
            sep_delta = round(comp.median_separation_m - baseline_result.median_separation_m, 3)

            rel_diffs[comp.scenario_id] = diff_prob
            sep_deltas[comp.scenario_id] = sep_delta

            if diff_prob < 0.0:
                observations.append(
                    f"Scenario '{comp.scenario_id}' reduces collision probability by {abs(diff_prob):.2f}% vs baseline "
                    f"(median separation changed by {sep_delta:+.2f}m)."
                )
            elif diff_prob > 0.0:
                observations.append(
                    f"Scenario '{comp.scenario_id}' increases collision probability by {diff_prob:.2f}% vs baseline "
                    f"(median separation changed by {sep_delta:+.2f}m)."
                )
            else:
                observations.append(
                    f"Scenario '{comp.scenario_id}' maintains identical collision probability to baseline "
                    f"(sep delta: {sep_delta:+.2f}m)."
                )

        return ScenarioComparisonResult(
            status="COMPARISON_COMPLETED",
            baseline_scenario_id=baseline_result.scenario_id,
            comparison_scenario_ids=[c.scenario_id for c in comparison_results],
            relative_risk_differences=rel_diffs,
            separation_deltas_m=sep_deltas,
            safer_scenario_id=safer_scenario,
            sensitivity_observations=observations,
            model_assumptions=[
                f"Baseline sample count: {baseline_result.sample_count}",
                f"Baseline horizon: {baseline_result.simulation_horizon_seconds}s",
            ],
        )
