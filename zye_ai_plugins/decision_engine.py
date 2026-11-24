"""Weighted Decision Intelligence Engine for Zye AI Council.

Evaluates and ranks candidate solutions using multi-criteria weighted scoring across 7 priority modes:
- BALANCED
- SPEED_CRITICAL
- MAXIMUM_SAFETY
- LOW_RESOURCE
- HIGH_RELIABILITY
- MAINTAINABILITY_FIRST
- USER_CUSTOM

Transparently presents criteria breakdowns, pros/cons, unresolved risks, and ranking caveats.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


PRIORITY_MODES: Dict[str, Dict[str, float]] = {
    "balanced": {
        "reliability": 0.20,
        "correctness": 0.20,
        "safety": 0.20,
        "performance": 0.15,
        "maintainability": 0.10,
        "simplicity": 0.10,
        "compatibility": 0.05,
    },
    "speed_critical": {
        "performance": 0.35,
        "reliability": 0.20,
        "correctness": 0.15,
        "safety": 0.15,
        "simplicity": 0.15,
    },
    "maximum_safety": {
        "safety": 0.40,
        "reliability": 0.25,
        "correctness": 0.20,
        "maintainability": 0.15,
    },
    "low_resource": {
        "resource_efficiency": 0.35,
        "simplicity": 0.25,
        "reliability": 0.20,
        "maintainability": 0.20,
    },
    "high_reliability": {
        "reliability": 0.35,
        "correctness": 0.25,
        "safety": 0.20,
        "fault_tolerance": 0.20,
    },
    "maintainability_first": {
        "maintainability": 0.35,
        "simplicity": 0.25,
        "correctness": 0.20,
        "reliability": 0.20,
    },
}


def get_priority_mode_weights(
    priority_mode: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Retrieve normalized weight matrix for chosen priority mode."""
    mode_key = priority_mode.lower().strip()

    if mode_key == "user_custom" and custom_weights:
        # Normalize custom weights to sum to 1.0
        total = sum(custom_weights.values())
        if total > 0:
            return {k: round(v / total, 3) for k, v in custom_weights.items()}

    base_weights = PRIORITY_MODES.get(mode_key, PRIORITY_MODES["balanced"])
    return dict(base_weights)


def calculate_weighted_scores(
    candidate_scores: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
) -> Dict[str, float]:
    """Calculate composite score (0.0 to 1.0) for each candidate solution."""
    final_scores: Dict[str, float] = {}

    for cand_id, scores_map in candidate_scores.items():
        total_score = 0.0
        applied_weight = 0.0

        for criterion, weight in weights.items():
            if criterion in scores_map:
                val = max(0.0, min(1.0, float(scores_map[criterion])))
                total_score += val * weight
                applied_weight += weight

        if applied_weight > 0:
            normalized_score = total_score / applied_weight
            final_scores[cand_id] = round(normalized_score, 3)
        else:
            final_scores[cand_id] = 0.0

    return final_scores


def rank_candidate_solutions(
    candidate_solutions: Dict[str, Dict[str, Any]],
    priority_mode: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Perform multi-criteria decision analysis and rank solutions."""
    weights = get_priority_mode_weights(priority_mode, custom_weights)

    # Extract raw criterion scores
    scores_input: Dict[str, Dict[str, float]] = {}
    for cid, cdata in candidate_solutions.items():
        scores_input[cid] = cdata.get("scores", {})

    composite_scores = calculate_weighted_scores(scores_input, weights)

    # Sort descending by composite score
    ranked_ids = sorted(composite_scores.keys(), key=lambda k: composite_scores[k], reverse=True)

    ranked_list: List[Dict[str, Any]] = []
    for rank_idx, cid in enumerate(ranked_ids, start=1):
        sol_data = candidate_solutions[cid]
        score = composite_scores[cid]

        ranked_list.append({
            "rank": rank_idx,
            "solution_id": cid,
            "title": sol_data.get("title", f"Solution {cid}"),
            "provider_id": sol_data.get("provider_id", "unknown"),
            "composite_score": score,
            "criteria_scores": sol_data.get("scores", {}),
            "pros": sol_data.get("pros", []),
            "cons": sol_data.get("cons", []),
            "unresolved_risks": sol_data.get("risks", []),
        })

    best_candidate = ranked_list[0] if ranked_list else None

    return {
        "decision_id": f"dec_{uuid.uuid4().hex[:8]}",
        "priority_mode": priority_mode.upper(),
        "criteria_weights": weights,
        "total_candidates": len(ranked_list),
        "ranked_solutions": ranked_list,
        "recommended_solution": best_candidate["solution_id"] if best_candidate else None,
        "top_score": best_candidate["composite_score"] if best_candidate else 0.0,
        "score_separation": round((ranked_list[0]["composite_score"] - ranked_list[1]["composite_score"]), 3) if len(ranked_list) >= 2 else 1.0,
        "is_provisional": len(ranked_list) < 2 or (len(ranked_list) >= 2 and (ranked_list[0]["composite_score"] - ranked_list[1]["composite_score"]) < 0.05),
    }
