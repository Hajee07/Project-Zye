"""
Kinematic Data Models and Structured Result Schemas (Day 37 / Phase 3).
Pydantic data models for 2D/3D kinematic states, safety envelopes, uncertainty configs,
deterministic risk results, and Monte Carlo probabilistic simulation outputs.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CoordinateDimension(int, Enum):
    TWO_D = 2
    THREE_D = 3


class RiskCategory(str, Enum):
    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DistributionType(str, Enum):
    NORMAL = "NORMAL"
    UNIFORM = "UNIFORM"
    TRUNCATED_NORMAL = "TRUNCATED_NORMAL"
    EMPIRICAL = "EMPIRICAL"


class KinematicState(BaseModel):
    """Represents the instantaneous physical state of a moving entity in SI units (m, m/s, m/s^2)."""
    entity_id: str = Field(..., description="Unique entity identifier (e.g. 'drone_alpha', 'vehicle_01')")
    timestamp: float = Field(default_factory=time.time, description="State timestamp in seconds (epoch or relative)")
    position: List[float] = Field(..., description="Position vector [x, y] or [x, y, z] in meters")
    velocity: List[float] = Field(..., description="Velocity vector [vx, vy] or [vx, vy, vz] in m/s")
    acceleration: Optional[List[float]] = Field(default=None, description="Acceleration vector [ax, ay] or [ax, ay, az] in m/s^2")
    radius: float = Field(default=1.0, ge=0.0, description="Effective physical bounding radius in meters")
    uncertainty_pos: Optional[List[float]] = Field(default=None, description="1-sigma position standard deviation per axis [m]")
    uncertainty_vel: Optional[List[float]] = Field(default=None, description="1-sigma velocity standard deviation per axis [m/s]")
    covariance_pos: Optional[List[List[float]]] = Field(default=None, description="Spatial covariance matrix (dim x dim)")
    covariance_vel: Optional[List[List[float]]] = Field(default=None, description="Velocity covariance matrix (dim x dim)")


class SafetyEnvelope(BaseModel):
    """Defines the spatial collision boundaries and clearance margins for risk assessment."""
    combined_radius: float = Field(default=2.0, ge=0.0, description="Sum of physical entity radii in meters (R_A + R_B)")
    clearance_margin: float = Field(default=3.0, ge=0.0, description="Additional safety separation margin in meters")
    uncertainty_margin: float = Field(default=1.0, ge=0.0, description="Measurement error buffer in meters")
    reaction_time_sec: float = Field(default=0.5, ge=0.0, description="Allowed human or autonomous reaction buffer in seconds")

    @property
    def near_miss_radius(self) -> float:
        """Near-miss threshold distance including clearance and uncertainty."""
        return self.combined_radius + self.clearance_margin + self.uncertainty_margin


class UncertaintyConfig(BaseModel):
    """Configuration container for Monte Carlo stochastic perturbation distributions."""
    distribution_type: DistributionType = Field(default=DistributionType.NORMAL)
    pos_std: List[float] = Field(default_factory=lambda: [1.0, 1.0], description="Position std dev per axis [m]")
    vel_std: List[float] = Field(default_factory=lambda: [0.5, 0.5], description="Velocity std dev per axis [m/s]")
    accel_std: Optional[List[float]] = Field(default=None, description="Acceleration std dev per axis [m/s^2]")
    pos_cov: Optional[List[List[float]]] = Field(default=None, description="Correlated position covariance matrix")
    vel_cov: Optional[List[List[float]]] = Field(default=None, description="Correlated velocity covariance matrix")
    reaction_delay_mean: float = Field(default=0.0, ge=0.0, description="Mean reaction delay in seconds")
    reaction_delay_std: float = Field(default=0.0, ge=0.0, description="Reaction delay standard deviation in seconds")
    dimension_uncertainty_std: float = Field(default=0.0, ge=0.0, description="Standard deviation of physical radius [m]")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "position_std" in data and "pos_std" not in data:
                data["pos_std"] = data.pop("position_std")
            if "velocity_std" in data and "vel_std" not in data:
                data["vel_std"] = data.pop("velocity_std")
            if "accel_std" not in data and "acceleration_std" in data:
                data["accel_std"] = data.pop("acceleration_std")
        return data


class ConfidenceInterval(BaseModel):
    """Statistical confidence interval for an estimated probability or measurement."""
    lower: float = Field(..., ge=0.0, le=1.0, description="Lower confidence bound")
    upper: float = Field(..., ge=0.0, le=1.0, description="Upper confidence bound")
    confidence_level: float = Field(default=0.95, description="Statistical confidence level (e.g. 0.95 for 95%)")
    method: str = Field(default="WILSON_SCORE", description="Method used: WILSON_SCORE, CLOPPER_PEARSON, or NORMAL_APPROX")


class KinematicRiskResult(BaseModel):
    """Complete output for deterministic kinematic analysis."""
    status: str = Field(..., description="ANALYSIS_COMPLETED, COLLISION_IMMINENT, SAFE, or ERROR")
    dimension: int = Field(default=2, description="Spatial dimension (2 or 3)")
    entity_a_id: str
    entity_b_id: str
    relative_position: List[float] = Field(..., description="Vector r = pB - pA [m]")
    relative_velocity: List[float] = Field(..., description="Vector v = vB - vA [m/s]")
    relative_acceleration: Optional[List[float]] = Field(default=None, description="Vector a = aB - aA [m/s^2]")
    current_distance_m: float = Field(..., ge=0.0, description="Instantaneous Euclidean distance ||r|| [m]")
    closing_speed_mps: float = Field(..., description="Speed of approach -(r . v)/||r|| [m/s] (positive = closing)")
    is_approaching: bool = Field(..., description="True if entities are moving closer (r . v < 0)")
    cpa_time_sec: float = Field(..., ge=0.0, description="Time to Closest Point of Approach (TCPA) [s]")
    min_separation_m: float = Field(..., ge=0.0, description="Distance at CPA (d_CPA) [m]")
    ttc_sec: Optional[float] = Field(default=None, description="Time to Collision (TTC) within horizon if collision occurs [s]")
    collision_detected: bool = Field(default=False, description="True if trajectory penetrates combined collision radius")
    near_miss_detected: bool = Field(default=False, description="True if trajectory penetrates near-miss safety envelope")
    risk_category: RiskCategory = Field(default=RiskCategory.LOW)
    risk_explanation: str = Field(..., description="Transparent mathematical justification for assigned risk category")
    assumptions: List[str] = Field(default_factory=list, description="Explicit physical assumptions (e.g. CONSTANT_VELOCITY)")
    warnings: List[str] = Field(default_factory=list, description="Analytical notices or parameter warnings")
    compute_time_ms: float = Field(default=0.0, description="Execution compute time in milliseconds")

    @property
    def time_to_cpa_sec(self) -> float:
        return self.cpa_time_sec

    @property
    def closest_approach_distance_m(self) -> float:
        return self.min_separation_m

    @property
    def time_to_collision_sec(self) -> float:
        return self.ttc_sec if self.ttc_sec is not None else float("inf")


class MonteCarloResult(BaseModel):
    """Complete output for probabilistic Monte Carlo trajectory risk simulation."""
    status: str = Field(..., description="SIMULATION_COMPLETED, INSUFFICIENT_DATA, or ERROR")
    scenario_id: str = Field(..., description="Scenario identifier")
    model: str = Field(default="KINEMATIC_MONTE_CARLO")
    dimension: int = Field(default=2, description="2D or 3D simulation")
    sample_count: int = Field(..., description="Total stochastic scenarios simulated (e.g. 20,000)")
    simulation_horizon_seconds: float = Field(..., description="Future projection duration in seconds")
    collision_count: int = Field(..., ge=0, description="Number of simulated runs that resulted in collision")
    collision_probability: float = Field(..., ge=0.0, le=1.0, description="Empirical collision probability (k / N)")
    near_miss_count: int = Field(..., ge=0, description="Number of simulated runs that resulted in near-miss")
    near_miss_probability: float = Field(..., ge=0.0, le=1.0, description="Empirical near-miss probability")
    min_separation_m: float = Field(..., description="Absolute minimum separation observed across all samples [m]")
    median_separation_m: float = Field(..., description="50th percentile minimum separation [m]")
    mean_separation_m: float = Field(..., description="Mean minimum separation across all samples [m]")
    p05_separation_m: float = Field(..., description="5th percentile minimum separation [m] (worst 5% case)")
    p95_separation_m: float = Field(..., description="95th percentile minimum separation [m]")
    std_separation_m: float = Field(..., description="Standard deviation of minimum separation [m]")
    confidence_interval: ConfidenceInterval = Field(..., description="Confidence bounds for collision probability")
    random_seed: Optional[int] = Field(default=None, description="PRNG seed for bitwise reproducibility")
    execution_time_ms: float = Field(..., description="End-to-end simulation compute latency in milliseconds")
    throughput_samples_per_sec: float = Field(default=0.0, description="Monte Carlo simulation throughput")
    risk_category: RiskCategory = Field(default=RiskCategory.LOW)
    risk_explanation: str = Field(..., description="Human-readable explanation of probabilistic risk level")
    assumptions: List[str] = Field(default_factory=list, description="Model assumptions and physical parameters")
    warnings: List[str] = Field(default_factory=list, description="Analytical caveats and uncertainty limitations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution timing breakdowns and diagnostic telemetry")
    verified: bool = Field(default=True, description="Strict boolean confirming empirical completion")

    @property
    def empirical_collision_probability(self) -> float:
        return self.collision_probability

    @property
    def cpa_distance_distribution(self) -> Dict[str, float]:
        return {
            "min": self.min_separation_m,
            "p50": self.median_separation_m,
            "mean": self.mean_separation_m,
            "p05": self.p05_separation_m,
            "p95": self.p95_separation_m,
            "std": self.std_separation_m,
        }


class ScenarioComparisonResult(BaseModel):
    """Comparative analysis across multiple validated simulation scenarios."""
    status: str = Field(default="COMPARISON_COMPLETED")
    baseline_scenario_id: str
    comparison_scenario_ids: List[str]
    relative_risk_differences: Dict[str, float] = Field(
        default_factory=dict, description="Percentage point differences in collision probability compared to baseline"
    )
    separation_deltas_m: Dict[str, float] = Field(
        default_factory=dict, description="Difference in median separation compared to baseline [m]"
    )
    safer_scenario_id: str = Field(..., description="Identifier of scenario with the lowest overall risk")
    sensitivity_observations: List[str] = Field(default_factory=list)
    model_assumptions: List[str] = Field(default_factory=list)
