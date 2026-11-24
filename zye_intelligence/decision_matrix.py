"""
Multi-Solution Comparison and Decision Engine — Zye Day 13.
Evaluates 2-4 candidate solutions against weighted criteria (Reliability, Speed, Safety, Simplicity)
across 4 priority modes with hard safety veto constraints.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from zye_intelligence.schemas import DecisionResult, SolutionCandidate

logger = logging.getLogger("zye.intelligence.decision_matrix")

PRIORITY_WEIGHTS: dict[str, dict[str, float]] = {
    "balanced": {
        "reliability": 0.35,
        "speed": 0.25,
        "safety": 0.25,
        "simplicity": 0.15,
    },
    "speed_critical": {
        "reliability": 0.25,
        "speed": 0.50,
        "safety": 0.15,
        "simplicity": 0.10,
    },
    "maximum_safety": {
        "reliability": 0.35,
        "speed": 0.10,
        "safety": 0.45,
        "simplicity": 0.10,
    },
    "low_resource": {
        "reliability": 0.30,
        "speed": 0.30,
        "safety": 0.15,
        "simplicity": 0.25,
    },
}

DEFAULT_SAFETY_THRESHOLD = 3.0  # Solutions with safety below this are vetoed


class ZyeDecisionMatrix:
    """
    Evaluates competing solution candidates objectively using weighted multi-criteria decision analysis.
    Prevents unsafe solutions from winning purely on speed or simplicity.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self.safety_threshold = float(self._config.get("safety_threshold", DEFAULT_SAFETY_THRESHOLD))

    def calculate_weighted_score(
        self, candidate: dict[str, Any], weights: dict[str, float]
    ) -> float:
        """Calculate weighted score for a candidate across 4 dimensions."""
        rel = float(candidate.get("reliability", 5.0))
        spd = float(candidate.get("speed", 5.0))
        saf = float(candidate.get("safety", 5.0))
        sim = float(candidate.get("simplicity", 5.0))

        score = (
            rel * weights.get("reliability", 0.35)
            + spd * weights.get("speed", 0.25)
            + saf * weights.get("safety", 0.25)
            + sim * weights.get("simplicity", 0.15)
        )
        return round(score, 3)

    def rank_solutions(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Sort candidates descending by weighted_score, with safety as deterministic tie-breaker."""
        return sorted(
            candidates,
            key=lambda c: (c.get("weighted_score", 0.0), c.get("safety", 0.0), c.get("reliability", 0.0)),
            reverse=True,
        )

    def compare_solutions(
        self,
        problem_statement: str,
        candidate_solutions: list[dict[str, Any]],
        priority_mode: str = "balanced",
    ) -> dict[str, Any]:
        """
        Compare solutions, calculate weighted scores, rank, and explain recommendation.
        Returns comprehensive DecisionResult dictionary matching Section 10 output requirements.
        """
        if not problem_statement or not str(problem_statement).strip():
            raise ValueError("problem_statement must not be empty")

        mode = str(priority_mode).strip().lower()
        if mode not in PRIORITY_WEIGHTS:
            valid_modes = list(PRIORITY_WEIGHTS.keys())
            raise ValueError(f"Unknown priority mode '{priority_mode}'. Valid modes: {valid_modes}")

        if not candidate_solutions or len(candidate_solutions) == 0:
            raise ValueError("At least one candidate solution is required for comparison")

        weights = PRIORITY_WEIGHTS[mode]
        # Validate that weights sum to 1.0 (within float tolerance)
        weight_sum = sum(weights.values())
        if abs(weight_sum - 1.0) > 1e-6:
            raise ValueError(f"Weight group for mode '{mode}' does not total 1.0 (got {weight_sum})")

        validated_candidates: list[dict[str, Any]] = []
        weighted_scores: dict[str, float] = {}
        reliability_scores: dict[str, float] = {}
        speed_scores: dict[str, float] = {}
        safety_scores: dict[str, float] = {}
        simplicity_scores: dict[str, float] = {}
        pros_dict: dict[str, list[str]] = {}
        cons_dict: dict[str, list[str]] = {}
        resources_dict: dict[str, str] = {}
        uncertainties: list[str] = []

        # Validate each candidate via Pydantic SolutionCandidate
        for cand in candidate_solutions:
            if not isinstance(cand, dict):
                raise ValueError(f"Candidate solution must be a dictionary, got {type(cand).__name__}")
            validated = SolutionCandidate(**cand).model_dump()
            score = self.calculate_weighted_score(validated, weights)
            validated["weighted_score"] = score
            validated_candidates.append(validated)

            c_name = validated["name"]
            weighted_scores[c_name] = score
            reliability_scores[c_name] = validated["reliability"]
            speed_scores[c_name] = validated["speed"]
            safety_scores[c_name] = validated["safety"]
            simplicity_scores[c_name] = validated["simplicity"]
            pros_dict[c_name] = validated.get("pros", [])
            cons_dict[c_name] = validated.get("cons", [])
            resources_dict[c_name] = validated.get("resource_requirements", "Normal")

            if not validated.get("rationale"):
                uncertainties.append(f"Candidate '{c_name}' scores are estimates without provided empirical benchmark.")

        # Rank solutions descending
        ranked = self.rank_solutions(validated_candidates)

        # Check safety constraint
        safe_candidates = [c for c in ranked if c.get("safety", 0.0) >= self.safety_threshold]

        if not safe_candidates:
            # No candidate meets minimum safety cutoff
            rec_reason = (
                f"NO_SAFE_SOLUTION: None of the {len(ranked)} candidate solutions met the minimum "
                f"safety threshold ({self.safety_threshold:.1f}/10). Recommend proposing a safer alternative."
            )
            return {
                "problem": problem_statement,
                "priority_mode": mode,
                "candidates": validated_candidates,
                "weighted_scores": weighted_scores,
                "reliability_scores": reliability_scores,
                "speed_scores": speed_scores,
                "safety_scores": safety_scores,
                "simplicity_scores": simplicity_scores,
                "pros": pros_dict,
                "cons": cons_dict,
                "resource_requirements": resources_dict,
                "risk_analysis": {
                    "status": "NO_SAFE_SOLUTION",
                    "highest_unmet_safety": max(c.get("safety", 0.0) for c in ranked),
                    "threshold_required": self.safety_threshold,
                },
                "recommended_best_solution": {
                    "name": "NO_SAFE_SOLUTION",
                    "status": "REJECTED_ON_SAFETY",
                    "reason": rec_reason,
                },
                "full_comparison_ranking": ranked,
                "recommendation_reason": rec_reason,
                "unresolved_uncertainties": uncertainties + ["All candidates pose excessive safety risks"],
                "tradeoffs": [f"Candidate '{c['name']}' rejected due to safety {c['safety']:.1f} < {self.safety_threshold:.1f}" for c in ranked],
            }

        # Select highest-ranked safe solution
        best_safe = safe_candidates[0]
        if best_safe["name"] != ranked[0]["name"]:
            rec_reason = (
                f"Top weighted solution '{ranked[0]['name']}' was REJECTED (vetoed) due to unsafe score "
                f"({ranked[0]['safety']:.1f} < {self.safety_threshold:.1f}). "
                f"Selected highest-ranked safe alternative '{best_safe['name']}' (Score: {best_safe['weighted_score']:.2f})."
            )
        else:
            rec_reason = (
                f"Recommended '{best_safe['name']}' with highest weighted score of {best_safe['weighted_score']:.2f} "
                f"under '{mode}' priority mode (Safety: {best_safe['safety']:.1f}, Reliability: {best_safe['reliability']:.1f})."
            )

        tradeoffs = [
            f"'{c['name']}': weighted={c['weighted_score']:.2f} (Rel={c['reliability']}, Spd={c['speed']}, Saf={c['safety']}, Sim={c['simplicity']})"
            for c in ranked
        ]

        return {
            "problem": problem_statement,
            "priority_mode": mode,
            "candidates": validated_candidates,
            "weighted_scores": weighted_scores,
            "reliability_scores": reliability_scores,
            "speed_scores": speed_scores,
            "safety_scores": safety_scores,
            "simplicity_scores": simplicity_scores,
            "pros": pros_dict,
            "cons": cons_dict,
            "resource_requirements": resources_dict,
            "risk_analysis": {
                "status": "SAFE_CANDIDATE_SELECTED",
                "recommended_safety": best_safe["safety"],
                "safety_threshold": self.safety_threshold,
            },
            "recommended_best_solution": best_safe,
            "full_comparison_ranking": ranked,
            "recommendation_reason": rec_reason,
            "unresolved_uncertainties": uncertainties,
            "tradeoffs": tradeoffs,
        }


def compare_and_decide_solutions(
    problem_statement: str,
    candidate_solutions: list[dict[str, Any]],
    priority_mode: str = "balanced",
) -> dict[str, Any]:
    """Top-level functional interface for Section 10 solution comparison."""
    matrix = ZyeDecisionMatrix()
    return matrix.compare_solutions(problem_statement, candidate_solutions, priority_mode)
