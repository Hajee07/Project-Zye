"""
ZYE AI — Real-Time News Intelligence & Verification Package (Phase 3 / Day 38).
DuckDuckGo News integration, canonical domain normalization, publisher independence evaluation,
syndication & duplicate detection, publication timestamp validation, atomic claim corroboration,
content validation with SSRF defense, and proactive voice alert gating.
"""

from __future__ import annotations

from zye_realtime_tactical.news.claim_corroborator import ClaimCorroborator
from zye_realtime_tactical.news.content_validator import ContentValidator
from zye_realtime_tactical.news.news_models import (
    Claim,
    ClaimVerificationResult,
    Contradiction,
    IndependenceClassification,
    NewsArticle,
    NewsVerificationResult,
    SourceIndependenceResult,
    VerificationStatus,
)
from zye_realtime_tactical.news.news_retriever import NewsRetriever
from zye_realtime_tactical.news.publisher_registry import PublisherRegistry
from zye_realtime_tactical.news.syndication_detector import SyndicationDetector
from zye_realtime_tactical.news.timestamp_validator import TimestampValidator
from zye_realtime_tactical.news.url_normalizer import UrlNormalizer
from zye_realtime_tactical.news.verification_engine import NewsVerificationEngine

__all__ = [
    "NewsVerificationEngine",
    "NewsRetriever",
    "UrlNormalizer",
    "PublisherRegistry",
    "SyndicationDetector",
    "TimestampValidator",
    "ClaimCorroborator",
    "ContentValidator",
    "NewsArticle",
    "Claim",
    "Contradiction",
    "VerificationStatus",
    "IndependenceClassification",
    "NewsVerificationResult",
    "ClaimVerificationResult",
    "SourceIndependenceResult",
]
