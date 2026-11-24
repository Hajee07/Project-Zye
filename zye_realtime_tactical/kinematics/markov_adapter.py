"""
Day 36 Markov Prediction Adapter (Day 37 / Phase 3).
Maps empirical opponent Markov next-action probability distributions and inter-action timing
into probabilistic kinematic acceleration and velocity perturbations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import UncertaintyConfig
from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager
from zye_realtime_tactical.opponent.opponent_prediction_engine import OpponentPredictionEngine


# Mapping canonical tactical actions to physical acceleration modifier vectors [ax, ay] in m/s^2
ACTION_KINEMATIC_PROFILES: Dict[str, List[float]] = {
    "attack": [2.5, 0.0],      # Forward acceleration burst toward target
    "punch": [3.0, 0.0],       # Rapid direct surge
    "kick": [2.8, -0.5],
    "lunge": [4.0, 0.0],       # Aggressive forward leap
    "charge": [5.0, 0.0],      # Heavy forward rush
    "dodge": [-1.0, 2.5],      # Lateral evasive acceleration
    "guard": [-0.5, 0.0],      # Deceleration to braced stance
    "retreat": [-3.0, 0.0],    # Rapid reverse acceleration
    "idle": [0.0, 0.0],
}


class MarkovPredictionAdapter:
    """Transforms Day 36 empirical Markov transition distributions into kinematic simulation priors."""

    def __init__(self, buffer_manager: Optional[OpponentBufferManager] = None) -> None:
        self.buffer_manager = buffer_manager or OpponentBufferManager.get_instance()
        self.engine = OpponentPredictionEngine(buffer_manager=self.buffer_manager)

    def extract_tactical_acceleration_prior(
        self,
        opponent_id: str,
        dimension: int = 2,
    ) -> Tuple[str, Optional[List[float]], Optional[UncertaintyConfig], Dict[str, Any]]:
        """
        Retrieves active Markov predictions for opponent_id and calculates expected acceleration bias.
        Returns:
            (status, expected_accel_or_None, conditioned_uncertainty_or_None, metadata)
        Status values:
            - MARKOV_CONDITIONED: Valid multi-action probability distribution applied
            - INSUFFICIENT_DATA: Buffer has < 6 observations; baseline kinematic model recommended
            - NO_REPEAT_FOUND: Transitions observed but no repeating pattern; baseline recommended
            - NOT_FOUND: Opponent sequence buffer uninitialized
        """
        buf = self.buffer_manager.sequence_manager.get_buffer(opponent_id)
        if buf is None or buf.size == 0:
            return "NOT_FOUND", None, None, {"message": f"Opponent '{opponent_id}' has no buffered actions."}

        actions = buf.get_all_actions()
        if len(actions) < 6:
            return (
                "INSUFFICIENT_DATA",
                None,
                None,
                {"message": f"Opponent '{opponent_id}' has only {len(actions)} actions (minimum 6 required)."},
            )

        # Execute Day 36 Markov prediction
        pred_res = self.engine.predict_opponent_attack(opponent_id=opponent_id, observed_actions=[])

        if pred_res.status != "PREDICTION_AVAILABLE" or not pred_res.next_attack_probabilities:
            return (
                pred_res.status,
                None,
                None,
                {"message": f"Markov engine returned status: {pred_res.status}"},
            )

        # Compute probability-weighted acceleration vector: E[a] = sum(P_i * a_i)
        dim = int(dimension)
        weighted_accel = np.zeros(dim, dtype=np.float64)
        total_weight = 0.0
        action_breakdown: List[Dict[str, Any]] = []

        for cand in pred_res.next_attack_probabilities:
            prob = cand.probability_pct / 100.0
            act_name = cand.predicted_action.lower().strip()
            profile = ACTION_KINEMATIC_PROFILES.get(act_name, [0.0] * dim)

            acc_vec = np.array(profile[:dim], dtype=np.float64)
            weighted_accel += prob * acc_vec
            total_weight += prob

            action_breakdown.append({
                "action": act_name,
                "probability": round(prob, 4),
                "accel_profile": [round(float(x), 2) for x in acc_vec],
            })

        # Normalize if non-zero
        if total_weight > 0.0:
            expected_a = (weighted_accel / total_weight).tolist()
        else:
            expected_a = [0.0] * dim

        # Compute higher uncertainty if distribution has high entropy
        std_acc = max(1.0, float(np.std(weighted_accel)))
        uncertainty = UncertaintyConfig(
            accel_std=[round(std_acc, 2)] * dim,
            reaction_delay_mean=pred_res.expected_next_attack_in_sec or 0.5,
        )

        metadata = {
            "opponent_id": opponent_id,
            "prediction_basis": pred_res.prediction_basis,
            "action_breakdown": action_breakdown,
            "expected_next_attack_in_sec": pred_res.expected_next_attack_in_sec,
        }

        return "MARKOV_CONDITIONED", [round(float(x), 4) for x in expected_a], uncertainty, metadata
