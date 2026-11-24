"""
Reporting & Voice Summary Formatting Subsystem.
Synthesizes structured analytical reports, markdown dashboards, and Gemini Live voice scripts.
"""

from .analysis_report import AnalysisReportBuilder
from .result_formatter import ResultFormatter

__all__ = [
    "AnalysisReportBuilder",
    "ResultFormatter",
]
