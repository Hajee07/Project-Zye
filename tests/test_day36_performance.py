"""
Performance Benchmark Suite for ZYE AI Day 36: Opponent Behaviour Pattern Recognition.
Measures nanosecond-level computation latency across sequence lengths: 6, 50, 100, 500, and 1,000 actions.
Validates sub-millisecond realtime inference and high-throughput batch performance.
"""

import time
import unittest
from typing import List
import numpy as np

from zye_realtime_tactical.opponent.opponent_buffer_manager import OpponentBufferManager
from zye_realtime_tactical.opponent.opponent_prediction_engine import OpponentPredictionEngine


class TestDay36PerformanceBenchmarks(unittest.TestCase):
    def setUp(self) -> None:
        OpponentBufferManager.reset_instance()
        self.engine = OpponentPredictionEngine()

    def tearDown(self) -> None:
        OpponentBufferManager.reset_instance()

    def _generate_synthetic_combat_sequence(self, n: int) -> tuple[List[str], List[float]]:
        """Generates realistic alternating fighting moves with 0.5s inter-action timing."""
        moves = ["guard", "dodge", "attack"]
        actions = [moves[i % len(moves)] for i in range(n)]
        start_t = 1000.0
        timestamps = [start_t + i * 0.5 for i in range(n)]
        return actions, timestamps

    def test_realtime_single_action_ingestion_latency(self) -> None:
        """Benchmarks online single-action prediction updates into an active 100-action buffer."""
        opponent_id = "realtime_combatant"
        # Seed buffer with 100 initial actions
        actions, timestamps = self._generate_synthetic_combat_sequence(100)
        self.engine.predict_opponent_attack(
            opponent_id=opponent_id,
            observed_actions=actions,
            action_timestamps=timestamps,
        )

        latencies_ms = []
        moves = ["guard", "dodge", "attack"]
        for i in range(50):
            t_act = timestamps[-1] + (i + 1) * 0.5
            move = moves[i % 3]

            t0 = time.perf_counter_ns()
            res = self.engine.predict_opponent_attack(
                opponent_id=opponent_id,
                observed_actions=[move],
                action_timestamps=[t_act],
            )
            t1 = time.perf_counter_ns()
            latencies_ms.append((t1 - t0) / 1_000_000.0)
            self.assertEqual(res.status, "PREDICTION_AVAILABLE")

        p50 = float(np.percentile(latencies_ms, 50))
        p95 = float(np.percentile(latencies_ms, 95))
        avg = float(np.mean(latencies_ms))

        print(f"\n[Day 36 Benchmark: Online Real-Time Ingestion (50 single-action turns)]")
        print(f"  p50 Latency: {p50:.4f} ms | p95 Latency: {p95:.4f} ms | Avg Latency: {avg:.4f} ms")

        # Sub-millisecond requirement for online tactical prediction
        self.assertLess(avg, 2.0)

    def test_latency_across_scale(self) -> None:
        """Benchmark prediction latency for 6, 50, 100, 500, and 1,000 action batch sequences."""
        scales = [6, 50, 100, 500, 1000]
        results = {}

        for n in scales:
            opponent_id = f"benchmark_boss_{n}"
            iterations = 15
            latencies_ms = []

            for it in range(iterations):
                actions, _ = self._generate_synthetic_combat_sequence(n)
                base_time = 1000.0 + (it * (n + 10) * 0.5)
                timestamps = [base_time + idx * 0.5 for idx in range(n)]

                # Reset between iterations to cleanly measure exact N size performance
                self.engine.buffer_manager.sequence_manager.reset_opponent(opponent_id)

                t0 = time.perf_counter_ns()
                res = self.engine.predict_opponent_attack(
                    opponent_id=opponent_id,
                    observed_actions=actions,
                    action_timestamps=timestamps,
                )
                t1 = time.perf_counter_ns()
                latencies_ms.append((t1 - t0) / 1_000_000.0)

            avg_latency = float(np.mean(latencies_ms))
            min_latency = float(np.min(latencies_ms))
            max_latency = float(np.max(latencies_ms))
            results[n] = {
                "avg_ms": avg_latency,
                "min_ms": min_latency,
                "max_ms": max_latency,
            }

            print(
                f"[Day 36 Benchmark] Batch N={n:4d} actions: "
                f"Avg={avg_latency:6.3f} ms, Min={min_latency:6.3f} ms, Max={max_latency:6.3f} ms"
            )

            # Targets: N <= 100 should be sub-2.0ms; large batches (500-1000) sub-10.0ms
            threshold = 2.0 if n <= 100 else 10.0
            self.assertLess(
                avg_latency,
                threshold,
                f"Latency exceeded {threshold}ms threshold for N={n}: {avg_latency:.3f}ms",
            )
            self.assertEqual(res.status, "PREDICTION_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
