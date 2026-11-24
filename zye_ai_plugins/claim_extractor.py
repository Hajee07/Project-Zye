"""Response Claim Extraction & Normalization Engine for Zye AI Council.

Deconstructs free-form AI outputs into atomic, categorizable statements:
- Technical claims
- Factual statements
- Assumptions
- Recommendations
- Numerical metrics
- Safety considerations
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NormalizedClaim(BaseModel):
    """Normalized claim structure representing an atomic assertion."""
    claim_id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}")
    provider_id: str
    claim_text: str
    claim_type: str = "technical"  # technical | factual | assumption | recommendation | numerical | security
    topic: str = "general"
    supporting_evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    verification_status: str = "unverified"  # verified | unverified | disputed | unsupported
    confidence_label: str = "MODERATE"  # HIGH | MODERATE | LOW | UNVERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def _classify_claim_type(text: str) -> tuple[str, str]:
    """Classify the claim type and topic based on keywords and syntax."""
    text_lower = text.lower()

    # Claim Type
    if re.search(r"\b(recommend|suggest|prefer|should|propose|choice|adopt)\b", text_lower):
        ctype = "recommendation"
    elif re.search(r"\b(assume|assuming|premise|if we assume|provided that)\b", text_lower):
        ctype = "assumption"
    elif re.search(r"\b(\d+(?:\.\d+)?\s*(ms|seconds|minutes|mb|gb|kb|%|percent|qps|tps|req/s))\b", text_lower):
        ctype = "numerical"
    elif re.search(r"\b(vulnerabilit(y|ies)|exploit(s)?|threat(s)?|insecure|secure|security|attack(s)?|injection(s)?|auth|permission(s)?|cve|flaw(s)?)\b", text_lower):
        ctype = "security"
    elif re.search(r"\b(is|are|released|created|supports|contains|includes|exists)\b", text_lower):
        ctype = "factual"
    else:
        ctype = "technical"

    # Topic
    if any(k in text_lower for k in ("latency", "speed", "fast", "cpu", "ram", "memory", "overhead", "performance")):
        topic = "performance"
    elif any(k in text_lower for k in ("scale", "scalable", "throughput", "concurrency", "distributed")):
        topic = "scalability"
    elif any(k in text_lower for k in ("security", "secure", "insecure", "safe", "vulnerability", "vulnerabilities", "auth", "token", "ssrf", "flaw", "flaws")):
        topic = "security"
    elif any(k in text_lower for k in ("maintain", "clean", "refactor", "simple", "readability", "structure")):
        topic = "maintainability"
    elif any(k in text_lower for k in ("cost", "price", "budget", "billing", "token cost")):
        topic = "cost"
    elif any(k in text_lower for k in ("api", "library", "sdk", "framework", "import", "version", "architecture")):
        topic = "architecture"
    else:
        topic = "general"

    return ctype, topic


def extract_response_claims(provider_id: str, content: str) -> List[NormalizedClaim]:
    """Break unstructured response text into categorized atomic claims."""
    if not content or not content.strip():
        return []

    claims: List[NormalizedClaim] = []
    lines = content.strip().split("\n")

    # Clean sentence candidates
    sentence_candidates: List[str] = []
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
        # Strip markdown bullet markers or numbers: *, -, 1., 2.
        cleaned_line = re.sub(r"^(\*|-|\d+\.)\s+", "", cleaned_line)
        # Split line by strong terminators if multiple sentences exist
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned_line)
        for s in sentences:
            s_clean = s.strip()
            # Retain substantive sentences (min 15 chars, not markdown headers alone)
            if len(s_clean) >= 15 and not s_clean.startswith("#"):
                sentence_candidates.append(s_clean)

    # Convert candidates into NormalizedClaims
    for s in sentence_candidates[:20]:  # Limit to top 20 salient claims per response
        ctype, topic = _classify_claim_type(s)

        # Extract explicit assumptions if present
        assumptions = []
        if "assuming" in s.lower() or "if " in s.lower():
            assumptions.append("Conditional premise detected in statement")

        # Determine initial evidence confidence
        confidence = "HIGH" if ctype in ("numerical", "factual") and len(s) > 40 else "MODERATE"
        if ctype == "assumption":
            confidence = "LOW"

        claim = NormalizedClaim(
            provider_id=provider_id,
            claim_text=s,
            claim_type=ctype,
            topic=topic,
            supporting_evidence=[],
            assumptions=assumptions,
            verification_status="unverified",
            confidence_label=confidence,
        )
        claims.append(claim)

    return claims


def normalize_claims(claims: List[NormalizedClaim]) -> List[NormalizedClaim]:
    """Deduplicate and clean claims across provider outputs."""
    seen_texts = set()
    normalized: List[NormalizedClaim] = []

    for c in claims:
        norm_key = re.sub(r"[^\w\s]", "", c.claim_text.lower()).strip()
        if norm_key not in seen_texts:
            seen_texts.add(norm_key)
            normalized.append(c)

    return normalized


def classify_claims(claims: List[NormalizedClaim]) -> Dict[str, List[Dict[str, Any]]]:
    """Group claims by type for quick inspection."""
    categorized: Dict[str, List[Dict[str, Any]]] = {
        "recommendation": [],
        "technical": [],
        "factual": [],
        "numerical": [],
        "security": [],
        "assumption": [],
    }

    for c in claims:
        cat = c.claim_type if c.claim_type in categorized else "technical"
        categorized[cat].append(c.to_dict())

    return categorized


def compare_claims(claim_a: NormalizedClaim, claim_b: NormalizedClaim) -> Dict[str, Any]:
    """Compare two claims on semantic alignment, contradiction, or topic overlap."""
    words_a = set(re.findall(r"\w{4,}", claim_a.claim_text.lower()))
    words_b = set(re.findall(r"\w{4,}", claim_b.claim_text.lower()))

    intersection = words_a.intersection(words_b)
    overlap_score = len(intersection) / max(len(words_a.union(words_b)), 1)

    is_same_topic = (
        claim_a.topic == claim_b.topic
        or (claim_a.claim_type == claim_b.claim_type and claim_a.claim_type in ("security", "numerical", "recommendation"))
    )
    
    # Check for direct contradiction keywords on shared topic
    neg_a = any(w in claim_a.claim_text.lower() for w in ("not", "never", "avoid", "poor", "unsuitable", "bad", "disadvantage", "insecure", "flaw", "flaws", "fatal"))
    neg_b = any(w in claim_b.claim_text.lower() for w in ("not", "never", "avoid", "poor", "unsuitable", "bad", "disadvantage", "insecure", "flaw", "flaws", "fatal"))

    is_contradiction = (is_same_topic and overlap_score >= 0.20 and (neg_a != neg_b))

    return {
        "claim_a_id": claim_a.claim_id,
        "claim_b_id": claim_b.claim_id,
        "overlap_score": round(overlap_score, 2),
        "is_same_topic": is_same_topic,
        "is_contradiction": is_contradiction,
        "shared_terms": sorted(list(intersection)),
    }
