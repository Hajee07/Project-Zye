"""
Acceptance Test Suite: Trajectory Prediction and Time-Series Analyzer.
Verifies discrete trajectory projections, checkpoint intervals, collision windows, and near-miss corridors.
"""

import unittest
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import KinematicState, SafetyEnvelope
from zye_realtime_tactical.kinematics.trajectory_predictor import TrajectoryPredictor


class TestTrajectoryPrediction(unittest.TestCase):
    """Verifies forward trajectory simulation across discrete time steps."""

    def test_01_linear_discrete_trajectory(self):
        """Test 01: Host and Target linear trajectories approaching each other."""
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

        res = TrajectoryPredictor.predict_trajectories(
            entity_a=host,
            entity_b=target,
            horizon_seconds=10.0,
            time_step_seconds=0.1,
            dimension=2,
        )

        self.assertEqual(res["entity_a_id"], "host")
        self.assertEqual(res["entity_b_id"], "target")
        self.assertEqual(res["step_count"], 101)  # 0.0 to 10.0 by 0.1
        self.assertAlmostEqual(res["initial_separation_m"], 100.0, places=3)
        self.assertAlmostEqual(res["min_separation_m"], 0.0, places=3)
        self.assertAlmostEqual(res["time_at_min_separation_sec"], 5.0, places=1)
        self.assertTrue(res["collision_detected"])
        self.assertIsNotNone(res["collision_window"])
        self.assertAlmostEqual(res["collision_window"]["start_time_sec"], 4.9, delta=0.15)
        self.assertAlmostEqual(res["collision_window"]["end_time_sec"], 5.1, delta=0.15)

    def test_02_accelerated_curved_trajectory(self):
        """Test 02: Target accelerating laterally, bending its trajectory path."""
        host = KinematicState(
            entity_id="drone_alpha",
            position=[0.0, 0.0],
            velocity=[0.0, 0.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="drone_beta",
            position=[50.0, 0.0],
            velocity=[-10.0, 0.0],
            acceleration=[0.0, 4.0],  # Accelerating upwards in Y
            radius=1.0,
        )

        res = TrajectoryPredictor.predict_trajectories(
            entity_a=host,
            entity_b=target,
            horizon_seconds=5.0,
            time_step_seconds=0.05,
            dimension=2,
        )

        self.assertIn("checkpoint_separations_m", res)
        # Checkpoints exist for t_0.0s, etc.
        self.assertIn("t_0.0s", res["checkpoint_separations_m"])
        self.assertAlmostEqual(res["checkpoint_separations_m"]["t_0.0s"], 50.0, places=2)
        # At final time 5.0s, target x = 50 - 50 = 0, y = 0.5 * 4 * 25 = 50
        self.assertAlmostEqual(res["final_separation_m"], 50.0, places=1)

    def test_03_near_miss_envelope_detection(self):
        """Test 03: Near-miss corridor detected without physical collision."""
        host = KinematicState(
            entity_id="host",
            position=[0.0, 0.0],
            velocity=[10.0, 0.0],
            radius=1.0,
        )
        # Passes with CPA of 4.0 meters
        target = KinematicState(
            entity_id="target",
            position=[100.0, 4.0],
            velocity=[-10.0, 0.0],
            radius=1.0,
        )

        # Safety envelope: combined_radius = 2.0m, near_miss_radius = 6.0m
        envelope = SafetyEnvelope(combined_radius=2.0, near_miss_radius=6.0)

        res = TrajectoryPredictor.predict_trajectories(
            entity_a=host,
            entity_b=target,
            horizon_seconds=10.0,
            safety_envelope=envelope,
            dimension=2,
        )

        self.assertFalse(res["collision_detected"])
        self.assertTrue(res["near_miss_detected"])
        self.assertIsNone(res["collision_window"])
        self.assertIsNotNone(res["near_miss_window"])
        self.assertAlmostEqual(res["min_separation_m"], 4.0, places=2)

    def test_04_3d_trajectory_prediction(self):
        """Test 04: 3D discrete trajectory prediction."""
        host = KinematicState(
            entity_id="h3d",
            position=[0.0, 0.0, 10.0],
            velocity=[0.0, 0.0, 2.0],
            radius=1.0,
        )
        target = KinematicState(
            entity_id="t3d",
            position=[0.0, 0.0, 30.0],
            velocity=[0.0, 0.0, -2.0],
            radius=1.0,
        )

        res = TrajectoryPredictor.predict_trajectories(
            entity_a=host,
            entity_b=target,
            horizon_seconds=10.0,
            dimension=3,
        )

        self.assertEqual(res["dimension"], 3)
        self.assertTrue(res["collision_detected"])
        self.assertAlmostEqual(res["time_at_min_separation_sec"], 5.0, places=1)
        self.assertAlmostEqual(res["min_separation_m"], 0.0, places=2)

    def test_05_invalid_parameters(self):
        """Test 05: Invalid horizon or dimension triggers errors."""
        s1 = KinematicState(entity_id="s1", position=[0.0, 0.0], velocity=[1.0, 0.0])
        s2 = KinematicState(entity_id="s2", position=[10.0, 0.0], velocity=[-1.0, 0.0])

        with self.assertRaises(ValueError):
            TrajectoryPredictor.predict_trajectories(s1, s2, horizon_seconds=-5.0)

        with self.assertRaises(ValueError):
            TrajectoryPredictor.predict_trajectories(s1, s2, dimension=4)


if __name__ == "__main__":
    unittest.main()
