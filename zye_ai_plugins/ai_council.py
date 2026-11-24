"""Advanced Multi-AI Council Intelligence Engine for Zye AI (Day 26).

Coordinates multi-agent independent analysis, cross-examination, disagreement detection,
consensus evaluation, weighted decision analysis, and Gemini Master Brain supreme synthesis.

Operating Modes:
- QUICK_COUNCIL: Fast parallel independent analysis between ChatGPT & Claude
- DEEP_COUNCIL: Multi-round debate, claim extraction, cross-critique, and decision ranking
- LOCAL_COUNCIL: 100% offline, privacy-first local Ollama deliberation

Supreme Arbiter:
- Google Gemini alone renders the authoritative final verdict.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Union

from .claim_extractor import (
    NormalizedClaim,
    classify_claims,
    extract_response_claims,
    normalize_claims,
)
from .consensus_analyzer import analyze_consensus
from .council_evaluator import (
    evaluate_reasoning_quality,
    evaluate_security_risks,
    evaluate_technical_claims,
    get_evaluation_profile,
)
from .council_report import generate_ai_council_report, save_ai_council_report
from .decision_engine import rank_candidate_solutions
from .disagreement_detector import detect_disagreements, generate_disagreement_report
from .evidence_analyzer import analyze_answer_uncertainty, evaluate_evidence_coverage
from .plugin_security import sanitize_prompt
from .response_normalizer import AIResponse

logger = logging.getLogger("zye.ai_plugins.council")


class AICouncilEngine:
    """Advanced Multi-AI Council Orchestrator."""

    def __init__(self, registry: Any):
        self.registry = registry
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def get_council_status(self) -> Dict[str, Any]:
        """Check readiness of all potential Council members and quorum status."""
        active_providers = self.registry.get_active_providers()
        available_members = []
        unconfigured_members = []

        standard_council = ["chatgpt", "claude", "ollama", "perplexity", "deepseek", "groq", "openrouter"]
        for pid in standard_council:
            provider = self.registry.get_provider(pid)
            if provider and provider.is_configured and provider.config.enabled:
                available_members.append({
                    "provider_id": pid,
                    "model": provider.config.default_model,
                    "is_local": getattr(provider, "allow_loopback", False),
                })
            else:
                unconfigured_members.append(pid)

        return {
            "council_ready": len(available_members) >= 1,
            "min_members_for_comparison": 2,
            "has_multimodal_consensus": len(available_members) >= 2,
            "active_members_count": len(available_members),
            "available_members": available_members,
            "unconfigured_members": unconfigured_members,
            "supreme_arbiter": "Gemini Master Brain (Voice: en-IN-NeerjaNeural)",
            "supported_modes": ["QUICK_COUNCIL", "DEEP_COUNCIL", "LOCAL_COUNCIL"],
            "supported_priority_modes": [
                "BALANCED", "SPEED_CRITICAL", "MAXIMUM_SAFETY",
                "LOW_RESOURCE", "HIGH_RELIABILITY", "MAINTAINABILITY_FIRST", "USER_CUSTOM"
            ],
        }

    # =========================================================================
    # 1. Round 1 — Independent AI Analysis
    # =========================================================================

    async def _run_independent_round(
        self,
        question: str,
        target_providers: List[str],
        focus_area: str = "general",
        context: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> Dict[str, AIResponse]:
        """Query each provider independently with zero exposure to peer outputs."""
        focus_instructions = {
            "general": "Provide a rigorous, independent, and logically structured analysis of the problem.",
            "code": "Focus on optimal software engineering, syntax correctness, typing, safety, and performance.",
            "security": "Perform a strict security, threat modeling, and vulnerability analysis of the problem.",
            "architecture": "Evaluate modularity, scalability, fault tolerance, resource limits, and operational complexity.",
            "creative": "Offer innovative, divergent, and unorthodox perspectives and alternative approaches.",
            "fact_check": "Provide strict factual verification, citing verifiable premises and empirical evidence.",
        }
        base_instruction = focus_instructions.get(focus_area, focus_instructions["general"])
        system_instruction = f"{base_instruction}\nContext:\n{context}" if context else base_instruction

        tasks = []
        valid_pids = []
        for pid in target_providers:
            provider = self.registry.get_provider(pid)
            if provider:
                valid_pids.append(pid)
                tasks.append(
                    provider.generate_response(
                        prompt=question,
                        system_prompt=system_instruction,
                        max_tokens=max_tokens,
                    )
                )

        if not tasks:
            return {}

        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses: Dict[str, AIResponse] = {}

        for pid, res in zip(valid_pids, results):
            if isinstance(res, Exception):
                responses[pid] = AIResponse(
                    provider_id=pid,
                    model="unknown",
                    status="error",
                    error_message=str(res),
                )
            elif isinstance(res, AIResponse):
                responses[pid] = res
            else:
                responses[pid] = AIResponse(
                    provider_id=pid,
                    model="unknown",
                    status="unknown",
                    content=str(res),
                )

        return responses

    # =========================================================================
    # 2. Round 2 — Cross-AI Critique & Challenge Engine
    # =========================================================================

    async def _run_cross_review_round(
        self,
        question: str,
        round1_responses: Dict[str, AIResponse],
        max_tokens: int = 1024,
    ) -> Dict[str, AIResponse]:
        """Present peer proposals to each model and gather technical critiques."""
        critique_tasks = []
        critique_pids = []

        active_successful = {pid: resp for pid, resp in round1_responses.items() if resp.is_success and resp.content}
        if len(active_successful) < 2:
            return {}  # Cross-critique requires at least 2 distinct successful proposals

        for reviewer_pid, reviewer_resp in active_successful.items():
            provider = self.registry.get_provider(reviewer_pid)
            if not provider:
                continue

            # Format peers' proposals
            peer_blocks = []
            for peer_pid, peer_resp in active_successful.items():
                if peer_pid != reviewer_pid:
                    peer_blocks.append(f"[{peer_pid.upper()} PROPOSAL]:\n{peer_resp.content}\n")

            prompt = (
                f"Original Problem: {question}\n\n"
                f"Your Initial Proposal ({reviewer_pid}):\n{reviewer_resp.content}\n\n"
                f"Peer Proposals:\n" + "\n".join(peer_blocks) + "\n\n"
                "Task: Objectively critique the peer proposals above.\n"
                "1. Identify technical errors or questionable assumptions in peer answers.\n"
                "2. Identify any superior arguments or edge cases in peer answers that your answer omitted.\n"
                "3. State your refined position and defend why your approach is optimal or how it should be modified."
            )

            critique_pids.append(reviewer_pid)
            critique_tasks.append(
                provider.generate_response(
                    prompt=prompt,
                    system_prompt="You are an expert peer reviewer. Identify technical flaws and defend optimal architecture.",
                    max_tokens=max_tokens,
                )
            )

        results = await asyncio.gather(*critique_tasks, return_exceptions=True)
        critique_responses: Dict[str, AIResponse] = {}

        for pid, res in zip(critique_pids, results):
            if isinstance(res, AIResponse):
                critique_responses[pid] = res
            elif isinstance(res, Exception):
                critique_responses[pid] = AIResponse(
                    provider_id=pid,
                    model="unknown",
                    status="error",
                    error_message=str(res),
                )

        return critique_responses

    # =========================================================================
    # 3. Main Council Orchestrator (Quick, Deep, Local)
    # =========================================================================

    async def run_ai_council(
        self,
        question: str,
        providers: Optional[List[str]] = None,
        council_mode: str = "quick",
        priority_mode: str = "balanced",
        max_rounds: int = 1,
        evaluation_profile: str = "general",
        custom_weights: Optional[Dict[str, float]] = None,
        context: Optional[str] = None,
        privacy_mode: bool = False,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Execute full multi-AI Council deliberation session."""
        start_time = time.perf_counter()
        council_id = f"council_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        mode = council_mode.lower().strip()

        # Enforce local privacy mode
        if privacy_mode or mode in ("local", "local_council"):
            mode = "local_council"
            target_providers = ["ollama"]
            logger.info("Executing Council in LOCAL-ONLY mode (Privacy Guard Active).")
        else:
            target_providers = providers or ["chatgpt", "claude"]
            if isinstance(target_providers, str):
                target_providers = [p.strip() for p in target_providers.split(",")]

        # Step 1: Independent Analysis Round
        r1_responses = await self._run_independent_round(
            question=question,
            target_providers=target_providers,
            focus_area=evaluation_profile,
            context=context,
            max_tokens=max_tokens,
        )

        participants = []
        provider_claims: Dict[str, List[NormalizedClaim]] = {}
        candidate_solutions: Dict[str, Dict[str, Any]] = {}

        for pid, resp in r1_responses.items():
            p_data = {
                "provider_id": pid,
                "model": resp.model_used,
                "status": resp.status,
                "content": resp.content,
                "latency_ms": resp.usage.latency_ms,
                "usage": resp.usage.model_dump(),
                "error": resp.error_message,
            }
            participants.append(p_data)

            if resp.is_success and resp.content:
                # Step 2: Claim Extraction & Normalization
                claims = extract_response_claims(pid, resp.content)
                provider_claims[pid] = normalize_claims(claims)

                # Formulate candidate solution for Decision Engine
                reasoning_meta = evaluate_reasoning_quality(resp.content)
                sec_meta = evaluate_security_risks(resp.content)

                candidate_solutions[pid] = {
                    "title": f"{pid.capitalize()} Architecture Proposal",
                    "provider_id": pid,
                    "scores": {
                        "correctness": reasoning_meta["coherence_score"],
                        "reliability": 0.85 if reasoning_meta["has_structure"] else 0.6,
                        "safety": sec_meta["security_score"],
                        "performance": 0.85 if any(c.topic == "performance" for c in claims) else 0.7,
                        "maintainability": 0.9 if reasoning_meta["considers_tradeoffs"] else 0.65,
                        "simplicity": 0.8 if len(claims) <= 10 else 0.65,
                        "compatibility": 0.85,
                        "resource_efficiency": 0.9 if pid == "ollama" else 0.75,
                        "fault_tolerance": 0.85 if reasoning_meta["considers_error_handling"] else 0.6,
                    },
                    "pros": [c.claim_text for c in claims if c.claim_type == "recommendation"][:3],
                    "cons": [f"Assumes: {c.claim_text}" for c in claims if c.claim_type == "assumption"][:2],
                    "risks": sec_meta["risks"],
                }

        # Step 3: Multi-Round Cross-Critique (for Deep Council)
        critiques: Dict[str, Any] = {}
        if mode == "deep_council" and max_rounds >= 2 and len(candidate_solutions) >= 2:
            logger.info("Convening Round 2: Cross-AI Critique for Deep Council.")
            r2_responses = await self._run_cross_review_round(
                question=question,
                round1_responses=r1_responses,
                max_tokens=max_tokens,
            )
            for r_pid, r_resp in r2_responses.items():
                if r_resp.is_success:
                    critiques[r_pid] = r_resp.content

        # Step 4: Disagreement Detection
        disagreements = detect_disagreements(provider_claims)
        disagreement_summary = generate_disagreement_report(disagreements)

        # Step 5: Consensus Analysis
        consensus_summary = analyze_consensus(provider_claims, disagreements)

        # Step 6: Decision Engine Multi-Criteria Ranking
        decision_results = rank_candidate_solutions(
            candidate_solutions=candidate_solutions,
            priority_mode=priority_mode,
            custom_weights=custom_weights,
        )

        # Step 7: Evidence & Uncertainty Analysis
        evidence_summary: Dict[str, Any] = {}
        for pid, claims in provider_claims.items():
            content = r1_responses[pid].content
            unc = analyze_answer_uncertainty(content, claims)
            cov = evaluate_evidence_coverage(claims)
            evidence_summary[pid] = {
                "uncertainty": unc,
                "coverage": cov,
            }

        # Step 8: Gemini Supreme Arbiter Final Synthesis
        synthesis_prompt = self._build_gemini_synthesis_prompt(
            question=question,
            participants=participants,
            disagreements=disagreements,
            consensus=consensus_summary,
            decision=decision_results,
            critiques=critiques,
        )

        # Determine default verdict categorization
        best_sol = decision_results.get("recommended_solution")
        score_diff = decision_results.get("score_separation", 1.0)
        has_critical_sec = disagreement_summary.get("critical_count", 0) > 0

        if has_critical_sec:
            verdict_cat = "ALL_CANDIDATES_UNSAFE_OR_UNSUITABLE"
        elif len(candidate_solutions) < 2:
            verdict_cat = "RECOMMENDED_SOLUTION_A"
        elif score_diff < 0.05:
            verdict_cat = "HYBRID_SOLUTION"
        elif best_sol == "chatgpt":
            verdict_cat = "RECOMMENDED_SOLUTION_A"
        elif best_sol == "claude":
            verdict_cat = "RECOMMENDED_SOLUTION_B"
        else:
            verdict_cat = "HYBRID_SOLUTION"

        final_decision = {
            "verdict_category": verdict_cat,
            "selected_solution": f"{best_sol.capitalize()} Architecture Path" if best_sol else "Hybrid Synthesis",
            "reasoning": [
                f"Multi-criteria decision analysis scored top candidate at {decision_results.get('top_score')}.",
                f"Consensus status resolved as {consensus_summary.get('consensus_status')}.",
                f"Disagreements identified: {len(disagreements)} ({disagreement_summary.get('critical_count')} critical).",
            ],
            "unresolved_risks": [d.explanation for d in disagreements[:3]],
            "supreme_arbiter": "Gemini Master Brain (Authoritative Verdict Ready)",
        }

        total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        session_record = {
            "council_id": council_id,
            "mode": mode.upper(),
            "status": "completed" if candidate_solutions else "failed",
            "success": bool(candidate_solutions),
            "question": question,
            "total_queried": len(target_providers),
            "successful_count": len(candidate_solutions),
            "execution_time_ms": total_latency_ms,
            "participants": participants,
            "perspectives": {p["provider_id"]: p for p in participants},
            "comparison": {
                "agreements": consensus_summary.get("shared_points", []),
                "disagreements": [d.to_dict() for d in disagreements],
                "minority_arguments": consensus_summary.get("minority_positions", []),
            },
            "consensus": consensus_summary,
            "evaluation": decision_results,
            "evidence": evidence_summary,
            "cross_critiques": critiques,
            "final_decision": final_decision,
            "synthesis_prompt_ready": synthesis_prompt,
        }

        # Cache session in memory
        self._sessions[council_id] = session_record
        # Save session to reports directory
        save_ai_council_report(session_record)

        return session_record

    # Convenience API aliases
    async def run_quick_council(self, question: str, providers: Optional[List[str]] = None, timeout: float = 45.0) -> Dict[str, Any]:
        """Convenience method for Quick Council (ChatGPT + Claude independent comparison)."""
        return await self.run_ai_council(
            question=question,
            providers=providers or ["chatgpt", "claude"],
            council_mode="quick",
            priority_mode="balanced",
            max_rounds=1,
        )

    async def run_deep_council(
        self,
        question: str,
        providers: Optional[List[str]] = None,
        max_rounds: int = 2,
        priority_mode: str = "balanced",
        evaluation_criteria: str = "general",
        timeout: float = 90.0,
    ) -> Dict[str, Any]:
        """Convenience method for Deep Council (Multi-round debate & decision ranking)."""
        return await self.run_ai_council(
            question=question,
            providers=providers or ["chatgpt", "claude"],
            council_mode="deep_council",
            priority_mode=priority_mode,
            max_rounds=max_rounds,
            evaluation_profile=evaluation_criteria,
        )

    async def deliberate(
        self,
        question: str,
        providers: Optional[List[str]] = None,
        focus_area: Optional[str] = None,
        context: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Day 25 backward-compatibility bridge forwarding to run_ai_council."""
        return await self.run_ai_council(
            question=question,
            providers=providers,
            context=context,
            max_tokens=max_tokens,
            evaluation_profile=focus_area or "general",
        )

    def get_council_report(self, council_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve completed Council report by ID."""
        return self._sessions.get(council_id)

    def cancel_council(self, council_id: str) -> Dict[str, Any]:
        """Cancel a running Council session."""
        task = self._active_tasks.get(council_id)
        if task and not task.done():
            task.cancel()
            return {"success": True, "council_id": council_id, "status": "CANCELLED"}
        return {"success": False, "council_id": council_id, "message": "Session not active or already finished"}

    def _build_gemini_synthesis_prompt(
        self,
        question: str,
        participants: List[Dict[str, Any]],
        disagreements: List[Any],
        consensus: Dict[str, Any],
        decision: Dict[str, Any],
        critiques: Dict[str, Any],
    ) -> str:
        """Format the complete council deliberation dossier for Gemini Master Brain."""
        blocks = [
            "=== AI COUNCIL SUPREME ARBITER DOSSIER ===",
            f"Original Question: {question}",
            f"Council Quorum: {len(participants)} models queried.",
            "",
            "--- INDEPENDENT MODEL PROPOSALS ---",
        ]

        for p in participants:
            if p["status"] == "success":
                blocks.append(
                    f"\n[{p['provider_id'].upper()} (Model: {p['model']}, Latency: {p['latency_ms']}ms) - {p['provider_id'].capitalize()} recommendation]:\n{p['content']}\n"
                )
            else:
                blocks.append(f"\n[{p['provider_id'].upper()}]: FAILED ({p.get('error')})\n")

        if critiques:
            blocks.append("\n--- CROSS-EXAMINATION & CRITIQUES ---")
            for c_pid, c_text in critiques.items():
                blocks.append(f"\n[{c_pid.upper()} PEER CRITIQUE]:\n{c_text}\n")

        blocks.append("\n--- DISAGREEMENT MATRIX ---")
        if disagreements:
            for d in disagreements[:5]:
                blocks.append(f"- [{getattr(d, 'severity', 'MED')}] {getattr(d, 'topic', '')}: {getattr(d, 'explanation', '')}")
        else:
            blocks.append("No critical contradictions detected.")

        blocks.append("\n--- MULTI-CRITERIA DECISION SCORING ---")
        for r in decision.get("ranked_solutions", []):
            blocks.append(f"- Rank {r.get('rank')}: {r.get('title')} (Composite Score: {r.get('composite_score')})")

        blocks.append(
            "\n--- SUPREME ARBITER INSTRUCTIONS FOR GEMINI MASTER BRAIN ---\n"
            "Gemini Master Brain is the Supreme Arbiter and sole voice of Zye AI. Review the independent proposals, "
            "cross-critiques, and decision ranking above. Reconcile technical disagreements, reject false "
            "premises, and synthesize the definitive, authoritative recommendation for the user. Speak the final "
            "verdict directly via Edge-TTS (en-IN-NeerjaNeural)."
        )

        return "\n".join(blocks)
