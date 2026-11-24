"""
Data models and structured schemas for ZYE AI News Verification Engine (Day 38 / Phase 3).
Defines strongly typed models for articles, claims, evidence matrices, contradictions,
independence classifications, and verification results.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IndependenceClassification(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    SAME_PUBLISHER = "SAME_PUBLISHER"
    SAME_OWNERSHIP_GROUP = "SAME_OWNERSHIP_GROUP"
    SYNDICATED = "SYNDICATED"
    DUPLICATE = "DUPLICATE"
    UNKNOWN_INDEPENDENCE = "UNKNOWN_INDEPENDENCE"


class VerificationStatus(str, Enum):
    CORROBORATED = "CORROBORATED"
    SINGLE_SOURCE_UNVERIFIED = "SINGLE_SOURCE_UNVERIFIED"
    UNVERIFIED_INSUFFICIENT_SOURCES = "UNVERIFIED_INSUFFICIENT_SOURCES"
    DUPLICATE_REPORTS = "DUPLICATE_REPORTS"
    SYNDICATED_REPORTS = "SYNDICATED_REPORTS"
    CONFLICTING_REPORTS = "CONFLICTING_REPORTS"
    STALE_REPORTS = "STALE_REPORTS"
    NO_RESULTS = "NO_RESULTS"
    SOURCE_FETCH_FAILED = "SOURCE_FETCH_FAILED"
    INVALID_SOURCE_METADATA = "INVALID_SOURCE_METADATA"
    NEEDS_MANUAL_REVIEW = "NEEDS_MANUAL_REVIEW"


class SourceQualityType(str, Enum):
    OFFICIAL_PRIMARY_SOURCE = "OFFICIAL_PRIMARY_SOURCE"
    INDEPENDENT_NEWS_REPORT = "INDEPENDENT_NEWS_REPORT"
    GOVERNMENT_PUBLICATION = "GOVERNMENT_PUBLICATION"
    REGULATORY_DOCUMENT = "REGULATORY_DOCUMENT"
    SCIENTIFIC_PUBLICATION = "SCIENTIFIC_PUBLICATION"
    COMPANY_ANNOUNCEMENT = "COMPANY_ANNOUNCEMENT"
    EYEWITNESS_REPORT = "EYEWITNESS_REPORT"
    SECONDARY_REPORT = "SECONDARY_REPORT"
    SOCIAL_MEDIA_POST = "SOCIAL_MEDIA_POST"
    UNKNOWN_SOURCE_TYPE = "UNKNOWN_SOURCE_TYPE"


class NewsArticle(BaseModel):
    """Normalized article metadata representation extracted from live search or HTTP content."""
    title: str = Field(..., description="Article headline")
    url: str = Field(..., description="Original article URL")
    canonical_url: str = Field(default="", description="Normalized URL stripped of tracking parameters")
    source_name: str = Field(default="", description="Raw display source name returned by provider")
    source: Optional[str] = Field(default=None, description="Alias for source_name")
    canonical_domain: str = Field(default="", description="Normalized host / registrable domain (e.g. 'bbc.com')")
    publisher_group: str = Field(default="UNKNOWN", description="Canonical media ownership group or brand")
    raw_date: Optional[str] = Field(default=None, description="Raw date string returned by search provider")
    published_at_utc: Optional[str] = Field(default=None, description="Normalized ISO 8601 UTC timestamp")
    published_timestamp: Optional[float] = Field(default=None, description="Epoch timestamp in seconds")
    timestamp_status: str = Field(default="UNKNOWN", description="VALID_UTC, MISSING_TIMESTAMP, INVALID_TIMESTAMP, FUTURE_TIMESTAMP, STALE")
    snippet: str = Field(default="", description="Article body summary / snippet")
    author: Optional[str] = Field(default=None, description="Byline / author if present")
    wire_attribution: Optional[str] = Field(default=None, description="Wire service attribution (e.g. 'Reuters', 'AP', 'PTI')")
    independence: IndependenceClassification = Field(default=IndependenceClassification.UNKNOWN_INDEPENDENCE)
    source_quality: SourceQualityType = Field(default=SourceQualityType.INDEPENDENT_NEWS_REPORT)
    fingerprint: str = Field(default="", description="Content/headline hash for duplicate detection")
    is_stale: bool = Field(default=False, description="True if published date falls outside the freshness window")

    def model_post_init(self, __context: Any) -> None:
        if self.source and not self.source_name:
            self.source_name = self.source
        if not self.canonical_url and self.url:
            try:
                from zye_realtime_tactical.news.url_normalizer import UrlNormalizer
                self.canonical_url = UrlNormalizer.normalize_url(self.url)
            except Exception:
                self.canonical_url = self.url
        if not self.canonical_domain and self.url:
            try:
                from zye_realtime_tactical.news.url_normalizer import UrlNormalizer
                self.canonical_domain = UrlNormalizer.extract_canonical_domain(self.url)
            except Exception:
                pass


class Claim(BaseModel):
    """Atomic factual proposition extracted for cross-source corroboration."""
    claim_id: str
    claim_text: str
    subject: str = Field(default="", description="Core subject entity / organization / person")
    event_or_action: str = Field(default="", description="Reported action or event")
    numerical_values: List[str] = Field(default_factory=list, description="Extracted numerical figures (e.g. '50%', '$10M')")
    date_values: List[str] = Field(default_factory=list, description="Extracted event dates or temporal references")
    status: str = Field(default="PENDING", description="CORROBORATED, UNVERIFIED, CONFLICTING")
    supporting_source_count: int = 0
    supporting_sources: List[Dict[str, Any]] = Field(default_factory=list)
    contradicting_sources: List[Dict[str, Any]] = Field(default_factory=list)


class Contradiction(BaseModel):
    """Detailed record of a factual contradiction discovered between reporting sources."""
    claim_id: str
    conflict_type: str = Field(..., description="NUMERICAL, DATE, OUTCOME, FACTUAL")
    field: str = Field(default="number", description="Conflicting field alias (e.g. 'number', 'date', 'outcome')")
    source_a_publisher: str
    source_a_url: str
    source_a_value: str
    source_b_publisher: str
    source_b_url: str
    source_b_value: str
    newer_source_url: Optional[str] = None
    is_correction: bool = Field(default=False, description="True if one source explicitly corrects an earlier report")
    explanation: str


class SourceIndependenceResult(BaseModel):
    """Structured assessment of independence between multiple news reports."""
    total_sources_evaluated: int
    independent_publisher_count: int
    publishers_identified: List[Dict[str, Any]] = Field(default_factory=list)
    syndication_detected: bool = False
    syndication_details: List[Dict[str, Any]] = Field(default_factory=list)
    duplicates_detected: bool = False
    duplicate_details: List[Dict[str, Any]] = Field(default_factory=list)
    independence_summary: Dict[str, str] = Field(default_factory=dict)
    explanation: str


class ClaimVerificationResult(BaseModel):
    """Structured output for user-provided claim verification."""
    claim: str
    status: VerificationStatus
    interpretation: str
    supporting_source_count: int
    independent_supporting_count: int
    supporting_sources: List[Dict[str, Any]] = Field(default_factory=list)
    contradicting_sources: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    proactive_alert_eligible: bool = False
    explanation: str


class NewsVerificationResult(BaseModel):
    """Comprehensive output schema for live news verification query."""
    status: VerificationStatus
    topic: str
    checked_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_policy: Dict[str, Any] = Field(
        default_factory=lambda: {
            "minimum_independent_sources": 2,
            "require_valid_timestamps": True,
            "require_same_claim_corroboration": True,
            "suppress_unverified_alerts": True,
            "freshness_window_hours": 72,
        }
    )
    source_summary: Dict[str, int] = Field(
        default_factory=lambda: {
            "total_results": 0,
            "valid_results": 0,
            "duplicate_results": 0,
            "syndicated_results": 0,
            "stale_results": 0,
            "independent_sources": 0,
        }
    )
    verified_claims: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    excluded_reports: List[Dict[str, Any]] = Field(default_factory=list)
    proactive_alert_eligible: bool = False
    voice_summary: str = Field(default="", description="Grounded, concise text suitable for TTS voice notification")
    warnings: List[str] = Field(default_factory=list)
    compute_time_ms: float = 0.0
    verified: bool = True
