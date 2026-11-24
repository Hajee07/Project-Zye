"""
Acceptance Test Suite: Vectorized Monte Carlo Simulation Engine.
Tests 11-18 covering stochastic convergence, random seed reproducibility, Wilson score confidence intervals,
zero observed events, correlated covariance sampling, large sample stability, and invalid distributions.
"""

import math
import unittest
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import (
    DistributionType,
    KinematicState,
    SafetyEnvelope,
    UncertaintyConfig,
)
from zye_realtime_tactical.kinematics.monte_carlo_engine import MonteCarloSimulationEngine
from zye_realtime_tactical.kinematics.statistical_analyzer import StatisticalAnalyzer
from zye_realtime_tactical.kinematics.uncertainty_distribution import (
    CovarianceValidationError,
    UncertaintyDistributionSampler,
)


class TestMonteCarloSimulation(unittest.TestCase):
    """Rigorous verification of the Monte Carlo simulation engine and statistical layers."""

    def test_11_zero_uncertainty_convergence(self):
        """Test 11: With zero uncertainty (sigma=0), Monte Carlo converges exactly to deterministic CPA."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[100.0, 20.0],
            velocity=[-10.0, 0.0],
            radius=1.0,
        )

        unc = UncertaintyConfig(
            pos_std=[0.0, 0.0],
            vel_std=[0.0, 0.0],
        )

        res = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=1000,
            horizon_seconds=10.0,
            uncertainty_a=unc,
            uncertainty_b=unc,
            random_seed=42,
            dimension=2,
        )

        # All 1000 trials must have identical CPA of exactly 20.0m
        self.assertAlmostEqual(res.cpa_distance_distribution["p50"], 20.0, places=4)
        self.assertAlmostEqual(res.cpa_distance_distribution["p05"], 20.0, places=4)
        self.assertAlmostEqual(res.cpa_distance_distribution["p95"], 20.0, places=4)
        self.assertEqual(res.empirical_collision_probability, 0.0)

    def test_12_increasing_uncertainty_spreads_distribution(self):
        """Test 12: Higher velocity variance broadens the distribution of CPA distances."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[100.0, 0.0],
            velocity=[-10.0, 0.0],
            radius=1.0,
        )

        # Low uncertainty
        low_unc = UncertaintyConfig(pos_std=[0.1, 0.1], vel_std=[0.1, 0.1])
        res_low = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=2000,
            uncertainty_b=low_unc,
            random_seed=123,
        )

        # High uncertainty
        high_unc = UncertaintyConfig(pos_std=[5.0, 5.0], vel_std=[3.0, 3.0])
        res_high = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=2000,
            uncertainty_b=high_unc,
            random_seed=123,
        )

        spread_low = res_low.cpa_distance_distribution["p95"] - res_low.cpa_distance_distribution["p05"]
        spread_high = res_high.cpa_distance_distribution["p95"] - res_high.cpa_distance_distribution["p05"]
        self.assertGreater(spread_high, spread_low)

    def test_13_fixed_random_seed_reproducibility(self):
        """Test 13: Identical random seeds produce bit-exact simulation metrics."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[80.0, 5.0],
            velocity=[-8.0, 0.0],
            radius=1.0,
        )
        unc = UncertaintyConfig(pos_std=[1.0, 1.0], vel_std=[0.5, 0.5])

        run1 = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=3000,
            uncertainty_b=unc,
            random_seed=999,
        )
        run2 = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=3000,
            uncertainty_b=unc,
            random_seed=999,
        )

        self.assertEqual(run1.empirical_collision_probability, run2.empirical_collision_probability)
        self.assertEqual(run1.collision_count, run2.collision_count)
        self.assertEqual(run1.cpa_distance_distribution["p50"], run2.cpa_distance_distribution["p50"])
        self.assertEqual(run1.confidence_interval.lower, run2.confidence_interval.lower)
        self.assertEqual(run1.confidence_interval.upper, run2.confidence_interval.upper)

    def test_14_wilson_score_interval(self):
        """Test 14: Wilson score interval stays strictly within [0, 1] and reflects confidence."""
        # 100 collisions out of 1000
        ci = StatisticalAnalyzer.calculate_wilson_score_interval(success_count=100, sample_count=1000, confidence_level=0.95)
        self.assertGreaterEqual(ci.lower, 0.0)
        self.assertLessEqual(ci.upper, 1.0)
        self.assertLess(ci.lower, 0.10)
        self.assertGreater(ci.upper, 0.10)
        # Expected around [0.0826, 0.1205]
        self.assertAlmostEqual(ci.lower, 0.0826, delta=0.005)
        self.assertAlmostEqual(ci.upper, 0.1205, delta=0.005)

    def test_15_zero_observed_events(self):
        """Test 15: k=0 collisions produces Wilson upper bound > 0 (reflects resolution limit)."""
        ci = StatisticalAnalyzer.calculate_wilson_score_interval(success_count=0, sample_count=20000, confidence_level=0.95)
        self.assertEqual(ci.lower, 0.0)
        # For n=20000, k=0, upper bound is approx 3.8416 / (20000 + 3.8416) ~ 0.000192
        self.assertGreater(ci.upper, 0.0)
        self.assertLess(ci.upper, 0.0003)
        self.assertAlmostEqual(ci.upper, 0.000192, delta=0.00005)

    def test_16_correlated_variables_covariance(self):
        """Test 16: Multi-variate sampling with positive semi-definite covariance matrix."""
        cov = np.array([
            [2.0, 0.5],
            [0.5, 1.0],
        ], dtype=np.float64)

        base = np.array([10.0, 5.0], dtype=np.float64)
        samples = UncertaintyDistributionSampler.sample_perturbations(
            base_vector=base,
            std_vector=None,
            cov_matrix=cov,
            sample_count=10000,
            rng=np.random.default_rng(42),
        )

        self.assertEqual(samples.shape, (10000, 2))
        empirical_cov = np.cov(samples, rowvar=False)
        self.assertAlmostEqual(empirical_cov[0, 0], 2.0, delta=0.15)
        self.assertAlmostEqual(empirical_cov[1, 1], 1.0, delta=0.1)
        self.assertAlmostEqual(empirical_cov[0, 1], 0.5, delta=0.1)

    def test_17_large_sample_count_20k(self):
        """Test 17: Large sample count (20,000 scenarios) runs stably without numerical overflow."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.5,
        )
        target = KinematicState(
            entity_id="target",
            position=[60.0, 2.0],
            velocity=[-10.0, 0.0],
            radius=1.5,
        )
        unc = UncertaintyConfig(position_std=[1.0, 1.0], velocity_std=[0.5, 0.5])

        res = MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=20000,
            horizon_seconds=5.0,
            uncertainty_b=unc,
            random_seed=42,
        )

        self.assertEqual(res.sample_count, 20000)
        self.assertGreater(res.empirical_collision_probability, 0.0)
        self.assertLess(res.empirical_collision_probability, 1.0)
        self.assertGreater(res.execution_time_ms, 0.0)
        self.assertIn("p50", res.cpa_distance_distribution)

    def test_18_invalid_distribution_error(self):
        """Test 18: Non-positive semi-definite or asymmetrical covariance matrix triggers error."""
        # Non-symmetric matrix
        bad_cov_asym = np.array([
            [1.0, 2.0],
            [0.0, 1.0],
        ], dtype=np.float64)

        with self.assertRaises(CovarianceValidationError):
            UncertaintyDistributionSampler.validate_covariance_matrix(bad_cov_asym, expected_dim=2)

        # Negative eigenvalue matrix (not positive semi-definite)
        bad_cov_neg = np.array([
            [1.0, 3.0],
            [3.0, 1.0],  # Det = 1 - 9 = -8 < 0
        ], dtype=np.float64)

        with self.assertRaises(CovarianceValidationError):
            UncertaintyDistributionSampler.validate_covariance_matrix(bad_cov_neg, expected_dim=2)


if __name__ == "__main__":
    unittest.main()
