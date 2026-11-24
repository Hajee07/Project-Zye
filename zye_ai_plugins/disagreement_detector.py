"""Disagreement Detection Engine for Zye AI Council.

Identifies, categorizes, and ranks conflicts, divergent recommendations,
and contradictory statements across participating AI models.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .claim_extractor import NormalizedClaim, compare_claims


class DisagreementItem(BaseModel):
    """Structured representation of an identified disagreement between models."""
    disagreement_id: str = Field(default_factory=lambda: f"dag_{uuid.uuid4().hex[:8]}")
    category: str  # FACTUAL | TECHNICAL | ASSUMPTION | PERFORMANCE | SECURITY | IMPLEMENTATION | PRIORITY | INSUFFICIENT_INFO
    topic: str
    provider_a: str
    provider_b: str
    position_a: str
    position_b: str
    explanation: str
    severity: str = "MEDIUM"  # LOW | MEDIUM | HIGH | CRITICAL
    resolution_status: str = "UNRESOLVED"  # UNRESOLVED | RESOLVED_BY_EVIDENCE | RECONCILED_BY_GEMINI

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def _evaluate_severity(category: str, topic: str, position_a: str, position_b: str) -> str:
    """Determine disagreement severity based on domain impact."""
    if category == "SECURITY" or topic == "security":
        return "CRITICAL"
    if category in ("TECHNICAL", "FACTUAL") and any(k in topic for k in ("architecture", "scalability", "performance")):
        return "HIGH"
    if category in ("PERFORMANCE", "IMPLEMENTATION"):
        return "MEDIUM"
    return "LOW"


def classify_disagreement(claim_a: NormalizedClaim, claim_b: NormalizedClaim) -> Optional[DisagreementItem]:
    """Examine two claims for genuine divergence or contradiction."""
    if claim_a.provider_id == claim_b.provider_id:
        return None

    cmp_meta = compare_claims(claim_a, claim_b)
    
    # 1. Direct contradiction detected
    if cmp_meta["is_contradiction"]:
        category = "TECHNICAL"
        if claim_a.topic == "security":
            category = "SECURITY"
        elif claim_a.topic == "performance":
            category = "PERFORMANCE"
        elif claim_a.claim_type == "factual":
            category = "FACTUAL"

        severity = _evaluate_severity(category, claim_a.topic, claim_a.claim_text, claim_b.claim_text)
        
        return DisagreementItem(
            category=category,
            topic=claim_a.topic,
            provider_a=claim_a.provider_id,
            provider_b=claim_b.provider_id,
            position_a=claim_a.claim_text,
            position_b=claim_b.claim_text,
            explanation=f"{claim_a.provider_id.upper()} and {claim_b.provider_id.upper()} assert conflicting positions on {claim_a.topic}.",
            severity=severity,
            resolution_status="UNRESOLVED",
        )

    # 2. Competing recommendations on the same topic
    if claim_a.claim_type == "recommendation" and claim_b.claim_type == "recommendation":
        if claim_a.topic == claim_b.topic and cmp_meta["overlap_score"] < 0.6:
            category = "TECHNICAL"
            severity = "HIGH" if claim_a.topic in ("architecture", "security") else "MEDIUM"
            return DisagreementItem(
                category=category,
                topic=claim_a.topic,
                provider_a=claim_a.provider_id,
                provider_b=claim_b.provider_id,
                position_a=claim_a.claim_text,
                position_b=claim_b.claim_text,
                explanation=f"{claim_a.provider_id.upper()} recommends a different architectural path than {claim_b.provider_id.upper()}.",
                severity=severity,
                resolution_status="UNRESOLVED",
            )

    # 3. Divergent numerical claims
    if claim_a.claim_type == "numerical" and claim_b.claim_type == "numerical":
        if (claim_a.topic == claim_b.topic or cmp_meta["overlap_score"] >= 0.2):
            num_a = re.findall(r"\d+(?:\.\d+)?", claim_a.claim_text)
            num_b = re.findall(r"\d+(?:\.\d+)?", claim_b.claim_text)
            if num_a != num_b:
                return DisagreementItem(
                    category="PERFORMANCE",
                    topic=claim_a.topic,
                    provider_a=claim_a.provider_id,
                    provider_b=claim_b.provider_id,
                    position_a=claim_a.claim_text,
                    position_b=claim_b.claim_text,
                    explanation=f"Numerical metrics differ between {claim_a.provider_id} and {claim_b.provider_id}.",
                    severity="MEDIUM",
                    resolution_status="UNRESOLVED",
                )

    return None


def detect_disagreements(provider_claims: Dict[str, List[NormalizedClaim]]) -> List[DisagreementItem]:
    """Scan all pairwise claims across providers and detect substantive disagreements."""
    disagreements: List[DisagreementItem] = []
    providers = list(provider_claims.keys())
    seen_pairs = set()

    for i in range(len(providers)):
        p_a = providers[i]
        claims_a = provider_claims[p_a]

        for j in range(i + 1, len(providers)):
            p_b = providers[j]
            claims_b = provider_claims[p_b]

            for ca in claims_a:
                for cb in claims_b:
                    dag = classify_disagreement(ca, cb)
                    if dag:
                        # Avoid duplicate topic pairs
                        pair_key = tuple(sorted([dag.position_a, dag.position_b]))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            disagreements.append(dag)

    return rank_disagreement_severity(disagreements)


def rank_disagreement_severity(disagreements: List[DisagreementItem]) -> List[DisagreementItem]:
    """Sort disagreements by critical severity first: CRITICAL > HIGH > MEDIUM > LOW."""
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(disagreements, key=lambda d: severity_rank.get(d.severity, 4))


def generate_disagreement_report(disagreements: List[DisagreementItem]) -> Dict[str, Any]:
    """Generate structured summary of disagreements."""
    critical_count = len([d for d in disagreements if d.severity == "CRITICAL"])
    high_count = len([d for d in disagreements if d.severity == "HIGH"])

    return {
        "total_disagreements": len(disagreements),
        "critical_count": critical_count,
        "high_severity_count": high_count,
        "requires_evidence_resolution": (critical_count + high_count) > 0,
        "items": [d.to_dict() for d in disagreements],
    }
