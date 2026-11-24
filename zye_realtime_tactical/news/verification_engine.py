"""
ZYE AI — Master Real-Time News Verification & Anti-Fake News Engine (Day 38 / Phase 3).
Orchestrates retrieval, canonical normalization, publisher independence analysis,
syndication detection, timestamp validation, claim-level corroboration, and proactive alert gates.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from zye_realtime_tactical.news.claim_corroborator import ClaimCorroborator
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

logger = logging.getLogger("zye.realtime_tactical.news.verification_engine")


class NewsVerificationEngine:
    """Master facade for multi-source independent news verification and false-information suppression."""

    _instance: Optional[NewsVerificationEngine] = None

    def __init__(
        self,
        registry: Optional[PublisherRegistry] = None,
        retriever: Optional[NewsRetriever] = None,
    ) -> None:
        self.registry = registry or PublisherRegistry.get_instance()
        self.retriever = retriever or NewsRetriever()
        self.syndication_detector = SyndicationDetector(registry=self.registry)
        self._cache: Dict[str, Tuple[float, NewsVerificationResult]] = {}
        self._cache_ttl_seconds: float = 300.0  # 5 minutes
        self._total_verifications: int = 0
        self._corroborated_count: int = 0
        self._last_verification_timestamp: float = 0.0
        self._last_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> NewsVerificationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets engine singleton for isolated testing."""
        cls._instance = None

    def verify_topic_sync(
        self,
        topic: str,
        max_results: int = 8,
        freshness_window_hours: float = 72.0,
        as_of_timestamp: Optional[float] = None,
        use_cache: bool = True,
    ) -> NewsVerificationResult:
        """Synchronously executes end-to-end news verification (for offline testing & synchronous callers)."""
        t_start = time.perf_counter_ns()
        clean_topic = topic.strip()
        now_epoch = as_of_timestamp if as_of_timestamp is not None else time.time()

        cache_key = f"{clean_topic.lower()}_{max_results}_{freshness_window_hours}"
        if use_cache and cache_key in self._cache:
            cached_time, cached_res = self._cache[cache_key]
            if (now_epoch - cached_time) < self._cache_ttl_seconds:
                return cached_res

        self._total_verifications += 1
        self._last_verification_timestamp = now_epoch

        search_status, raw_items, err_msg = self.retriever.fetch_news_results_sync(
            topic=clean_topic,
            max_results=max_results,
        )
        return self._evaluate_articles(
            clean_topic=clean_topic,
            raw_items=raw_items,
            search_status=search_status,
            err_msg=err_msg,
            freshness_window_hours=freshness_window_hours,
            now_epoch=now_epoch,
            t_start=t_start,
            cache_key=cache_key,
            use_cache=use_cache,
        )

    async def verify_topic(
        self,
        topic: str,
        max_results: int = 8,
        freshness_window_hours: float = 72.0,
        as_of_timestamp: Optional[float] = None,
        use_cache: bool = True,
    ) -> NewsVerificationResult:
        """
        Executes end-to-end news verification for a given topic:
        Searches news, normalizes sources, checks independence, validates timestamps,
        extracts atomic claims, detects contradictions, and evaluates proactive alert eligibility.
        """
        t_start = time.perf_counter_ns()
        clean_topic = topic.strip()
        now_epoch = as_of_timestamp if as_of_timestamp is not None else time.time()

        # Check Cache
        cache_key = f"{clean_topic.lower()}_{max_results}_{freshness_window_hours}"
        if use_cache and cache_key in self._cache:
            cached_time, cached_res = self._cache[cache_key]
            if (now_epoch - cached_time) < self._cache_ttl_seconds:
                return cached_res

        self._total_verifications += 1
        self._last_verification_timestamp = now_epoch

        # 1. Retrieve Candidate News Articles
        search_status, raw_items, err_msg = await self.retriever.fetch_news_results(
            topic=clean_topic,
            max_results=max_results,
        )
        return self._evaluate_articles(
            clean_topic=clean_topic,
            raw_items=raw_items,
            search_status=search_status,
            err_msg=err_msg,
            freshness_window_hours=freshness_window_hours,
            now_epoch=now_epoch,
            t_start=t_start,
            cache_key=cache_key,
            use_cache=use_cache,
        )

    def _evaluate_articles(
        self,
        clean_topic: str,
        raw_items: List[Dict[str, Any]],
        search_status: str,
        err_msg: Optional[str],
        freshness_window_hours: float,
        now_epoch: float,
        t_start: int,
        cache_key: str,
        use_cache: bool,
    ) -> NewsVerificationResult:
        if search_status == "NO_RESULTS" or not raw_items:
            res = NewsVerificationResult(
                status=VerificationStatus.NO_RESULTS,
                topic=clean_topic,
                warnings=[err_msg or "No news items discovered for the requested topic."],
                proactive_alert_eligible=False,
                voice_summary="No news reports found for this topic.",
                compute_time_ms=round((time.perf_counter_ns() - t_start) / 1e6, 2),
            )
            return res

        if search_status in ("NEWS_PROVIDER_UNAVAILABLE", "NEWS_SEARCH_TIMEOUT"):
            self._last_error = err_msg
            res = NewsVerificationResult(
                status=VerificationStatus.SOURCE_FETCH_FAILED,
                topic=clean_topic,
                warnings=[f"External news provider failed: {err_msg}"],
                proactive_alert_eligible=False,
                voice_summary="News verification could not be completed because the search provider is unavailable.",
                compute_time_ms=round((time.perf_counter_ns() - t_start) / 1e6, 2),
            )
            return res

        # 2. Normalize and Ingest Candidate Articles
        articles: List[NewsArticle] = []
        excluded_reports: List[Dict[str, Any]] = []

        for item in raw_items:
            raw_url = item.get("url", "")
            raw_title = item.get("title", "")
            raw_source = item.get("source", "")
            raw_date = item.get("date", "")
            raw_body = item.get("body", "") or item.get("snippet", "")

            # URL validation & canonicalization
            try:
                canonical_url = UrlNormalizer.normalize_url(raw_url)
                canonical_domain = UrlNormalizer.extract_canonical_domain(canonical_url)
            except Exception as exc:
                excluded_reports.append({
                    "raw_url": raw_url,
                    "title": raw_title,
                    "reason": f"Invalid URL metadata: {exc}",
                })
                continue

            # Publisher Group Resolution
            pub_group = self.registry.resolve_publisher_group(canonical_domain, raw_source)

            # Timestamp parsing and freshness evaluation
            ts_status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
                raw_date=raw_date,
                freshness_window_hours=freshness_window_hours,
                as_of_timestamp=now_epoch,
            )

            # Headline & content fingerprint for deduplication
            fingerprint = SyndicationDetector.compute_text_fingerprint(f"{raw_title} {raw_body}")
            wire_attr = SyndicationDetector.detect_wire_attribution(f"{raw_title} {raw_body}")

            article = NewsArticle(
                title=raw_title,
                url=raw_url,
                canonical_url=canonical_url,
                source_name=raw_source or canonical_domain,
                canonical_domain=canonical_domain,
                publisher_group=pub_group,
                raw_date=raw_date,
                published_at_utc=iso_utc,
                published_timestamp=epoch_ts,
                timestamp_status=ts_status,
                snippet=raw_body,
                author=item.get("author"),
                wire_attribution=wire_attr,
                fingerprint=fingerprint,
                is_stale=is_stale,
            )
            articles.append(article)

        if not articles:
            return NewsVerificationResult(
                status=VerificationStatus.INVALID_SOURCE_METADATA,
                topic=clean_topic,
                excluded_reports=excluded_reports,
                warnings=["All retrieved news items contained invalid URLs or corrupted metadata."],
                proactive_alert_eligible=False,
                voice_summary="All candidate news articles contained invalid metadata.",
                compute_time_ms=round((time.perf_counter_ns() - t_start) / 1e6, 2),
            )

        # 3. Source Independence & Syndication Detection
        independence_res = self.syndication_detector.analyze_source_set_independence(articles)

        # 4. Factual Claim Extraction & Cross-Source Corroboration
        claim_primary = ClaimCorroborator.evaluate_claim_corroboration(
            claim_text=clean_topic,
            articles=articles,
            claim_id="claim_primary",
        )

        # 5. Contradiction Detection
        contradictions = ClaimCorroborator.detect_contradictions(articles, claim_id="claim_primary")

        # 6. Source Summary Accounting
        duplicate_count = sum(1 for a in articles if a.independence == IndependenceClassification.DUPLICATE)
        syndicated_count = sum(1 for a in articles if a.independence == IndependenceClassification.SYNDICATED)
        stale_count = sum(1 for a in articles if a.is_stale)
        independent_sources = independence_res.independent_publisher_count

        source_summary = {
            "total_results": len(raw_items),
            "valid_results": len(articles),
            "duplicate_results": duplicate_count,
            "syndicated_results": syndicated_count,
            "stale_results": stale_count,
            "independent_sources": independent_sources,
        }

        # 7. Verification Gate Decision Matrix
        warnings: List[str] = []
        status: VerificationStatus

        if len(contradictions) > 0:
            status = VerificationStatus.CONFLICTING_REPORTS
            warnings.append(
                f"Discovered {len(contradictions)} factual contradictions across reporting sources."
            )
        elif independent_sources >= 2 and claim_primary.status == "CORROBORATED":
            # Check timestamps validity on supporting independent sources
            valid_supporting_ts = [
                s for s in claim_primary.supporting_sources if s.get("published_at") is not None
            ]
            if len(valid_supporting_ts) >= 2:
                status = VerificationStatus.CORROBORATED
                self._corroborated_count += 1
            else:
                status = VerificationStatus.UNVERIFIED_INSUFFICIENT_SOURCES
                warnings.append(
                    "Independent sources support the claim, but fewer than 2 possess valid, verifiable timestamps."
                )
        elif stale_count == len(articles) and stale_count > 0:
            status = VerificationStatus.STALE_REPORTS
            warnings.append(
                f"All candidate reports are older than the freshness threshold ({freshness_window_hours} hours)."
            )
        elif len(articles) > 1 and (duplicate_count + syndicated_count == len(articles) - 1) and independent_sources <= 1:
            if syndicated_count > 0:
                status = VerificationStatus.SYNDICATED_REPORTS
                warnings.append("Articles originate from a single syndicated wire agency or press release.")
            else:
                status = VerificationStatus.DUPLICATE_REPORTS
                warnings.append("Multiple results represent duplicate republishings of a single original article.")
        elif independent_sources == 1:
            status = VerificationStatus.SINGLE_SOURCE_UNVERIFIED
            warnings.append("Only a single independent publisher was discovered. Minimum requirement is 2.")
        else:
            status = VerificationStatus.UNVERIFIED_INSUFFICIENT_SOURCES
            warnings.append("Insufficient independent evidence to corroborate the requested topic.")

        # 8. Strict Proactive Alert Gate
        proactive_alert_eligible = (
            status == VerificationStatus.CORROBORATED
            and independent_sources >= 2
            and len(contradictions) == 0
        )

        # 9. Grounded Voice Summary Generation
        if status == VerificationStatus.CORROBORATED:
            voice_summary = (
                f"Zye Verified Update: {clean_topic} has been corroborated by {independent_sources} "
                f"independent publishers with verified timestamps."
            )
        elif status == VerificationStatus.CONFLICTING_REPORTS:
            voice_summary = (
                f"Zye Intelligence Alert: Conflicting reports detected for {clean_topic}. "
                f"Sources report contradictory figures or outcomes."
            )
        elif status == VerificationStatus.SINGLE_SOURCE_UNVERIFIED:
            voice_summary = (
                f"Indha update-ai single source mattumae report pannirukku. "
                f"Second independent source verify panna mudiyala."
            )
        else:
            voice_summary = (
                "Indha update-ai independent sources moolama verify panna mudiyala. "
                "Ippo confirmed news-ah report panna evidence podhavillai."
            )

        compute_ms = round((time.perf_counter_ns() - t_start) / 1e6, 2)

        result = NewsVerificationResult(
            status=status,
            topic=clean_topic,
            checked_at_utc=datetime.now(timezone.utc).isoformat(),
            source_summary=source_summary,
            verified_claims=[claim_primary.model_dump()],
            contradictions=[c.model_dump() for c in contradictions],
            excluded_reports=excluded_reports,
            proactive_alert_eligible=proactive_alert_eligible,
            voice_summary=voice_summary,
            warnings=warnings,
            compute_time_ms=compute_ms,
            verified=True,
        )

        # Update cache
        if use_cache:
            self._cache[cache_key] = (now_epoch, result)

        return result

    def verify_specific_claim_sync(
        self,
        claim: str,
        search_context: Optional[str] = None,
        freshness_window_hours: float = 72.0,
        max_results: int = 8,
    ) -> ClaimVerificationResult:
        """Synchronously verifies a factual claim (for offline tests & synchronous callers)."""
        search_query = search_context or claim
        topic_res = self.verify_topic_sync(
            topic=search_query,
            max_results=max_results,
            freshness_window_hours=freshness_window_hours,
        )
        primary_claim = topic_res.verified_claims[0] if topic_res.verified_claims else {}
        supporting = primary_claim.get("supporting_sources", [])
        contradicting = primary_claim.get("contradicting_sources", [])
        independent_count = sum(
            1 for s in supporting if s.get("independence") == "INDEPENDENT"
        )
        explanation = (
            f"Claim evaluated against {topic_res.source_summary.get('valid_results', 0)} articles. "
            f"Supported by {independent_count} independent sources; status: {topic_res.status.value}."
        )
        return ClaimVerificationResult(
            claim=claim,
            status=topic_res.status,
            interpretation=f"Atomic factual evaluation for: {claim}",
            supporting_source_count=len(supporting),
            independent_supporting_count=independent_count,
            supporting_sources=supporting,
            contradicting_sources=contradicting,
            contradictions=topic_res.contradictions,
            proactive_alert_eligible=topic_res.proactive_alert_eligible,
            explanation=explanation,
        )

    async def verify_specific_claim(
        self,
        claim: str,
        search_context: Optional[str] = None,
        freshness_window_hours: float = 72.0,
        max_results: int = 8,
    ) -> ClaimVerificationResult:
        """Verifies a user-provided factual claim by performing targeted search and atomic matching."""
        search_query = search_context or claim
        topic_res = await self.verify_topic(
            topic=search_query,
            max_results=max_results,
            freshness_window_hours=freshness_window_hours,
        )

        primary_claim = topic_res.verified_claims[0] if topic_res.verified_claims else {}
        supporting = primary_claim.get("supporting_sources", [])
        contradicting = primary_claim.get("contradicting_sources", [])
        independent_count = sum(
            1 for s in supporting if s.get("independence") == "INDEPENDENT"
        )

        explanation = (
            f"Claim evaluated against {topic_res.source_summary.get('valid_results', 0)} articles. "
            f"Supported by {independent_count} independent sources; status: {topic_res.status.value}."
        )

        return ClaimVerificationResult(
            claim=claim,
            status=topic_res.status,
            interpretation=f"Atomic factual evaluation for: {claim}",
            supporting_source_count=len(supporting),
            independent_supporting_count=independent_count,
            supporting_sources=supporting,
            contradicting_sources=contradicting,
            contradictions=topic_res.contradictions,
            proactive_alert_eligible=topic_res.proactive_alert_eligible,
            explanation=explanation,
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime diagnostics and performance telemetry for the news engine."""
        return {
            "engine_status": "OPERATIONAL",
            "total_verifications": self._total_verifications,
            "corroborated_verifications": self._corroborated_count,
            "cached_query_count": len(self._cache),
            "last_verification_timestamp": self._last_verification_timestamp,
            "last_error": self._last_error,
            "verification_policy": {
                "minimum_independent_sources": 2,
                "freshness_window_hours": 72.0,
                "suppress_unverified_alerts": True,
            },
        }
