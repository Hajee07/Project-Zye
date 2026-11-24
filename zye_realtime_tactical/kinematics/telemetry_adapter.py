"""
Day 35 Telemetry Adapter (Day 37 / Phase 3).
Converts streaming in-memory telemetry samples from Day 35 ring buffers into validated
KinematicState representations without modifying source telemetry structures.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.kinematics.kinematic_models import KinematicState
from zye_realtime_tactical.telemetry.telemetry_buffer_manager import TelemetryBufferManager


class TelemetryAdapter:
    """Safely extracts and reconstructs spatial kinematic states from Day 35 in-memory ring buffers."""

    def __init__(self, buffer_manager: Optional[TelemetryBufferManager] = None) -> None:
        self.buffer_manager = buffer_manager or TelemetryBufferManager.get_instance()

    def build_kinematic_state_from_streams(
        self,
        entity_id: str,
        pos_stream_names: List[str],
        vel_stream_names: Optional[List[str]] = None,
        accel_stream_names: Optional[List[str]] = None,
        max_staleness_seconds: float = 5.0,
        radius: float = 1.0,
    ) -> Tuple[str, Optional[KinematicState], Optional[str]]:
        """
        Extracts latest timestamped values from named telemetry streams.
        Returns:
            (status, KinematicState_or_None, explanation_or_error)
        Status values:
            - STATE_EXTRACTED: Valid state successfully constructed
            - INSUFFICIENT_DATA: Required stream does not exist or has zero samples
            - STALE_TELEMETRY: Most recent sample exceeds max_staleness_seconds
            - ERROR: Parsing or dimensional mismatch
        """
        dim = len(pos_stream_names)
        if dim not in (2, 3):
            return "ERROR", None, f"Position stream names must specify 2 or 3 axes, got {dim}"

        positions: List[float] = []
        latest_ts = 0.0
        now = time.time()

        # 1. Extract Position Streams
        for stream_name in pos_stream_names:
            buf = self.buffer_manager.stream_manager.get_stream(stream_name)
            if buf is None or len(buf) == 0:
                return (
                    "INSUFFICIENT_DATA",
                    None,
                    f"Position stream '{stream_name}' has no buffered samples. Cannot fabricate physical coordinates.",
                )

            samples_latest = buf.get_latest_n(1)
            if not samples_latest:
                return "INSUFFICIENT_DATA", None, f"Stream '{stream_name}' returned null sample."

            sample = samples_latest[0]
            positions.append(float(sample.value))
            if sample.timestamp > latest_ts:
                latest_ts = sample.timestamp

        # Staleness check
        if latest_ts > 0 and (now - latest_ts) > max_staleness_seconds:
            # Check if timestamps are relative/monotonic or epoch
            if latest_ts > 1000000 and (now - latest_ts) > max_staleness_seconds:
                return (
                    "STALE_TELEMETRY",
                    None,
                    f"Telemetry sample is stale (last sample age = {now - latest_ts:.2f}s > threshold {max_staleness_seconds}s)",
                )

        # 2. Extract Velocity Streams (or estimate if velocity streams omitted)
        velocities: List[float] = []
        if vel_stream_names and len(vel_stream_names) == dim:
            for v_stream in vel_stream_names:
                buf = self.buffer_manager.stream_manager.get_stream(v_stream)
                if buf is not None and len(buf) > 0:
                    s_list = buf.get_latest_n(1)
                    velocities.append(float(s_list[0].value) if s_list else 0.0)
                else:
                    velocities.append(0.0)
        else:
            # Attempt numerical velocity estimate from latest 2 position samples if available
            for stream_name in pos_stream_names:
                buf = self.buffer_manager.stream_manager.get_stream(stream_name)
                samples = buf.get_latest_n(2) if buf else []
                if len(samples) >= 2:
                    dt = samples[1].timestamp - samples[0].timestamp
                    dv = samples[1].value - samples[0].value
                    vel_est = (dv / dt) if dt > 1e-6 else 0.0
                    velocities.append(float(vel_est))
                else:
                    velocities.append(0.0)

        # 3. Extract Acceleration Streams if provided
        accelerations: Optional[List[float]] = None
        if accel_stream_names and len(accel_stream_names) == dim:
            accelerations = []
            for a_stream in accel_stream_names:
                buf = self.buffer_manager.stream_manager.get_stream(a_stream)
                if buf is not None and len(buf) > 0:
                    s_list = buf.get_latest_n(1)
                    accelerations.append(float(s_list[0].value) if s_list else 0.0)
                else:
                    accelerations.append(0.0)

        state = KinematicState(
            entity_id=entity_id,
            timestamp=latest_ts if latest_ts > 0 else now,
            position=positions,
            velocity=velocities,
            acceleration=accelerations,
            radius=radius,
        )
        return "STATE_EXTRACTED", state, "Kinematic state extracted successfully from Day 35 telemetry."
