"""
ZYE AI — Kinematic Risk Intelligence & Monte Carlo Simulation Engine (Day 37 / Phase 3).
Provides deterministic 2D/3D kinematic collision analysis, CPA/TCPA/TTC calculation,
vectorized Monte Carlo trajectory simulation, Wilson Score confidence intervals,
and Day 35 telemetry & Day 36 Markov prediction adapters.
"""

from __future__ import annotations

from zye_realtime_tactical.kinematics.kinematic_models import (
    ConfidenceInterval,
    CoordinateDimension,
    DistributionType,
    KinematicRiskResult,
    KinematicState,
    MonteCarloResult,
    RiskCategory,
    SafetyEnvelope,
    ScenarioComparisonResult,
    UncertaintyConfig,
)
from zye_realtime_tactical.kinematics.unit_converter import (
    UnitConverter,
    UnitConversionError,
)
from zye_realtime_tactical.kinematics.kinematic_engine import KinematicEngine
from zye_realtime_tactical.kinematics.trajectory_predictor import TrajectoryPredictor
from zye_realtime_tactical.kinematics.uncertainty_distribution import (
    CovarianceValidationError,
    UncertaintyDistributionSampler,
)
from zye_realtime_tactical.kinematics.monte_carlo_engine import MonteCarloSimulationEngine
from zye_realtime_tactical.kinematics.statistical_analyzer import StatisticalAnalyzer
from zye_realtime_tactical.kinematics.risk_classifier import RiskClassifier
from zye_realtime_tactical.kinematics.telemetry_adapter import TelemetryAdapter
from zye_realtime_tactical.kinematics.markov_adapter import MarkovPredictionAdapter
from zye_realtime_tactical.kinematics.scenario_manager import ScenarioManager, ScenarioValidationError
from zye_realtime_tactical.kinematics.simulation_status_tracker import SimulationStatusTracker

__all__ = [
    "ConfidenceInterval",
    "CoordinateDimension",
    "CovarianceValidationError",
    "DistributionType",
    "KinematicEngine",
    "KinematicRiskResult",
    "KinematicState",
    "MarkovPredictionAdapter",
    "MonteCarloResult",
    "MonteCarloSimulationEngine",
    "RiskCategory",
    "RiskClassifier",
    "SafetyEnvelope",
    "ScenarioComparisonResult",
    "ScenarioManager",
    "ScenarioValidationError",
    "SimulationStatusTracker",
    "StatisticalAnalyzer",
    "TelemetryAdapter",
    "TrajectoryPredictor",
    "UncertaintyConfig",
    "UncertaintyDistributionSampler",
    "UnitConversionError",
    "UnitConverter",
]
