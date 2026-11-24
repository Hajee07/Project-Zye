"""
Opponent Prediction Output Schemas.
Structured Pydantic models for Markov next-action probability distributions and fighting patterns.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PatternType(str, Enum):
    BIGRAM = "BIGRAM"
    TRIGRAM = "TRIGRAM"


class FightingPattern(BaseModel):
    """Represents a recurring multi-action tactical combination."""
    pattern_type: PatternType = Field(..., description="BIGRAM (2 actions) or TRIGRAM (3 actions)")
    sequence: str = Field(..., description="Action sequence representation (e.g. 'guard -> dodge -> attack')")
    count: int = Field(..., description="Observed recurrence count (minimum 2)")


class NextActionProbability(BaseModel):
    """Empirical probability for a candidate next action conditional on current context."""
    predicted_action: str = Field(..., description="Candidate action label")
    probability_pct: float = Field(..., description="Empirical percentage (0.0 to 100.0) based on sample hits")
    sample_hits: int = Field(..., description="Actual observed transition count following this context")


class OpponentPredictionResult(BaseModel):
    """Complete structured output for predict_opponent_attack."""
    status: str = Field(
        ...,
        description="PREDICTION_AVAILABLE, INSUFFICIENT_DATA, NO_REPEAT_TRANSITION_FOUND, or ERROR",
    )
    opponent_id: str = Field(..., description="Tracked opponent identifier")
    total_observed_actions: int = Field(..., description="Total action events retained in sequence buffer")
    detected_fighting_patterns: List[FightingPattern] = Field(
        default_factory=list, description="Top recurring bigrams and trigrams ranked by frequency"
    )
    current_state: Optional[str] = Field(
        default=None, description="Current action state or context (e.g. 'dodge -> attack')"
    )
    prediction_basis: Optional[str] = Field(
        default=None,
        description="2nd-Order Sequence Context, 1st-Order Transition Context, or NO_REPEAT_TRANSITION_FOUND",
    )
    context_observation_count: int = Field(
        default=0, description="Total outgoing transitions observed historically from current context"
    )
    next_attack_probabilities: List[NextActionProbability] = Field(
        default_factory=list, description="Top 3 empirical next-action candidates without artificial renormalization"
    )
    expected_next_attack_in_sec: Optional[float] = Field(
        default=None, description="Average inter-action timing interval estimate in seconds"
    )
    timing_basis: Optional[str] = Field(
        default=None, description="Explanation of timing calculation (e.g. AVERAGE_VALID_INTERVALS or INSUFFICIENT_VALID_INTERVALS)"
    )
    valid_interval_count: int = Field(
        default=0, description="Number of valid consecutive intervals used for timing analysis"
    )
    compute_time_ms: float = Field(default=0.0, description="Markov and pattern analysis compute latency in ms")
    error_message: Optional[str] = Field(default=None, description="Error details if status is ERROR")
