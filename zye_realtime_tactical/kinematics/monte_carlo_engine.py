"""
High-Speed Vectorized Monte Carlo Simulation Engine (Day 37 / Phase 3).
Simulates thousands (20,000+) of stochastic kinematic trajectory outcomes under uncertain
initial positions, velocities, and accelerations with sub-10ms target performance.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import (
    CoordinateDimension,
    DistributionType,
    KinematicState,
    MonteCarloResult,
    RiskCategory,
    SafetyEnvelope,
    UncertaintyConfig,
)
from zye_realtime_tactical.kinematics.risk_classifier import RiskClassifier
from zye_realtime_tactical.kinematics.statistical_analyzer import StatisticalAnalyzer
from zye_realtime_tactical.kinematics.uncertainty_distribution import UncertaintyDistributionSampler
from zye_realtime_tactical.kinematics.unit_converter import UnitConverter


class MonteCarloSimulationEngine:
    """High-performance vectorized Monte Carlo trajectory collision risk simulator."""

    @classmethod
    def run_simulation(
        cls,
        entity_a: KinematicState,
        entity_b: KinematicState,
        sample_count: int = 20000,
        horizon_seconds: float = 10.0,
        uncertainty_a: Optional[UncertaintyConfig] = None,
        uncertainty_b: Optional[UncertaintyConfig] = None,
        safety_envelope: Optional[SafetyEnvelope] = None,
        random_seed: Optional[int] = 42,
        dimension: int = 2,
    ) -> MonteCarloResult:
        """
        Executes a vectorized Monte Carlo simulation over N stochastic trajectory outcomes.
        Returns empirical collision probabilities, confidence intervals, and separation distributions.
        """
        t_total_start = time.perf_counter_ns()
        dim = int(dimension)
        if dim not in (2, 3):
            raise ValueError(f"Dimension must be 2 or 3, got: {dimension}")
        if sample_count <= 0:
            raise ValueError(f"Sample count must be positive, got: {sample_count}")
        if horizon_seconds <= 0.0:
            raise ValueError(f"Simulation horizon must be positive, got: {horizon_seconds}")

        envelope = safety_envelope or SafetyEnvelope(
            combined_radius=entity_a.radius + entity_b.radius
        )

        # Validate base vectors
        UnitConverter.validate_dimension(entity_a.position, dim, "entity_a.position")
        UnitConverter.validate_dimension(entity_b.position, dim, "entity_b.position")
        UnitConverter.validate_dimension(entity_a.velocity, dim, "entity_a.velocity")
        UnitConverter.validate_dimension(entity_b.velocity, dim, "entity_b.velocity")

        p_a0 = np.array(entity_a.position[:dim], dtype=np.float64)
        p_b0 = np.array(entity_b.position[:dim], dtype=np.float64)
        v_a0 = np.array(entity_a.velocity[:dim], dtype=np.float64)
        v_b0 = np.array(entity_b.velocity[:dim], dtype=np.float64)

        has_acc_a = entity_a.acceleration is not None and len(entity_a.acceleration) >= dim
        has_acc_b = entity_b.acceleration is not None and len(entity_b.acceleration) >= dim
        a_a0 = np.array(entity_a.acceleration[:dim], dtype=np.float64) if has_acc_a else np.zeros(dim, dtype=np.float64)
        a_b0 = np.array(entity_b.acceleration[:dim], dtype=np.float64) if has_acc_b else np.zeros(dim, dtype=np.float64)

        is_accelerated = bool(np.any(np.abs(a_a0) > 1e-6) or np.any(np.abs(a_b0) > 1e-6))

        # Setup PRNG generator with deterministic seed if provided
        rng = np.random.default_rng(random_seed)

        # ---------------------------------------------------------------------
        # 1. Vectorized Stochastic State Sampling
        # ---------------------------------------------------------------------
        t_sample_start = time.perf_counter_ns()

        unc_a = uncertainty_a or UncertaintyConfig(
            pos_std=entity_a.uncertainty_pos[:dim] if entity_a.uncertainty_pos else [0.5] * dim,
            vel_std=entity_a.uncertainty_vel[:dim] if entity_a.uncertainty_vel else [0.2] * dim,
        )
        unc_b = uncertainty_b or UncertaintyConfig(
            pos_std=entity_b.uncertainty_pos[:dim] if entity_b.uncertainty_pos else [0.5] * dim,
            vel_std=entity_b.uncertainty_vel[:dim] if entity_b.uncertainty_vel else [0.2] * dim,
        )

        # Sample initial positions: shape (N, dim)
        p_a_samples = UncertaintyDistributionSampler.sample_perturbations(
            base_vector=p_a0,
            std_vector=np.array(unc_a.pos_std[:dim], dtype=np.float64) if unc_a.pos_std else None,
            cov_matrix=np.array(unc_a.pos_cov, dtype=np.float64) if unc_a.pos_cov else None,
            sample_count=sample_count,
            distribution_type=unc_a.distribution_type,
            rng=rng,
        )
        p_b_samples = UncertaintyDistributionSampler.sample_perturbations(
            base_vector=p_b0,
            std_vector=np.array(unc_b.pos_std[:dim], dtype=np.float64) if unc_b.pos_std else None,
            cov_matrix=np.array(unc_b.pos_cov, dtype=np.float64) if unc_b.pos_cov else None,
            sample_count=sample_count,
            distribution_type=unc_b.distribution_type,
            rng=rng,
        )

        # Sample initial velocities: shape (N, dim)
        v_a_samples = UncertaintyDistributionSampler.sample_perturbations(
            base_vector=v_a0,
            std_vector=np.array(unc_a.vel_std[:dim], dtype=np.float64) if unc_a.vel_std else None,
            cov_matrix=np.array(unc_a.vel_cov, dtype=np.float64) if unc_a.vel_cov else None,
            sample_count=sample_count,
            distribution_type=unc_a.distribution_type,
            rng=rng,
        )
        v_b_samples = UncertaintyDistributionSampler.sample_perturbations(
            base_vector=v_b0,
            std_vector=np.array(unc_b.vel_std[:dim], dtype=np.float64) if unc_b.vel_std else None,
            cov_matrix=np.array(unc_b.vel_cov, dtype=np.float64) if unc_b.vel_cov else None,
            sample_count=sample_count,
            distribution_type=unc_b.distribution_type,
            rng=rng,
        )

        # Sample acceleration if accelerated
        if is_accelerated:
            a_a_samples = UncertaintyDistributionSampler.sample_perturbations(
                base_vector=a_a0,
                std_vector=np.array(unc_a.accel_std[:dim], dtype=np.float64) if unc_a.accel_std else None,
                cov_matrix=None,
                sample_count=sample_count,
                distribution_type=unc_a.distribution_type,
                rng=rng,
            )
            a_b_samples = UncertaintyDistributionSampler.sample_perturbations(
                base_vector=a_b0,
                std_vector=np.array(unc_b.accel_std[:dim], dtype=np.float64) if unc_b.accel_std else None,
                cov_matrix=None,
                sample_count=sample_count,
                distribution_type=unc_b.distribution_type,
                rng=rng,
            )
            rel_a = a_b_samples - a_a_samples
        else:
            rel_a = None

        t_sample_end = time.perf_counter_ns()

        # ---------------------------------------------------------------------
        # 2. Vectorized Trajectory Separation & CPA Analysis
        # ---------------------------------------------------------------------
        t_comp_start = time.perf_counter_ns()

        # Relative state matrices: R and V of shape (N, dim)
        rel_r = p_b_samples - p_a_samples
        rel_v = v_b_samples - v_a_samples

        if not is_accelerated or rel_a is None:
            # PURE VECTORIZED LINEAR CPA (Target < 10ms for 20k samples)
            # R . V = sum_k(R_k * V_k) -> shape (N,)
            r_dot_v = np.sum(rel_r * rel_v, axis=1)
            # V . V = sum_k(V_k^2) -> shape (N,)
            v_sq = np.sum(rel_v * rel_v, axis=1)

            # Avoid division by zero when relative speed is negligible
            zero_v_mask = v_sq <= 1e-12
            safe_v_sq = np.where(zero_v_mask, 1.0, v_sq)

            # t_cpa unclamped = -(R . V) / ||V||^2
            t_cpa_unclamped = -r_dot_v / safe_v_sq
            # Clamped to [0, horizon]
            t_cpa = np.clip(t_cpa_unclamped, 0.0, horizon_seconds)
            t_cpa = np.where(zero_v_mask, 0.0, t_cpa)

            # P_CPA = R + V * t_CPA -> shape (N, dim)
            pos_cpa = rel_r + (rel_v * t_cpa[:, np.newaxis])
            # d_CPA = ||P_CPA|| -> shape (N,)
            min_separations = np.linalg.norm(pos_cpa, axis=1)

        else:
            # VECTORIZED ACCELERATED GRID/CUBIC SAMPLING
            # Time grid for broad evaluation across N samples: shape (T, 1, 1)
            t_grid = np.linspace(0.0, horizon_seconds, num=50, dtype=np.float64)  # (T,)
            # rel_r: (N, dim) -> (1, N, dim)
            # rel_v: (N, dim) -> (1, N, dim)
            # rel_a: (N, dim) -> (1, N, dim)
            # t: (T, 1, 1)
            r_exp = rel_r[np.newaxis, :, :]
            v_exp = rel_v[np.newaxis, :, :]
            a_exp = rel_a[np.newaxis, :, :]
            t_exp = t_grid[:, np.newaxis, np.newaxis]

            # pos_grid: (T, N, dim) = r + v*t + 0.5*a*t^2
            pos_grid = r_exp + (v_exp * t_exp) + (0.5 * a_exp * (t_exp ** 2))
            # sep_grid: (T, N) = ||pos_grid||
            sep_grid = np.linalg.norm(pos_grid, axis=2)
            # min_separations: minimum along time axis -> shape (N,)
            min_separations = np.min(sep_grid, axis=0)

        # ---------------------------------------------------------------------
        # 3. Probabilistic Event Detection & Statistics
        # ---------------------------------------------------------------------
        collision_mask = min_separations <= envelope.combined_radius
        near_miss_mask = min_separations <= envelope.near_miss_radius

        collision_count = int(np.sum(collision_mask))
        near_miss_count = int(np.sum(near_miss_mask))

        collision_prob = float(collision_count / sample_count)
        near_miss_prob = float(near_miss_count / sample_count)

        dist_summary = StatisticalAnalyzer.summarize_distribution(min_separations)
        conf_interval = StatisticalAnalyzer.calculate_wilson_score_interval(
            success_count=collision_count,
            sample_count=sample_count,
            confidence_level=0.95,
        )

        t_comp_end = time.perf_counter_ns()
        total_time_ms = round((t_comp_end - t_total_start) / 1e6, 3)
        throughput = round((sample_count / (total_time_ms / 1000.0)), 1) if total_time_ms > 0 else 0.0

        risk_category, risk_explanation = RiskClassifier.classify_probabilistic_risk(
            collision_prob=collision_prob,
            near_miss_prob=near_miss_prob,
            p05_separation=dist_summary["p05"],
            median_separation=dist_summary["median"],
            envelope=envelope,
        )

        assumptions = [
            f"COORDINATE_DIMENSION_{dim}D",
            "CONSTANT_ACCELERATION_MODEL" if is_accelerated else "CONSTANT_VELOCITY_MODEL",
            f"STOCHASTIC_SAMPLE_COUNT_{sample_count}",
            f"HORIZON_{horizon_seconds}S",
            f"DISTRIBUTION_{unc_a.distribution_type.value}",
        ]
        warnings = []
        if collision_count == 0:
            warnings.append(
                f"Zero collisions observed in {sample_count} samples. True probability is bounded by "
                f"95% Wilson upper bound ({conf_interval.upper:.6f}), not strictly zero."
            )

        timing_breakdown = {
            "sampling_ms": round((t_sample_end - t_sample_start) / 1e6, 3),
            "kinematic_eval_ms": round((t_comp_end - t_comp_start) / 1e6, 3),
            "statistics_ms": round((t_comp_end - t_sample_end) / 1e6, 3),
        }

        return MonteCarloResult(
            status="SIMULATION_COMPLETED",
            scenario_id=f"mc_{entity_a.entity_id}_{entity_b.entity_id}_{int(time.time())}",
            model="KINEMATIC_MONTE_CARLO",
            dimension=dim,
            sample_count=sample_count,
            simulation_horizon_seconds=horizon_seconds,
            collision_count=collision_count,
            collision_probability=round(collision_prob, 6),
            near_miss_count=near_miss_count,
            near_miss_probability=round(near_miss_prob, 6),
            min_separation_m=dist_summary["min"],
            median_separation_m=dist_summary["median"],
            mean_separation_m=dist_summary["mean"],
            p05_separation_m=dist_summary["p05"],
            p95_separation_m=dist_summary["p95"],
            std_separation_m=dist_summary["std"],
            confidence_interval=conf_interval,
            random_seed=random_seed,
            execution_time_ms=total_time_ms,
            throughput_samples_per_sec=throughput,
            risk_category=risk_category,
            risk_explanation=risk_explanation,
            assumptions=assumptions,
            warnings=warnings,
            metadata={"timing_breakdown": timing_breakdown},
            verified=True,
        )
