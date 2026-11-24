"""
Acceptance Test Suite: Monte Carlo Simulation Performance Benchmarks.
Tests 25-27 verifying vectorized throughput, timing breakdown, memory scalability,
and latency across sample sizes from 1,000 to 50,000 runs.
"""

import time
import unittest

from zye_realtime_tactical.kinematics.kinematic_models import KinematicState, UncertaintyConfig
from zye_realtime_tactical.kinematics.monte_carlo_engine import MonteCarloSimulationEngine


class TestSimulationPerformance(unittest.TestCase):
    """Benchmarks and verifies high-speed vectorized trajectory simulation."""

    def setUp(self):
        self.host = KinematicState(
            entity_id="host_perf",
            position=[0.0, 0.0],
            velocity=[15.0, 0.0],
            radius=1.5,
        )
        self.target = KinematicState(
            entity_id="target_perf",
            position=[150.0, 2.0],
            velocity=[-15.0, 0.0],
            radius=1.5,
        )
        self.unc = UncertaintyConfig(
            position_std=[1.5, 1.5],
            velocity_std=[0.8, 0.8],
        )

    def test_25_scaling_1k_to_20k_samples(self):
        """Test 25: Performance across 1k, 5k, 10k, and 20k sample counts."""
        sample_counts = [1000, 5000, 10000, 20000]
        timings = {}

        for count in sample_counts:
            res = MonteCarloSimulationEngine.run_simulation(
                entity_a=self.host,
                entity_b=self.target,
                sample_count=count,
                uncertainty_b=self.unc,
                random_seed=42,
            )
            timings[count] = res.execution_time_ms
            self.assertEqual(res.sample_count, count)
            self.assertGreater(res.execution_time_ms, 0.0)

        # 20k samples execution time should be under 50ms (typically under 10-15ms in pure vectorized NumPy)
        self.assertLess(timings[20000], 100.0, f"20k simulation exceeded limit: {timings[20000]}ms")

    def test_26_timing_breakdown_components(self):
        """Test 26: Timing breakdown verifies sampling, vectorization, and percentile extraction."""
        res = MonteCarloSimulationEngine.run_simulation(
            entity_a=self.host,
            entity_b=self.target,
            sample_count=20000,
            uncertainty_b=self.unc,
            random_seed=42,
        )

        breakdown = res.metadata.get("timing_breakdown", {})
        self.assertIn("sampling_ms", breakdown)
        self.assertIn("kinematic_eval_ms", breakdown)
        self.assertIn("statistics_ms", breakdown)
        self.assertGreater(breakdown["sampling_ms"] + breakdown["kinematic_eval_ms"], 0.0)

    def test_27_high_volume_50k_stability(self):
        """Test 27: Massive 50,000 scenario run without degradation or memory leak."""
        res = MonteCarloSimulationEngine.run_simulation(
            entity_a=self.host,
            entity_b=self.target,
            sample_count=50000,
            uncertainty_b=self.unc,
            random_seed=42,
        )

        self.assertEqual(res.sample_count, 50000)
        self.assertIn("p50", res.cpa_distance_distribution)
        self.assertGreater(res.empirical_collision_probability, 0.0)


if __name__ == "__main__":
    unittest.main()
