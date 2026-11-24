"""
Trajectory Prediction and Time-Series Separation Analyzer (Day 37 / Phase 3).
Generates forward discrete trajectory projections for 2D and 3D entities,
computes dynamic time-series separation, and detects collision/near-miss temporal windows.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import (
    KinematicState,
    SafetyEnvelope,
)
from zye_realtime_tactical.kinematics.unit_converter import UnitConverter


class TrajectoryPredictor:
    """Computes vectorized time-series trajectory paths and inter-entity separation profiles."""

    @classmethod
    def predict_trajectories(
        cls,
        entity_a: KinematicState,
        entity_b: KinematicState,
        horizon_seconds: float = 10.0,
        time_step_seconds: float = 0.1,
        safety_envelope: Optional[SafetyEnvelope] = None,
        dimension: int = 2,
    ) -> Dict[str, Any]:
        """
        Project discrete time-series trajectories for entities A and B.
        Returns time points, positions, relative separations, collision windows, and near-miss intervals.
        """
        dim = int(dimension)
        if dim not in (2, 3):
            raise ValueError(f"Dimension must be 2 or 3, got: {dimension}")
        if horizon_seconds <= 0:
            raise ValueError(f"Horizon must be positive, got: {horizon_seconds}")
        if time_step_seconds <= 0 or time_step_seconds > horizon_seconds:
            time_step_seconds = min(0.1, horizon_seconds / 20.0)

        envelope = safety_envelope or SafetyEnvelope(
            combined_radius=entity_a.radius + entity_b.radius
        )

        # Validate dimensions
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

        a_a = np.array(entity_a.acceleration[:dim], dtype=np.float64) if has_acc_a else np.zeros(dim, dtype=np.float64)
        a_b = np.array(entity_b.acceleration[:dim], dtype=np.float64) if has_acc_b else np.zeros(dim, dtype=np.float64)

        # Time vector: shape (T, 1) for broadcasting
        t_steps = np.arange(0.0, horizon_seconds + (time_step_seconds * 0.5), time_step_seconds, dtype=np.float64)
        t_col = t_steps[:, np.newaxis]  # shape (T, 1)

        # Vectorized trajectories: p(t) = p0 + v0*t + 0.5*a*t^2 -> shape (T, dim)
        traj_a = p_a0 + (t_col * v_a0) + (0.5 * (t_col ** 2) * a_a)
        traj_b = p_b0 + (t_col * v_b0) + (0.5 * (t_col ** 2) * a_b)

        # Relative separation vector R(t) = traj_b - traj_a -> shape (T, dim)
        rel_pos = traj_b - traj_a
        # Separation distance d(t) = ||R(t)|| -> shape (T,)
        separations = np.linalg.norm(rel_pos, axis=1)

        min_idx = int(np.argmin(separations))
        min_sep = float(separations[min_idx])
        min_time = float(t_steps[min_idx])

        # Collision & Near-Miss Windows
        is_collision = separations <= envelope.combined_radius
        is_near_miss = separations <= envelope.near_miss_radius

        collision_window = cls._extract_temporal_window(t_steps, is_collision)
        near_miss_window = cls._extract_temporal_window(t_steps, is_near_miss)

        # Sample checkpoints for readable reporting (e.g. 0s, 25%, 50%, 75%, 100% of horizon)
        checkpoints_t = [0.0, horizon_seconds * 0.25, horizon_seconds * 0.5, horizon_seconds * 0.75, horizon_seconds]
        checkpoint_separations: Dict[str, float] = {}
        for cp in checkpoints_t:
            idx = int(np.argmin(np.abs(t_steps - cp)))
            checkpoint_separations[f"t_{cp:.1f}s"] = round(float(separations[idx]), 3)

        return {
            "entity_a_id": entity_a.entity_id,
            "entity_b_id": entity_b.entity_id,
            "dimension": dim,
            "horizon_seconds": horizon_seconds,
            "step_count": len(t_steps),
            "min_separation_m": round(min_sep, 4),
            "time_at_min_separation_sec": round(min_time, 4),
            "collision_detected": bool(np.any(is_collision)),
            "near_miss_detected": bool(np.any(is_near_miss)),
            "collision_window": collision_window,
            "near_miss_window": near_miss_window,
            "checkpoint_separations_m": checkpoint_separations,
            "initial_separation_m": round(float(separations[0]), 4),
            "final_separation_m": round(float(separations[-1]), 4),
        }

    @staticmethod
    def _extract_temporal_window(t_steps: np.ndarray, mask: np.ndarray) -> Optional[Dict[str, float]]:
        """Extract continuous time interval where condition is True."""
        indices = np.where(mask)[0]
        if len(indices) == 0:
            return None
        start_t = float(t_steps[indices[0]])
        end_t = float(t_steps[indices[-1]])
        duration = float(end_t - start_t)
        return {
            "start_time_sec": round(start_t, 3),
            "end_time_sec": round(end_t, 3),
            "duration_sec": round(duration, 3),
        }
