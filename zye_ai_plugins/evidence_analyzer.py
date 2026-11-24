"""Evidence Verification and Uncertainty Analysis Engine for Zye AI Council.

Evaluates empirical support, classifies qualitative uncertainty, and catalogs
unsupported assumptions in multi-model deliberation outputs:
- Labels: HIGH EVIDENCE SUPPORT | MODERATE EVIDENCE SUPPORT | LOW EVIDENCE SUPPORT | INSUFFICIENT EVIDENCE | UNVERIFIED
- Prevents confusing model hallucination/confidence with factual verification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from .claim_extractor import NormalizedClaim


def analyze_answer_uncertainty(
    content: str,
    claims: List[NormalizedClaim],
) -> Dict[str, Any]:
    """Examine hedge words, conditional qualifiers, and evidentiary grounding."""
    if not content:
        return {
            "evidence_tier": "INSUFFICIENT EVIDENCE",
            "uncertainty_score": 1.0,
            "hedge_phrases": [],
            "unsupported_assumptions": [],
            "notes": "Empty response; no evidence provided.",
        }

    hedge_patterns = [
        r"\b(might|maybe|possibly|perhaps|it seems|likely|unlikely|presumably)\b",
        r"\b(in my opinion|i believe|i assume|presumably|supposedly)\b",
        r"\b(may vary|could be|to my knowledge|as far as i know)\b",
        r"\b(untested|theoretical|experimental|hypothetical)\b",
    ]

    hedge_phrases: List[str] = []
    for pat in hedge_patterns:
        matches = re.findall(pat, content, re.I)
        hedge_phrases.extend(matches)

    assumptions = identify_unsupported_assumptions(claims)
    numerical_claims = [c for c in claims if c.claim_type == "numerical"]
    factual_claims = [c for c in claims if c.claim_type == "factual"]

    # Compute empirical grounding
    total_claims = max(len(claims), 1)
    evidence_ratio = (len(numerical_claims) + len(factual_claims)) / total_claims

    if len(hedge_phrases) >= 6 or len(assumptions) >= 4 or evidence_ratio < 0.15:
        tier = "LOW EVIDENCE SUPPORT"
        score = 0.75
    elif len(hedge_phrases) >= 3 or len(assumptions) >= 2:
        tier = "MODERATE EVIDENCE SUPPORT"
        score = 0.45
    elif evidence_ratio >= 0.40 and len(hedge_phrases) <= 1:
        tier = "HIGH EVIDENCE SUPPORT"
        score = 0.15
    else:
        tier = "MODERATE EVIDENCE SUPPORT"
        score = 0.35

    return {
        "evidence_tier": tier,
        "uncertainty_score": score,
        "hedge_phrases_count": len(hedge_phrases),
        "hedge_phrases_sample": list(set(hedge_phrases))[:6],
        "unsupported_assumptions_count": len(assumptions),
        "unsupported_assumptions": assumptions,
        "substantiated_claims_count": len(numerical_claims) + len(factual_claims),
        "is_unverified": tier in ("LOW EVIDENCE SUPPORT", "INSUFFICIENT EVIDENCE"),
    }


def evaluate_evidence_coverage(claims: List[NormalizedClaim]) -> Dict[str, Any]:
    """Inspect proportion of claims that possess concrete verifiable anchors."""
    total = len(claims)
    if total == 0:
        return {"coverage": 0.0, "status": "NO_CLAIMS"}

    anchored = sum(1 for c in claims if c.claim_type in ("numerical", "factual") or len(c.supporting_evidence) > 0)
    coverage = round(anchored / total, 2)

    return {
        "total_claims": total,
        "anchored_claims": anchored,
        "coverage_ratio": coverage,
        "assessment": "SUFFICIENT" if coverage >= 0.4 else "WEAK",
    }


def identify_unsupported_assumptions(claims: List[NormalizedClaim]) -> List[str]:
    """Isolate explicit and implicit assumptions lacking direct proof."""
    assumptions: List[str] = []

    for c in claims:
        if c.claim_type == "assumption" or c.assumptions:
            assumptions.append(c.claim_text)
        elif any(k in c.claim_text.lower() for k in ("assuming that", "presuming", "if we consider", "given that")):
            assumptions.append(c.claim_text)

    return list(dict.fromkeys(assumptions))[:8]
