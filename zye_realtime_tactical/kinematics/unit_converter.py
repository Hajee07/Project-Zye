"""
Unit Conversion and Coordinate Validation Engine (Day 37 / Phase 3).
Provides deterministic, zero-drift conversion of user-supplied units to standard SI units
(meters, m/s, m/s^2, seconds) and validates coordinate vector dimensional integrity.
"""

from __future__ import annotations

import math
from typing import List, Tuple, Union

# Standard SI conversion factors to base SI units (meters, seconds, m/s, m/s^2)
DISTANCE_TO_METERS: dict[str, float] = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "ft": 0.3048,
    "feet": 0.3048,
    "foot": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
    "nm": 1852.0,
    "nmi": 1852.0,
    "nautical_mile": 1852.0,
    "nautical_miles": 1852.0,
}

SPEED_TO_MPS: dict[str, float] = {
    "m/s": 1.0,
    "mps": 1.0,
    "meter/second": 1.0,
    "km/h": 1.0 / 3.6,
    "kph": 1.0 / 3.6,
    "kmh": 1.0 / 3.6,
    "mph": 0.44704,
    "mi/h": 0.44704,
    "knot": 1852.0 / 3600.0,  # ~0.514444 m/s
    "knots": 1852.0 / 3600.0,
    "kt": 1852.0 / 3600.0,
    "ft/s": 0.3048,
    "fps": 0.3048,
}

ACCELERATION_TO_MPS2: dict[str, float] = {
    "m/s^2": 1.0,
    "m/s2": 1.0,
    "mps2": 1.0,
    "g": 9.80665,
    "gees": 9.80665,
    "ft/s^2": 0.3048,
    "ft/s2": 0.3048,
}

TIME_TO_SECONDS: dict[str, float] = {
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "ms": 0.001,
    "millisecond": 0.001,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
}


class UnitConversionError(ValueError):
    """Raised when an invalid unit name or illegal numerical value is provided."""
    pass


class UnitConverter:
    """Safe conversion utility for kinematics calculations."""

    @staticmethod
    def to_meters(value: float, unit: str = "m") -> float:
        """Convert a scalar distance to meters."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Distance value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in DISTANCE_TO_METERS:
            raise UnitConversionError(f"Unsupported distance unit '{unit}'. Valid: {list(DISTANCE_TO_METERS.keys())}")
        return value * DISTANCE_TO_METERS[u]

    @staticmethod
    def from_meters(value: float, unit: str = "m") -> float:
        """Convert a scalar distance from meters to the target unit."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Distance value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in DISTANCE_TO_METERS:
            raise UnitConversionError(f"Unsupported distance unit '{unit}'. Valid: {list(DISTANCE_TO_METERS.keys())}")
        return value / DISTANCE_TO_METERS[u]

    @staticmethod
    def to_mps(value: float, unit: str = "m/s") -> float:
        """Convert a scalar speed to meters per second."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Speed value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in SPEED_TO_MPS:
            raise UnitConversionError(f"Unsupported speed unit '{unit}'. Valid: {list(SPEED_TO_MPS.keys())}")
        return value * SPEED_TO_MPS[u]

    @staticmethod
    def from_mps(value: float, unit: str = "m/s") -> float:
        """Convert a scalar speed from meters per second to the target unit."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Speed value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in SPEED_TO_MPS:
            raise UnitConversionError(f"Unsupported speed unit '{unit}'. Valid: {list(SPEED_TO_MPS.keys())}")
        return value / SPEED_TO_MPS[u]

    @staticmethod
    def to_mps2(value: float, unit: str = "m/s^2") -> float:
        """Convert a scalar acceleration to m/s^2."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Acceleration value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in ACCELERATION_TO_MPS2:
            raise UnitConversionError(f"Unsupported acceleration unit '{unit}'. Valid: {list(ACCELERATION_TO_MPS2.keys())}")
        return value * ACCELERATION_TO_MPS2[u]

    @staticmethod
    def from_mps2(value: float, unit: str = "m/s^2") -> float:
        """Convert a scalar acceleration from m/s^2 to the target unit."""
        if not math.isfinite(value):
            raise UnitConversionError(f"Acceleration value must be finite, got: {value}")
        u = unit.lower().strip()
        if u not in ACCELERATION_TO_MPS2:
            raise UnitConversionError(f"Unsupported acceleration unit '{unit}'. Valid: {list(ACCELERATION_TO_MPS2.keys())}")
        return value / ACCELERATION_TO_MPS2[u]

    @staticmethod
    def to_seconds(value: float, unit: str = "s") -> float:
        """Convert a duration to seconds."""
        if not math.isfinite(value) or value < 0:
            raise UnitConversionError(f"Duration must be non-negative and finite, got: {value}")
        u = unit.lower().strip()
        if u not in TIME_TO_SECONDS:
            raise UnitConversionError(f"Unsupported time unit '{unit}'. Valid: {list(TIME_TO_SECONDS.keys())}")
        return value * TIME_TO_SECONDS[u]

    @staticmethod
    def convert_vector(vec: List[float], unit: str, kind: str = "distance") -> List[float]:
        """Convert each component of a vector (position, velocity, or acceleration) to SI."""
        if kind == "distance":
            return [UnitConverter.to_meters(x, unit) for x in vec]
        elif kind == "speed" or kind == "velocity":
            return [UnitConverter.to_mps(x, unit) for x in vec]
        elif kind == "acceleration":
            return [UnitConverter.to_mps2(x, unit) for x in vec]
        else:
            raise UnitConversionError(f"Unknown vector kind: {kind}")

    @staticmethod
    def validate_dimension(vec: List[float], expected_dim: int, name: str = "vector") -> None:
        """Validate vector dimensionality and ensure all components are finite floats."""
        if not isinstance(vec, (list, tuple)):
            raise UnitConversionError(f"{name} must be a list of floats, got {type(vec)}")
        if len(vec) != expected_dim:
            raise UnitConversionError(f"{name} dimension mismatch: expected {expected_dim}D, got {len(vec)}D")
        for i, val in enumerate(vec):
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise UnitConversionError(f"{name}[{i}] must be a finite float, got: {val}")
