"""
Acceptance Test Suite: Deterministic Kinematic Mathematics Engine.
Tests 01-10 covering 2D/3D relative kinematics, CPA, TCPA, TTC, safety envelopes, and accelerated trajectories.
"""

import math
import unittest
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import (
    CoordinateDimension,
    KinematicRiskResult,
    KinematicState,
    RiskCategory,
    SafetyEnvelope,
)
from zye_realtime_tactical.kinematics.kinematic_engine import KinematicEngine
from zye_realtime_tactical.kinematics.unit_converter import UnitConverter, UnitConversionError


class TestKinematicRiskEngine(unittest.TestCase):
    """Rigorous verification of deterministic kinematic collision risk algorithms."""

    def test_01_stationary_target_moving_away(self):
        """Test 01: Stationary target with host moving away (relative distance increasing)."""
        host = KinematicState(
            entity_id="host",
            position=[-10.0, 0.0],
            velocity=[-5.0, 0.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[50.0, 0.0],
            velocity=[0.0, 0.0],
            radius=1.0,
        )

        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertFalse(res.is_approaching)
        self.assertLess(res.closing_speed_mps, 0.0)
        self.assertFalse(res.collision_detected)
        self.assertEqual(res.time_to_collision_sec, float("inf"))
        self.assertEqual(res.time_to_cpa_sec, 0.0)
        self.assertAlmostEqual(res.closest_approach_distance_m, 60.0, places=4)
        self.assertEqual(res.risk_category, RiskCategory.MINIMAL)

    def test_02_moving_away_target(self):
        """Test 02: Both moving in same direction, target is moving faster away."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.5,
        )
        target = KinematicState(
            entity_id="target",
            position=[50.0, 0.0],
            velocity=[25.0, 0.0],
            radius=1.5,
        )

        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertFalse(res.is_approaching)
        self.assertFalse(res.collision_detected)
        self.assertEqual(res.time_to_collision_sec, float("inf"))
        self.assertAlmostEqual(res.closest_approach_distance_m, 50.0, places=4)

    def test_03_direct_head_on_approach(self):
        """Test 03: Direct head-on collision trajectory."""
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

        # Relative speed = 20 m/s. Initial distance = 100 m. Combined radius = 2.0 m.
        # Collision occurs when distance <= 2.0 m, which is (100 - 2) / 20 = 4.9 seconds.
        # CPA occurs at distance = 0 m at t = 5.0 seconds.
        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertTrue(res.is_approaching)
        self.assertAlmostEqual(res.closing_speed_mps, 20.0, places=4)
        self.assertTrue(res.collision_detected)
        self.assertAlmostEqual(res.time_to_cpa_sec, 5.0, places=4)
        self.assertAlmostEqual(res.closest_approach_distance_m, 0.0, places=4)
        self.assertAlmostEqual(res.time_to_collision_sec, 4.9, places=4)
        self.assertIn(res.risk_category, [RiskCategory.HIGH, RiskCategory.CRITICAL])

    def test_04_parallel_offset_paths(self):
        """Test 04: Parallel tracks with lateral offset of 20m."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=2.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[100.0, 20.0],
            velocity=[-10.0, 0.0],
            radius=2.0,
        )

        # At t = 5s, host is at (50, 0), target is at (0, 20). Lateral distance is 20m.
        # Combined radius is 4.0m. Since CPA = 20.0m > 4.0m, no collision.
        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertTrue(res.is_approaching)
        self.assertFalse(res.collision_detected)
        self.assertAlmostEqual(res.time_to_cpa_sec, 5.0, places=4)
        self.assertAlmostEqual(res.closest_approach_distance_m, 20.0, places=4)
        self.assertEqual(res.time_to_collision_sec, float("inf"))

    def test_05_perpendicular_crossing_trajectories(self):
        """Test 05: Perpendicular 90-degree crossing trajectories."""
        # Host moving along Y axis: (0, -50) with velocity (0, 10)
        # Target moving along X axis: (50, 0) with velocity (-10, 0)
        host = KinematicState(
            entity_id="host",
            position=[0.0, -50.0],
            velocity=[0.0, 10.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[50.0, 0.0],
            velocity=[-10.0, 0.0],
            radius=1.0,
        )

        # Both reach (0, 0) at t = 5.0s.
        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertTrue(res.is_approaching)
        self.assertTrue(res.collision_detected)
        self.assertAlmostEqual(res.time_to_cpa_sec, 5.0, places=3)
        self.assertAlmostEqual(res.closest_approach_distance_m, 0.0, places=3)
        self.assertAlmostEqual(res.time_to_collision_sec, 5.0 - (2.0 / math.sqrt(200)), places=2)

    def test_06_initial_overlap(self):
        """Test 06: Initial positions overlap within the combined safety envelope."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[1.0, 0.0],
            radius=3.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[1.5, 0.0],
            velocity=[-1.0, 0.0],
            radius=3.0,
        )

        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertTrue(res.collision_detected)
        self.assertEqual(res.time_to_collision_sec, 0.0)
        self.assertEqual(res.risk_category, RiskCategory.CRITICAL)

    def test_07_constant_relative_acceleration(self):
        """Test 07: Relative acceleration alters CPA timing and closing behavior."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[0.0, 0.0],
            acceleration=[0.0, 0.0],
            radius=1.0,
        )
        # Target starts 100m away, moving towards host at 10 m/s and accelerating at 2 m/s^2 towards host
        target = KinematicState(
            entity_id="target",
            position=[100.0, 0.0],
            velocity=[-10.0, 0.0],
            acceleration=[-2.0, 0.0],
            radius=1.0,
        )

        # Distance formula: d(t) = 100 - 10*t - 0.5 * 2 * t^2 = 100 - 10*t - t^2.
        # d(t) = 2.0 (envelope) => t^2 + 10t - 98 = 0.
        # t = (-10 + sqrt(100 + 392)) / 2 = (-10 + sqrt(492)) / 2 = (-10 + 22.181) / 2 = 6.09s.
        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertTrue(res.collision_detected)
        self.assertIn("CONSTANT_ACCELERATION_MODEL", res.assumptions)
        self.assertAlmostEqual(res.time_to_collision_sec, 6.0905, places=2)

    def test_08_3d_kinematic_motion(self):
        """Test 08: 3-dimensional trajectory vectors [x, y, z]."""
        host = KinematicState(
            entity_id="host_drone",
            position=[0.0, 0.0, 10.0],
            velocity=[5.0, 5.0, 0.0],
            radius=0.5,
        )
        target = KinematicState(
            entity_id="intruder_drone",
            position=[50.0, 50.0, 10.0],
            velocity=[-5.0, -5.0, 0.0],
            radius=0.5,
        )

        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=3)
        self.assertTrue(res.is_approaching)
        self.assertTrue(res.collision_detected)
        self.assertAlmostEqual(res.closest_approach_distance_m, 0.0, places=4)
        self.assertIn("COORDINATE_DIMENSION_3D", res.assumptions)

    def test_09_missing_acceleration_fallback(self):
        """Test 09: Graceful fallback to constant-velocity model when acceleration is None."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            acceleration=None,
            radius=1.0,
        )
        target = KinematicState(
            entity_id="target",
            position=[100.0, 0.0],
            velocity=[-10.0, 0.0],
            acceleration=None,
            radius=1.0,
        )

        res = KinematicEngine.calculate_risk(host, target, horizon_seconds=10.0, dimension=2)
        self.assertIn("CONSTANT_VELOCITY_MODEL", res.assumptions)
        self.assertTrue(any("fallback to constant-velocity" in w for w in res.warnings))
        self.assertAlmostEqual(res.time_to_cpa_sec, 5.0, places=4)

    def test_10_invalid_units_and_validation(self):
        """Test 10: Validation of units and error handling."""
        # Speed conversions
        self.assertAlmostEqual(UnitConverter.to_mps(36.0, "km/h"), 10.0, places=4)
        self.assertAlmostEqual(UnitConverter.from_mps(10.0, "km/h"), 36.0, places=4)

        # Distance conversions
        self.assertAlmostEqual(UnitConverter.to_meters(1.0, "km"), 1000.0, places=4)
        self.assertAlmostEqual(UnitConverter.to_meters(10.0, "ft"), 3.048, places=4)

        # Invalid unit raises UnitConversionError
        with self.assertRaises(UnitConversionError):
            UnitConverter.to_mps(100.0, "parsecs_per_century")

        # Invalid dimension raises ValueError
        invalid_dim_state = KinematicState(
            entity_id="bad",
            position=[1.0],  # Only 1D
            velocity=[1.0, 2.0],
        )
        valid_state = KinematicState(
            entity_id="ok",
            position=[1.0, 2.0],
            velocity=[1.0, 2.0],
        )
        with self.assertRaises(ValueError):
            KinematicEngine.calculate_risk(invalid_dim_state, valid_state, dimension=2)


if __name__ == "__main__":
    unittest.main()
