"""
Permission & Risk Classification Engine for Word Automation — Zye Day 21.
Enforces zero-trust execution policies, confirmation gates, and risk tier categorization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from zye_office.word.word_errors import WordSecurityError


class WordRiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


WORD_OPERATION_RISK_MAP: Dict[str, WordRiskLevel] = {
    # READ_ONLY
    "word.inspect_document": WordRiskLevel.READ_ONLY,
    "word.get_document_metadata": WordRiskLevel.READ_ONLY,
    "word.get_statistics": WordRiskLevel.READ_ONLY,
    "word.get_available_styles": WordRiskLevel.READ_ONLY,
    "word.inspect_toc": WordRiskLevel.READ_ONLY,
    "word.get_hyperlinks": WordRiskLevel.READ_ONLY,
    "word.get_bookmarks": WordRiskLevel.READ_ONLY,
    "word.get_track_changes_status": WordRiskLevel.READ_ONLY,
    "word.get_revisions": WordRiskLevel.READ_ONLY,
    "word.get_comments": WordRiskLevel.READ_ONLY,
    "word.inspect_mail_merge": WordRiskLevel.READ_ONLY,
    "word.preview_merge_record": WordRiskLevel.READ_ONLY,
    "word.inspect_accessibility": WordRiskLevel.READ_ONLY,
    "word.generate_accessibility_report": WordRiskLevel.READ_ONLY,

    # LOW_RISK
    "word.insert_text": WordRiskLevel.LOW_RISK,
    "word.insert_paragraph": WordRiskLevel.LOW_RISK,
    "word.insert_heading": WordRiskLevel.LOW_RISK,
    "word.apply_style": WordRiskLevel.LOW_RISK,
    "word.format_text": WordRiskLevel.LOW_RISK,
    "word.format_paragraph": WordRiskLevel.LOW_RISK,
    "word.set_document_properties": WordRiskLevel.LOW_RISK,
    "word.create_bookmark": WordRiskLevel.LOW_RISK,
    "word.insert_hyperlink": WordRiskLevel.LOW_RISK,
    "word.set_track_changes": WordRiskLevel.LOW_RISK,
    "word.add_comment": WordRiskLevel.LOW_RISK,
    "word.resolve_comment": WordRiskLevel.LOW_RISK,
    "word.create_bullet_list": WordRiskLevel.LOW_RISK,
    "word.create_numbered_list": WordRiskLevel.LOW_RISK,
    "word.save_document": WordRiskLevel.LOW_RISK,
    "word.create_document": WordRiskLevel.LOW_RISK,
    "word.open_document": WordRiskLevel.LOW_RISK,

    # MEDIUM_RISK
    "word.save_document_as": WordRiskLevel.MEDIUM_RISK,
    "word.close_document": WordRiskLevel.MEDIUM_RISK,
    "word.create_table": WordRiskLevel.MEDIUM_RISK,
    "word.populate_table": WordRiskLevel.MEDIUM_RISK,
    "word.format_table": WordRiskLevel.MEDIUM_RISK,
    "word.add_table_row": WordRiskLevel.MEDIUM_RISK,
    "word.delete_table_row": WordRiskLevel.MEDIUM_RISK,
    "word.set_header": WordRiskLevel.MEDIUM_RISK,
    "word.set_footer": WordRiskLevel.MEDIUM_RISK,
    "word.insert_page_numbers": WordRiskLevel.MEDIUM_RISK,
    "word.set_page_orientation": WordRiskLevel.MEDIUM_RISK,
    "word.set_page_margins": WordRiskLevel.MEDIUM_RISK,
    "word.set_paper_size": WordRiskLevel.MEDIUM_RISK,
    "word.insert_page_break": WordRiskLevel.MEDIUM_RISK,
    "word.insert_section_break": WordRiskLevel.MEDIUM_RISK,
    "word.insert_toc": WordRiskLevel.MEDIUM_RISK,
    "word.update_toc": WordRiskLevel.MEDIUM_RISK,
    "word.accept_revision": WordRiskLevel.MEDIUM_RISK,
    "word.reject_revision": WordRiskLevel.MEDIUM_RISK,
    "word.connect_merge_source": WordRiskLevel.MEDIUM_RISK,
    "word.export_pdf_advanced": WordRiskLevel.MEDIUM_RISK,
    "word.create_custom_style": WordRiskLevel.MEDIUM_RISK,

    # HIGH_RISK (Requires explicit confirmation)
    "word.delete_selected_text": WordRiskLevel.HIGH_RISK,
    "word.replace_text": WordRiskLevel.HIGH_RISK,
    "word.accept_all_revisions": WordRiskLevel.HIGH_RISK,
    "word.reject_all_revisions": WordRiskLevel.HIGH_RISK,
    "word.execute_mail_merge": WordRiskLevel.HIGH_RISK,
    "word.delete_table": WordRiskLevel.HIGH_RISK,

    # CRITICAL (Forbidden / Blocked by default)
    "word.run_vba_macro": WordRiskLevel.CRITICAL,
    "word.execute_arbitrary_script": WordRiskLevel.CRITICAL,
    "word.auto_send_email": WordRiskLevel.CRITICAL,
}


class WordPermissionEngine:
    """Verifies authorization, risk level, and confirmation gates before execution."""

    @staticmethod
    def get_risk_level(operation_id: str) -> WordRiskLevel:
        return WORD_OPERATION_RISK_MAP.get(operation_id, WordRiskLevel.HIGH_RISK)

    @staticmethod
    def requires_confirmation(operation_id: str) -> bool:
        risk = WordPermissionEngine.get_risk_level(operation_id)
        return risk in (WordRiskLevel.HIGH_RISK, WordRiskLevel.CRITICAL)

    @staticmethod
    def enforce_gate(operation_id: str, confirmed: bool = False) -> None:
        if operation_id in ("word.run_vba_macro", "word.execute_arbitrary_script", "word.auto_send_email"):
            raise WordSecurityError(
                code="WORD_MACRO_EXECUTION_BLOCKED",
                message=f"Operation '{operation_id}' is permanently prohibited by Zye Zero-Trust Security Policy.",
            )

        if WordPermissionEngine.requires_confirmation(operation_id) and not confirmed:
            raise WordSecurityError(
                code="WORD_CONFIRMATION_REQUIRED",
                message=f"Operation '{operation_id}' is classified as HIGH_RISK and requires explicit user confirmation.",
            )

    verify_operation_allowed = enforce_gate
