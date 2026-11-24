"""
Sliding Window Extractor.
Extracts contiguous numerical arrays (values, timestamps) from RingBuffer snapshots
for vectorized NumPy computations without multiple redundant copies.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np

from zye_realtime_tactical.telemetry.ring_buffer import RingBuffer
from zye_realtime_tactical.telemetry.telemetry_models import TelemetrySample


class SlidingWindow:
    """Extracts contiguous NumPy float64 windows from ring-buffer observations."""

    @classmethod
    def extract_arrays(
        cls,
        samples: List[TelemetrySample],
        window_size: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Converts sample list into (values_array, timestamps_array) of type float64.
        If window_size is specified and smaller than len(samples), takes the latest window_size.
        """
        if not samples:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

        if window_size is not None and 0 < window_size < len(samples):
            target_samples = samples[-window_size:]
        else:
            target_samples = samples

        values = np.fromiter((s.value for s in target_samples), dtype=np.float64, count=len(target_samples))
        timestamps = np.fromiter((s.timestamp for s in target_samples), dtype=np.float64, count=len(target_samples))

        return values, timestamps
