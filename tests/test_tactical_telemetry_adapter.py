"""
Acceptance Test Suite: Day 35 Telemetry Adapter.
Verifies conversion of in-memory sliding telemetry streams to KinematicState,
handling of missing streams without fabrication, staleness verification, and velocity estimation.
"""

import time
import unittest

from zye_realtime_tactical.kinematics.telemetry_adapter import TelemetryAdapter
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager
from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource


class TestTacticalTelemetryAdapter(unittest.TestCase):
    """Verifies seamless integration between Day 35 Ring-Buffers and Day 37 Kinematics."""

    def setUp(self):
        TelemetryBufferManager.reset_instance()
        self.mgr = TelemetryBufferManager.get_instance()
        self.adapter = TelemetryAdapter(buffer_manager=self.mgr)

    def tearDown(self):
        TelemetryBufferManager.reset_instance()

    def _append(self, stream_name: str, value: float, ts: float):
        buf = self.mgr.stream_manager.get_or_create_stream(stream_name)
        buf.append(value=value, timestamp=ts, source=TimestampSource.CALLER_PROVIDED)

    def test_01_extract_valid_state_from_streams(self):
        """Test 01: Extract spatial 2D position and velocity from telemetry streams."""
        now = time.time()
        # Ingest positions
        self._append("uav_x", 12.5, ts=now)
        self._append("uav_y", -45.0, ts=now)
        # Ingest velocities
        self._append("uav_vx", 5.0, ts=now)
        self._append("uav_vy", -2.5, ts=now)

        status, state, msg = self.adapter.build_kinematic_state_from_streams(
            entity_id="uav_alpha",
            pos_stream_names=["uav_x", "uav_y"],
            vel_stream_names=["uav_vx", "uav_vy"],
            max_staleness_seconds=5.0,
            radius=1.5,
        )

        self.assertEqual(status, "STATE_EXTRACTED")
        self.assertIsNotNone(state)
        self.assertEqual(state.entity_id, "uav_alpha")
        self.assertEqual(state.position, [12.5, -45.0])
        self.assertEqual(state.velocity, [5.0, -2.5])
        self.assertEqual(state.radius, 1.5)

    def test_02_missing_stream_yields_insufficient_data(self):
        """Test 02: Missing stream refuses to fabricate coordinates and returns INSUFFICIENT_DATA."""
        now = time.time()
        self._append("target_x", 100.0, ts=now)
        # "target_y" stream is NOT created or empty

        status, state, msg = self.adapter.build_kinematic_state_from_streams(
            entity_id="target_drone",
            pos_stream_names=["target_x", "target_y"],
        )

        self.assertEqual(status, "INSUFFICIENT_DATA")
        self.assertIsNone(state)
        self.assertIn("target_y", msg)
        self.assertIn("Cannot fabricate physical coordinates", msg)

    def test_03_stale_telemetry_detection(self):
        """Test 03: Telemetry older than staleness threshold returns STALE_TELEMETRY."""
        old_time = time.time() - 60.0  # 60 seconds ago
        self._append("stale_x", 10.0, ts=old_time)
        self._append("stale_y", 20.0, ts=old_time)

        status, state, msg = self.adapter.build_kinematic_state_from_streams(
            entity_id="stale_vehicle",
            pos_stream_names=["stale_x", "stale_y"],
            max_staleness_seconds=5.0,
        )

        self.assertEqual(status, "STALE_TELEMETRY")
        self.assertIsNone(state)
        self.assertIn("stale", msg.lower())

    def test_04_velocity_estimation_from_position_series(self):
        """Test 04: Velocity is estimated from consecutive position samples when vel streams omitted."""
        t0 = time.time() - 2.0
        t1 = t0 + 1.0  # dt = 1.0s

        # Stream pos_x: 0 -> 10 over 1 second => vx = 10 m/s
        self._append("pos_x", 0.0, ts=t0)
        self._append("pos_x", 10.0, ts=t1)

        # Stream pos_y: 20 -> 25 over 1 second => vy = 5 m/s
        self._append("pos_y", 20.0, ts=t0)
        self._append("pos_y", 25.0, ts=t1)

        status, state, msg = self.adapter.build_kinematic_state_from_streams(
            entity_id="moving_bot",
            pos_stream_names=["pos_x", "pos_y"],
            max_staleness_seconds=10.0,
        )

        self.assertEqual(status, "STATE_EXTRACTED")
        self.assertIsNotNone(state)
        self.assertAlmostEqual(state.velocity[0], 10.0, places=3)
        self.assertAlmostEqual(state.velocity[1], 5.0, places=3)

    def test_05_3d_stream_extraction(self):
        """Test 05: Extraction of 3D spatial stream coordinates [x, y, z]."""
        now = time.time()
        self._append("x3d", 1.0, ts=now)
        self._append("y3d", 2.0, ts=now)
        self._append("z3d", 3.0, ts=now)

        status, state, msg = self.adapter.build_kinematic_state_from_streams(
            entity_id="drone_3d",
            pos_stream_names=["x3d", "y3d", "z3d"],
        )

        self.assertEqual(status, "STATE_EXTRACTED")
        self.assertEqual(state.position, [1.0, 2.0, 3.0])


if __name__ == "__main__":
    unittest.main()
