"""
Opponent Prediction Engine Master Facade (Day 36).
Orchestrates sequence ingestion, evidence validation, First/Second-Order Markov calculations,
tactical pattern recognition (bigrams & trigrams), and inter-action timing analysis.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from zye_realtime_tactical.opponent.bigram_pattern_detector import BigramPatternDetector
from zye_realtime_tactical.opponent.first_order_markov import FirstOrderMarkov
from zye_realtime_tactical.opponent.inter_action_timing import InterActionTimingAnalyzer
from zye_realtime_tactical.opponent.markov_context_selector import MarkovContextSelector
from zye_realtime_tactical.opponent.next_action_predictor import NextActionPredictor
from zye_realtime_tactical.opponent.opponent_action_models import OpponentAction
from zye_realtime_tactical.opponent.opponent_action_validator import OpponentActionValidator
from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager
from zye_realtime_tactical.opponent.opponent_prediction_schema import (
    FightingPattern,
    OpponentPredictionResult,
)
from zye_realtime_tactical.opponent.opponent_state_analyzer import OpponentStateAnalyzer
from zye_realtime_tactical.opponent.opponent_timestamp_manager import OpponentTimestampManager
from zye_realtime_tactical.opponent.pattern_ranking_engine import PatternRankingEngine
from zye_realtime_tactical.opponent.prediction_evidence_guard import PredictionEvidenceGuard
from zye_realtime_tactical.opponent.second_order_markov import SecondOrderMarkov
from zye_realtime_tactical.opponent.trigram_pattern_detector import TrigramPatternDetector

logger = logging.getLogger("zye.realtime_tactical.opponent.engine")


class OpponentPredictionEngine:
    """Master facade for opponent behaviour pattern recognition and Markov prediction."""

    def __init__(self, buffer_manager: Optional[OpponentBufferManager] = None) -> None:
        self.buffer_manager = buffer_manager or OpponentBufferManager.get_instance()

    def predict_opponent_attack(
        self,
        opponent_id: str,
        observed_actions: Optional[List[str]] = None,
        action_timestamps: Optional[List[float]] = None,
    ) -> OpponentPredictionResult:
        """
        Ingests actions and executes zero-fabrication Markov prediction and pattern detection.
        1. Atomic validation of opponent ID and action list.
        2. Ingestion into bounded circular deque.
        3. Strict 6-action evidence check (returns INSUFFICIENT_DATA if < 6).
        4. Context selection: 2nd-order preferred (>= 2 observed transitions), fallback to 1st-order.
        5. Top 3 empirical next-action probabilities without artificial renormalization.
        6. Top 4 bigram/trigram fighting pattern ranking.
        7. Inter-action timing analysis via NumPy diff.
        """
        start_ns = time.perf_counter_ns()

        try:
            validated_id = OpponentActionValidator.validate_opponent_id(opponent_id)
        except Exception as exc:
            return OpponentPredictionResult(
                status="ERROR",
                opponent_id=opponent_id.strip() if opponent_id else "unknown",
                total_observed_actions=0,
                error_message=f"Opponent ID validation error: {exc}",
                compute_time_ms=0.0,
            )

        buf = self.buffer_manager.sequence_manager.get_or_create_buffer(validated_id)

        # Ingest new observations if provided
        if observed_actions:
            try:
                clean_actions = OpponentActionValidator.validate_actions(observed_actions)
                last_ts = buf.last_action_timestamp
                clean_timestamps = OpponentTimestampManager.validate_timestamps(
                    raw_timestamps=action_timestamps,
                    expected_count=len(clean_actions),
                    last_known_timestamp=last_ts,
                )

                action_objs = [
                    OpponentAction(action=act, timestamp=ts)
                    for act, ts in zip(clean_actions, clean_timestamps)
                ]
                buf.append_batch(action_objs)
            except Exception as exc:
                elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000.0, 4)
                return OpponentPredictionResult(
                    status="ERROR",
                    opponent_id=validated_id,
                    total_observed_actions=buf.size,
                    error_message=f"Action ingestion failure: {exc}",
                    compute_time_ms=elapsed_ms,
                )

        total_actions = buf.size

        # Guard: Minimum 6 actions required for prediction
        if not PredictionEvidenceGuard.check_sufficient_evidence(total_actions):
            elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000.0, 4)
            self.buffer_manager.record_prediction(elapsed_ms)
            return OpponentPredictionResult(
                status="INSUFFICIENT_DATA",
                opponent_id=validated_id,
                total_observed_actions=total_actions,
                compute_time_ms=elapsed_ms,
            )

        # Retrieve all actions and timestamps in sequence
        actions = buf.get_all_actions()
        timestamps = buf.get_all_timestamps()

        # Extract current state context
        current_state_tuple = OpponentStateAnalyzer.get_current_state(actions)
        state_str = OpponentStateAnalyzer.format_state_string(current_state_tuple)

        # Build Markov transition matrices
        first_matrix = FirstOrderMarkov.build_transition_matrix(actions)
        second_matrix = SecondOrderMarkov.build_transition_matrix(actions)

        # Select context (2nd-order preferred with >= 2 transitions, fallback to 1st-order)
        context_result = MarkovContextSelector.select_context(
            current_state=current_state_tuple,
            first_order_matrix=first_matrix,
            second_order_matrix=second_matrix,
        )

        status_code = context_result["status"]
        prediction_basis = context_result["basis"]
        transitions = context_result["transitions"]
        context_count = context_result["context_total"]

        next_probs = []
        if status_code == "PREDICTION_AVAILABLE" and transitions:
            next_probs = NextActionPredictor.predict_next_actions(
                transitions=transitions,
                context_observation_count=context_count,
                top_k=3,
            )

        # Detect fighting patterns (bigrams and trigrams)
        bigrams = BigramPatternDetector.detect(actions)
        trigrams = TrigramPatternDetector.detect(actions)
        ranked_patterns: List[FightingPattern] = PatternRankingEngine.rank(bigrams, trigrams, top_n=4)

        # Analyze inter-action timing
        timing_stats = InterActionTimingAnalyzer.analyze(timestamps)

        elapsed_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000.0, 4)
        self.buffer_manager.record_prediction(elapsed_ms)

        return OpponentPredictionResult(
            status=status_code,
            opponent_id=validated_id,
            total_observed_actions=total_actions,
            detected_fighting_patterns=ranked_patterns,
            current_state=state_str,
            prediction_basis=prediction_basis,
            context_observation_count=context_count,
            next_attack_probabilities=next_probs,
            expected_next_attack_in_sec=timing_stats.get("expected_next_attack_in_sec"),
            timing_basis=timing_stats.get("timing_basis"),
            valid_interval_count=timing_stats.get("valid_interval_count", 0),
            compute_time_ms=elapsed_ms,
        )
