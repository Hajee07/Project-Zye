"""Consensus Analysis Engine for Zye AI Council.

Analyzes agreements, minority arguments, and shared perspectives:
- Distinguishes Full Agreement, Partial Agreement, No Agreement, and Contradictory.
- Protects against majority-voting fallacy (majority opinion != technical correctness).
- Isolates valuable minority edge cases that consensus might obscure.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set
from .claim_extractor import NormalizedClaim, compare_claims
from .disagreement_detector import DisagreementItem


def analyze_consensus(
    provider_claims: Dict[str, List[NormalizedClaim]],
    disagreements: List[DisagreementItem],
) -> Dict[str, Any]:
    """Evaluate degree of alignment and isolate shared vs minority arguments."""
    total_providers = len(provider_claims)
    if total_providers < 2:
        return {
            "consensus_status": "INSUFFICIENT_PARTICIPANTS",
            "agreement_score": 1.0 if total_providers == 1 else 0.0,
            "shared_points": [],
            "minority_positions": [],
            "unresolved_issues": [],
            "consensus_notes": "Single provider consulted; no multi-model consensus possible.",
        }

    shared_points: List[Dict[str, Any]] = []
    minority_positions: List[Dict[str, Any]] = []

    # Map of all claims per provider
    all_claims: List[NormalizedClaim] = []
    for p_id, c_list in provider_claims.items():
        all_claims.extend(c_list)

    # Detect shared concepts across providers
    clustered_claims: List[List[NormalizedClaim]] = []
    for c in all_claims:
        matched_cluster = False
        for cluster in clustered_claims:
            lead = cluster[0]
            cmp_res = compare_claims(lead, c)
            if cmp_res["is_same_topic"] and cmp_res["overlap_score"] >= 0.35 and not cmp_res["is_contradiction"]:
                cluster.append(c)
                matched_cluster = True
                break
        if not matched_cluster:
            clustered_claims.append([c])

    for cluster in clustered_claims:
        providers_in_cluster = list({c.provider_id for c in cluster})
        lead_claim = cluster[0]

        if len(providers_in_cluster) == total_providers:
            # Full consensus on this claim
            shared_points.append({
                "topic": lead_claim.topic,
                "summary": lead_claim.claim_text,
                "supporting_providers": providers_in_cluster,
                "consensus_level": "FULL",
            })
        elif len(providers_in_cluster) >= 2:
            # Majority / partial consensus
            shared_points.append({
                "topic": lead_claim.topic,
                "summary": lead_claim.claim_text,
                "supporting_providers": providers_in_cluster,
                "consensus_level": "PARTIAL",
            })
        elif len(providers_in_cluster) == 1:
            # Unique perspective or minority position
            minority_positions.append({
                "topic": lead_claim.topic,
                "summary": lead_claim.claim_text,
                "provider_id": providers_in_cluster[0],
                "claim_type": lead_claim.claim_type,
            })

    # Determine global consensus status
    if disagreements and any(d.severity in ("CRITICAL", "HIGH") for d in disagreements):
        status = "CONTRADICTORY_POSITIONS"
    elif len(shared_points) > 0 and len(minority_positions) == 0 and not disagreements:
        status = "FULL_AGREEMENT"
    elif len(shared_points) > 0:
        status = "PARTIAL_AGREEMENT"
    else:
        status = "NO_AGREEMENT"


    # Calculate agreement score
    denom = max(len(shared_points) + len(disagreements), 1)
    agreement_score = round(len(shared_points) / denom, 2)

    return {
        "consensus_status": status,
        "agreement_score": agreement_score,
        "shared_points_count": len(shared_points),
        "shared_points": shared_points,
        "minority_positions_count": len(minority_positions),
        "minority_positions": minority_positions,
        "critical_disagreements_count": len([d for d in disagreements if d.severity == "CRITICAL"]),
        "unresolved_issues": [d.explanation for d in disagreements[:5]],
        "signal_caveat": "Consensus reflects shared model heuristics and training overlap; not independent mathematical verification.",
    }
