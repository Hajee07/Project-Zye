"""Technical Correctness and Domain Evaluation Profiles for Zye AI Council.

Evaluates solution viability, reasoning coherence, architectural soundness,
and security across task-specific domain profiles:
- Software Development
- System Architecture
- Research & Factuality
- Engineering & Performance
- Business & Operations
- General Problem Solving
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from .claim_extractor import NormalizedClaim


EVALUATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "software_development": {
        "name": "Software Development",
        "criteria": [
            "syntax_correctness",
            "architecture_quality",
            "api_compatibility",
            "security",
            "performance",
            "maintainability",
            "test_coverage",
        ],
        "weights": {
            "syntax_correctness": 0.20,
            "architecture_quality": 0.20,
            "security": 0.20,
            "api_compatibility": 0.15,
            "performance": 0.10,
            "maintainability": 0.10,
            "test_coverage": 0.05,
        },
    },
    "system_architecture": {
        "name": "System Architecture",
        "criteria": [
            "reliability",
            "modularity",
            "scalability",
            "fault_tolerance",
            "resource_usage",
            "complexity",
            "integration_compatibility",
        ],
        "weights": {
            "reliability": 0.25,
            "scalability": 0.20,
            "fault_tolerance": 0.15,
            "modularity": 0.15,
            "integration_compatibility": 0.10,
            "resource_usage": 0.10,
            "complexity": 0.05,
        },
    },
    "research": {
        "name": "Research & Factuality",
        "criteria": [
            "evidence_quality",
            "source_reliability",
            "freshness",
            "completeness",
            "logical_consistency",
            "counterargument_handling",
        ],
        "weights": {
            "evidence_quality": 0.30,
            "source_reliability": 0.25,
            "logical_consistency": 0.20,
            "completeness": 0.15,
            "freshness": 0.10,
        },
    },
    "engineering": {
        "name": "Engineering & Safety",
        "criteria": [
            "technical_feasibility",
            "safety",
            "accuracy",
            "reliability",
            "material_constraints",
            "performance",
        ],
        "weights": {
            "safety": 0.30,
            "reliability": 0.25,
            "technical_feasibility": 0.20,
            "accuracy": 0.15,
            "performance": 0.10,
        },
    },
    "business": {
        "name": "Business & Strategy",
        "criteria": [
            "cost_efficiency",
            "feasibility",
            "risk_mitigation",
            "return_on_effort",
            "operational_impact",
            "long_term_sustainability",
        ],
        "weights": {
            "feasibility": 0.25,
            "risk_mitigation": 0.25,
            "cost_efficiency": 0.20,
            "operational_impact": 0.15,
            "long_term_sustainability": 0.15,
        },
    },
    "general": {
        "name": "General Problem Solving",
        "criteria": [
            "correctness",
            "completeness",
            "simplicity",
            "practicality",
            "reliability",
        ],
        "weights": {
            "correctness": 0.30,
            "practicality": 0.25,
            "reliability": 0.20,
            "completeness": 0.15,
            "simplicity": 0.10,
        },
    },
}


def get_evaluation_profile(profile_name: str) -> Dict[str, Any]:
    """Retrieve task profile schema and default weight matrix."""
    key = profile_name.lower().strip()
    return EVALUATION_PROFILES.get(key, EVALUATION_PROFILES["general"])


def evaluate_reasoning_quality(content: str) -> Dict[str, Any]:
    """Analyze structural coherence, argument progression, and counterargument handling."""
    if not content:
        return {"coherence_score": 0.0, "has_structure": False, "caveats_considered": False}

    has_code_block = "```" in content
    has_headers = bool(re.search(r"^#{1,3}\s+", content, re.M))
    has_bullets = bool(re.search(r"^[-*]\s+", content, re.M))
    has_tradeoffs = bool(re.search(r"\b(tradeoff|pros and cons|however|alternatively|limitation|drawback)\b", content, re.I))
    has_error_handling = bool(re.search(r"\b(try|except|catch|fallback|timeout|validation|error handling)\b", content, re.I))

    score = 0.5
    if has_headers or has_bullets:
        score += 0.2
    if has_tradeoffs:
        score += 0.2
    if has_code_block and has_error_handling:
        score += 0.1

    return {
        "coherence_score": round(min(score, 1.0), 2),
        "has_structure": (has_headers or has_bullets),
        "considers_tradeoffs": has_tradeoffs,
        "considers_error_handling": has_error_handling,
    }


def evaluate_security_risks(content: str) -> Dict[str, Any]:
    """Inspect proposed solution for security vulnerabilities, secrets, and dangerous primitives."""
    risks_detected: List[str] = []

    dangerous_patterns = [
        (r"\beval\s*\(", "Use of dynamic code evaluation (eval)"),
        (r"\bexec\s*\(", "Use of dynamic code execution (exec)"),
        (r"\bos\.system\s*\(", "Unsanitized system shell invocation (os.system)"),
        (r"\bsubprocess\.Popen\(.*shell\s*=\s*True", "Shell injection vulnerability (shell=True)"),
        (r"chmod\s+777", "Insecure file permissions (chmod 777)"),
        (r"verify\s*=\s*False", "Disabled SSL/TLS certificate verification"),
        (r"allow_all_origins\s*=\s*True", "Permissive CORS wildcard"),
    ]

    for pat, desc in dangerous_patterns:
        if re.search(pat, content):
            risks_detected.append(desc)

    return {
        "security_score": 1.0 if not risks_detected else max(0.2, 1.0 - (0.25 * len(risks_detected))),
        "has_critical_risks": len(risks_detected) > 0,
        "risks": risks_detected,
    }


def evaluate_technical_claims(
    claims: List[NormalizedClaim],
    profile: str = "general",
) -> Dict[str, Any]:
    """Evaluate extracted claims against selected profile criteria."""
    prof = get_evaluation_profile(profile)
    claims_count = len(claims)

    numerical_count = sum(1 for c in claims if c.claim_type == "numerical")
    factual_count = sum(1 for c in claims if c.claim_type == "factual")
    assumption_count = sum(1 for c in claims if c.claim_type == "assumption")
    recommendation_count = sum(1 for c in claims if c.claim_type == "recommendation")

    # Ratio of substantiated assertions
    substantiated_ratio = (numerical_count + factual_count) / max(claims_count, 1)

    return {
        "profile_applied": prof["name"],
        "total_claims_evaluated": claims_count,
        "numerical_assertions": numerical_count,
        "factual_assertions": factual_count,
        "unsubstantiated_assumptions": assumption_count,
        "recommendations": recommendation_count,
        "substantiation_ratio": round(substantiated_ratio, 2),
        "criteria": prof["criteria"],
    }
