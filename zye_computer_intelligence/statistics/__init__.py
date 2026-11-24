"""
Statistical Analysis & Correlation Engine Subsystem.
Implements Pearson/Spearman correlations, descriptive profiling, time trends, and anomaly detection.
"""

from .correlation_engine import CorrelationEngine
from .summary_statistics import SummaryStatistics
from .segment_analytics import SegmentAnalytics
from .trend_engine import TrendEngine
from .anomaly_engine import AnomalyEngine

__all__ = [
    "CorrelationEngine",
    "SummaryStatistics",
    "SegmentAnalytics",
    "TrendEngine",
    "AnomalyEngine",
]
