"""
Mathematical Explainer & Voice Script Generator.
Synthesizes step-by-step derivation outlines, markdown reports, and bilingual Gemini Live voice responses.
"""

from __future__ import annotations

from typing import Any


class MathExplainer:
    """Generates step-by-step mathematical explanations and voice summaries."""

    @staticmethod
    def format_step_by_step_explanation(
        operation: str,
        input_problem: str,
        result: Any,
        intermediate_steps: list[str] | None = None,
        verification: dict[str, Any] | None = None,
    ) -> str:
        """Formats structured step-by-step derivation in Markdown."""
        lines = [
            f"### Mathematical Solution: {operation.replace('_', ' ').title()}",
            f"**Given:** `{input_problem}`\n",
            "**Steps:**",
        ]

        if intermediate_steps:
            for i, step in enumerate(intermediate_steps, 1):
                lines.append(f"{i}. {step}")
        else:
            lines.append(f"1. Applied canonical transformation for `{operation}`.")
            lines.append(f"2. Evaluated exact symbolic solution: `{result}`.")

        lines.append(f"\n**Final Result:** `{result}`")

        if verification and verification.get("verification_status"):
            st = verification["verification_status"]
            lines.append(f"\n**Verification Status:** `{st}` (Residual: {verification.get('residual', 0)})")

        return "\n".join(lines)

    @staticmethod
    def generate_voice_summaries(
        operation: str,
        input_problem: str,
        result: Any,
        verification_status: str | None = None,
    ) -> tuple[str, str]:
        """Generates concise bilingual (Tanglish & English) voice scripts for Gemini Live."""
        op_clean = operation.replace("_", " ").lower()
        res_str = str(result)
        if len(res_str) > 80:
            res_str = res_str[:77] + "..."

        ver_phrase_tan = " Result verify panniyachu." if verification_status in ("VERIFIED_EXACT", "VERIFIED_NUMERICALLY") else ""
        ver_phrase_en = " The solution has been verified." if verification_status in ("VERIFIED_EXACT", "VERIFIED_NUMERICALLY") else ""

        voice_tanglish = (
            f"Mathematical calculation mudinjidhu. {input_problem}-ku {op_clean} result: {res_str}.{ver_phrase_tan}"
        )
        voice_en = (
            f"Mathematical computation complete. The {op_clean} for {input_problem} is {res_str}.{ver_phrase_en}"
        )

        return voice_tanglish, voice_en
