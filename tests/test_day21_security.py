"""
Day 21 Unit Tests — Word Automation Security & Permission Engine.
Verifies zero-trust policies, risk levels, confirmation gating on HIGH_RISK actions,
and unconditional blocking of CRITICAL actions (e.g., VBA macro execution).
"""

from __future__ import annotations

import unittest

from zye_office.word.word_errors import WordRevisionConfirmationRequiredError, WordSecurityError
from zye_office.word.word_permissions import (
    WordPermissionEngine,
    WordRiskLevel,
    WORD_OPERATION_RISK_MAP,
)


class TestDay21Security(unittest.TestCase):

    def test_risk_level_mapping(self) -> None:
        """Verify standard risk mappings across operation tiers."""
        self.assertEqual(
            WordPermissionEngine.get_risk_level("word.inspect_document"),
            WordRiskLevel.READ_ONLY,
        )
        self.assertEqual(
            WordPermissionEngine.get_risk_level("word.insert_text"),
            WordRiskLevel.LOW_RISK,
        )
        self.assertEqual(
            WordPermissionEngine.get_risk_level("word.create_table"),
            WordRiskLevel.MEDIUM_RISK,
        )
        self.assertEqual(
            WordPermissionEngine.get_risk_level("word.accept_all_revisions"),
            WordRiskLevel.HIGH_RISK,
        )
        self.assertEqual(
            WordPermissionEngine.get_risk_level("word.run_vba_macro"),
            WordRiskLevel.CRITICAL,
        )

    def test_critical_operation_strictly_blocked(self) -> None:
        """Verify CRITICAL operations (such as VBA macros) raise WordSecurityError unconditionally."""
        with self.assertRaises(WordSecurityError):
            WordPermissionEngine.verify_operation_allowed("word.run_vba_macro", confirmed=True)

        with self.assertRaises(WordSecurityError):
            WordPermissionEngine.verify_operation_allowed("word.execute_arbitrary_script", confirmed=True)

    def test_high_risk_requires_confirmation(self) -> None:
        """Verify HIGH_RISK operations require confirmed=True."""
        with self.assertRaises((WordRevisionConfirmationRequiredError, WordSecurityError)):
            WordPermissionEngine.verify_operation_allowed("word.accept_all_revisions", confirmed=False)

        # Passes with confirmed=True
        WordPermissionEngine.verify_operation_allowed("word.accept_all_revisions", confirmed=True)

    def test_low_and_medium_risk_allowed(self) -> None:
        """Verify LOW_RISK and MEDIUM_RISK operations are allowed without explicit confirmation."""
        WordPermissionEngine.verify_operation_allowed("word.insert_text", confirmed=False)
        WordPermissionEngine.verify_operation_allowed("word.create_table", confirmed=False)


if __name__ == "__main__":
    unittest.main()
