"""
Deterministic Kinematic Mathematics Engine (Day 37 / Phase 3).
Provides exact analytical calculations for 2D and 3D relative motion, Closest Point of Approach (CPA),
Time to Closest Point of Approach (TCPA), Time to Collision (TTC), closing speed, and accelerated trajectories.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import (
    CoordinateDimension,
    KinematicRiskResult,
    KinematicState,
    RiskCategory,
    SafetyEnvelope,
)
from zye_realtime_tactical.kinematics.unit_converter import UnitConverter


class KinematicEngine:
    """Core deterministic physics and vector mathematics engine for kinematic accident risk."""

    @classmethod
    def calculate_risk(
        cls,
        entity_a: KinematicState,
        entity_b: KinematicState,
        horizon_seconds: float = 10.0,
        safety_envelope: Optional[SafetyEnvelope] = None,
        dimension: int = 2,
    ) -> KinematicRiskResult:
        """
        Perform rigorous deterministic kinematic analysis between two entities.
        Supports both 2D and 3D coordinate frames with constant-velocity or constant-acceleration models.
        """
        t_start = time.perf_counter_ns()
        dim = int(dimension)
        if dim not in (2, 3):
            raise ValueError(f"Dimension must be 2 or 3, got: {dimension}")

        envelope = safety_envelope or SafetyEnvelope(
            combined_radius=entity_a.radius + entity_b.radius
        )

        # Validate input dimensions
        UnitConverter.validate_dimension(entity_a.position, dim, f"{entity_a.entity_id}.position")
        UnitConverter.validate_dimension(entity_b.position, dim, f"{entity_b.entity_id}.position")
        UnitConverter.validate_dimension(entity_a.velocity, dim, f"{entity_a.entity_id}.velocity")
        UnitConverter.validate_dimension(entity_b.velocity, dim, f"{entity_b.entity_id}.velocity")

        pos_a = np.array(entity_a.position[:dim], dtype=np.float64)
        pos_b = np.array(entity_b.position[:dim], dtype=np.float64)
        vel_a = np.array(entity_a.velocity[:dim], dtype=np.float64)
        vel_b = np.array(entity_b.velocity[:dim], dtype=np.float64)

        has_accel_a = entity_a.acceleration is not None and len(entity_a.acceleration) >= dim
        has_accel_b = entity_b.acceleration is not None and len(entity_b.acceleration) >= dim

        acc_a = np.array(entity_a.acceleration[:dim], dtype=np.float64) if has_accel_a else np.zeros(dim, dtype=np.float64)
        acc_b = np.array(entity_b.acceleration[:dim], dtype=np.float64) if has_accel_b else np.zeros(dim, dtype=np.float64)

        # Relative Vectors: r = pB - pA, v = vB - vA, a = aB - aA
        r = pos_b - pos_a
        v = vel_b - vel_a
        a = acc_b - acc_a

        current_dist = float(np.linalg.norm(r))
        v_norm = float(np.linalg.norm(v))
        r_dot_v = float(np.dot(r, v))

        # Closing Speed: -(r . v) / ||r|| (positive = approaching, negative = separating)
        if current_dist > 1e-9:
            closing_speed = -r_dot_v / current_dist
        else:
            closing_speed = 0.0

        is_approaching = r_dot_v < -1e-9

        assumptions: List[str] = [f"COORDINATE_DIMENSION_{dim}D"]
        warnings: List[str] = []

        # Check if acceleration is present
        is_accelerated = bool(np.any(np.abs(a) > 1e-6))
        if is_accelerated:
            assumptions.append("CONSTANT_ACCELERATION_MODEL")
            tcpa, d_cpa = cls._calculate_cpa_accelerated(r, v, a, horizon_seconds)
            ttc = cls._calculate_ttc_accelerated(r, v, a, envelope.combined_radius, horizon_seconds)
        else:
            assumptions.append("CONSTANT_VELOCITY_MODEL")
            if not has_accel_a and not has_accel_b:
                warnings.append("Acceleration unavailable for both entities; fallback to constant-velocity model.")
            tcpa, d_cpa = cls._calculate_cpa_linear(r, v, horizon_seconds)
            ttc = cls._calculate_ttc_linear(r, v, envelope.combined_radius, horizon_seconds)

        # Assess collisions and envelopes
        collision_detected = (current_dist <= envelope.combined_radius) or (d_cpa <= envelope.combined_radius and tcpa <= horizon_seconds)
        near_miss_detected = (d_cpa <= envelope.near_miss_radius and tcpa <= horizon_seconds)

        # Determine risk classification
        risk_cat, risk_explanation = cls._classify_deterministic_risk(
            current_dist=current_dist,
            d_cpa=d_cpa,
            tcpa=tcpa,
            ttc=ttc,
            closing_speed=closing_speed,
            is_approaching=is_approaching,
            envelope=envelope,
            horizon_seconds=horizon_seconds,
        )

        compute_ms = round((time.perf_counter_ns() - t_start) / 1e6, 4)

        status_str = "COLLISION_IMMINENT" if collision_detected else ("NEAR_MISS_WINDOW" if near_miss_detected else "ANALYSIS_COMPLETED")

        return KinematicRiskResult(
            status=status_str,
            dimension=dim,
            entity_a_id=entity_a.entity_id,
            entity_b_id=entity_b.entity_id,
            relative_position=[round(float(x), 4) for x in r],
            relative_velocity=[round(float(x), 4) for x in v],
            relative_acceleration=[round(float(x), 4) for x in a] if is_accelerated else None,
            current_distance_m=round(current_dist, 4),
            closing_speed_mps=round(closing_speed, 4),
            is_approaching=is_approaching,
            cpa_time_sec=round(tcpa, 4),
            min_separation_m=round(d_cpa, 4),
            ttc_sec=round(ttc, 4) if ttc is not None else None,
            collision_detected=collision_detected,
            near_miss_detected=near_miss_detected,
            risk_category=risk_cat,
            risk_explanation=risk_explanation,
            assumptions=assumptions,
            warnings=warnings,
            compute_time_ms=compute_ms,
        )

    # -------------------------------------------------------------------------
    # Analytical CPA Methods
    # -------------------------------------------------------------------------
    @classmethod
    def _calculate_cpa_linear(cls, r: np.ndarray, v: np.ndarray, horizon: float) -> Tuple[float, float]:
        """
        Closest Point of Approach for constant relative velocity.
        t_CPA = -(r . v) / ||v||^2, clamped to [0, horizon].
        d_CPA = ||r + v * t_CPA||.
        """
        v_sq = float(np.dot(v, v))
        if v_sq <= 1e-12:
            # Zero relative velocity: separation remains constant
            return 0.0, float(np.linalg.norm(r))

        r_dot_v = float(np.dot(r, v))
        t_cpa_unclamped = -r_dot_v / v_sq
        t_cpa = max(0.0, min(float(t_cpa_unclamped), float(horizon)))

        pos_at_cpa = r + v * t_cpa
        d_cpa = float(np.linalg.norm(pos_at_cpa))
        return t_cpa, d_cpa

    @classmethod
    def _calculate_cpa_accelerated(cls, r: np.ndarray, v: np.ndarray, a: np.ndarray, horizon: float) -> Tuple[float, float]:
        """
        Closest Point of Approach for constant relative acceleration.
        Separation squared D(t) = ||r + v*t + 0.5*a*t^2||^2.
        Derivative D'(t) = 2 * (r + v*t + 0.5*a*t^2) . (v + a*t) = 0.
        Yields a cubic polynomial: c3*t^3 + c2*t^2 + c1*t + c0 = 0.
        """
        # Coefficients of cubic polynomial D'(t) / 2 = 0
        c3 = 0.5 * float(np.dot(a, a))
        c2 = 1.5 * float(np.dot(a, v))
        c1 = float(np.dot(v, v)) + float(np.dot(a, r))
        c0 = float(np.dot(r, v))

        candidate_times = [0.0, float(horizon)]

        if abs(c3) > 1e-9:
            # Solve cubic
            roots = np.roots([c3, c2, c1, c0])
            for rt in roots:
                if np.isreal(rt):
                    real_t = float(np.real(rt))
                    if 0.0 <= real_t <= horizon:
                        candidate_times.append(real_t)
        elif abs(c2) > 1e-9:
            # Degenerate quadratic
            roots = np.roots([c2, c1, c0])
            for rt in roots:
                if np.isreal(rt):
                    real_t = float(np.real(rt))
                    if 0.0 <= real_t <= horizon:
                        candidate_times.append(real_t)
        elif abs(c1) > 1e-9:
            # Linear fallback
            linear_t = -c0 / c1
            if 0.0 <= linear_t <= horizon:
                candidate_times.append(linear_t)

        # Evaluate separation at all critical points
        best_t = 0.0
        min_d = float("inf")

        for t_eval in candidate_times:
            pos_t = r + v * t_eval + 0.5 * a * (t_eval ** 2)
            d_val = float(np.linalg.norm(pos_t))
            if d_val < min_d:
                min_d = d_val
                best_t = t_eval

        return best_t, min_d

    # -------------------------------------------------------------------------
    # Analytical TTC (Time To Collision) Methods
    # -------------------------------------------------------------------------
    @classmethod
    def _calculate_ttc_linear(cls, r: np.ndarray, v: np.ndarray, radius: float, horizon: float) -> Optional[float]:
        """
        Calculates exact Time to Collision for constant velocity.
        Solves ||r + vt||^2 = R^2 => ||v||^2 t^2 + 2(r.v) t + (||r||^2 - R^2) = 0.
        """
        r_sq = float(np.dot(r, r))
        radius_sq = radius * radius

        # Initial overlap
        if r_sq <= radius_sq:
            return 0.0

        v_sq = float(np.dot(v, v))
        if v_sq <= 1e-12:
            return None  # Stationary relative to each other; no collision

        r_dot_v = float(np.dot(r, v))
        # If moving apart, no collision in forward time
        if r_dot_v >= 0.0:
            return None

        # Quadratic equation A t^2 + B t + C = 0
        a_coeff = v_sq
        b_coeff = 2.0 * r_dot_v
        c_coeff = r_sq - radius_sq

        disc = b_coeff * b_coeff - 4.0 * a_coeff * c_coeff
        if disc < 0.0:
            return None  # Misses envelope entirely

        sqrt_disc = math.sqrt(disc)
        t1 = (-b_coeff - sqrt_disc) / (2.0 * a_coeff)
        t2 = (-b_coeff + sqrt_disc) / (2.0 * a_coeff)

        # Select earliest positive collision time within horizon
        if 0.0 <= t1 <= horizon:
            return t1
        elif 0.0 <= t2 <= horizon:
            return t2
        return None

    @classmethod
    def _calculate_ttc_accelerated(cls, r: np.ndarray, v: np.ndarray, a: np.ndarray, radius: float, horizon: float) -> Optional[float]:
        """
        Calculates Time to Collision for accelerated motion.
        Solves ||r + vt + 0.5*a*t^2|| = R on t in [0, horizon].
        """
        # Initial overlap check
        if float(np.linalg.norm(r)) <= radius:
            return 0.0

        # High-resolution time-domain bracket scan
        steps = 200
        dt = horizon / steps
        t_prev = 0.0
        d_prev = float(np.linalg.norm(r)) - radius

        for step in range(1, steps + 1):
            t_curr = step * dt
            pos_curr = r + v * t_curr + 0.5 * a * (t_curr ** 2)
            d_curr = float(np.linalg.norm(pos_curr)) - radius

            if d_curr <= 0.0:
                # Sign change found between t_prev and t_curr; apply bisection / secant refinement
                t_low = t_prev
                t_high = t_curr
                for _ in range(25):
                    t_mid = 0.5 * (t_low + t_high)
                    pos_mid = r + v * t_mid + 0.5 * a * (t_mid ** 2)
                    d_mid = float(np.linalg.norm(pos_mid)) - radius
                    if abs(d_mid) < 1e-5:
                        return t_mid
                    if d_mid > 0:
                        t_low = t_mid
                    else:
                        t_high = t_mid
                return 0.5 * (t_low + t_high)

            t_prev = t_curr
            d_prev = d_curr

        return None

    # -------------------------------------------------------------------------
    # Deterministic Risk Categorization
    # -------------------------------------------------------------------------
    @classmethod
    def _classify_deterministic_risk(
        cls,
        current_dist: float,
        d_cpa: float,
        tcpa: float,
        ttc: Optional[float],
        closing_speed: float,
        is_approaching: bool,
        envelope: SafetyEnvelope,
        horizon_seconds: float,
    ) -> Tuple[RiskCategory, str]:
        """Transparent, rule-based risk classification based on physical separation and closure."""
        # 1. Immediate overlap
        if current_dist <= envelope.combined_radius:
            return RiskCategory.CRITICAL, f"Entities are in physical overlap at t=0 (dist={current_dist:.2f}m <= radius={envelope.combined_radius:.2f}m)."

        # 2. Collision within horizon
        if ttc is not None and ttc <= horizon_seconds:
            if ttc <= 3.0:
                return RiskCategory.CRITICAL, f"Collision predicted in {ttc:.2f}s (d_CPA={d_cpa:.2f}m <= envelope={envelope.combined_radius:.2f}m, closing speed={closing_speed:.1f}m/s)."
            else:
                return RiskCategory.HIGH, f"Collision trajectory detected within horizon (TTC={ttc:.2f}s, TCPA={tcpa:.2f}s, d_CPA={d_cpa:.2f}m)."

        # 3. Near-miss within safety envelope
        if d_cpa <= envelope.near_miss_radius and is_approaching:
            if d_cpa <= (envelope.combined_radius + envelope.clearance_margin * 0.5):
                return RiskCategory.HIGH, f"Close proximity near-miss predicted at t={tcpa:.2f}s (d_CPA={d_cpa:.2f}m within safety envelope {envelope.near_miss_radius:.2f}m)."
            else:
                return RiskCategory.MODERATE, f"Near-miss corridor penetration predicted at t={tcpa:.2f}s (d_CPA={d_cpa:.2f}m, clearance={envelope.clearance_margin:.1f}m)."

        # 4. Approaching but safe CPA
        if is_approaching:
            return RiskCategory.LOW, f"Entities are closing (speed={closing_speed:.1f}m/s), but CPA maintains safe clearance (d_CPA={d_cpa:.2f}m > envelope={envelope.near_miss_radius:.2f}m at t={tcpa:.2f}s)."

        # 5. Diverging / Receding
        return RiskCategory.MINIMAL, f"Entities are separating or parallel (closing speed={closing_speed:.1f}m/s <= 0, minimum separation={d_cpa:.2f}m)."
