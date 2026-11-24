"""
Unit tests for Self-Repair MCP Server & Diagnostics (Day 17).
Verifies error log ingestion, source code inspection, static AST validation,
cryptographic backup payload verification, and error telemetry queries.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from self_repair_mcp import (
    inspect_source_file,
    list_project_source_files,
    read_own_source_code,
    read_recent_error_logs,
    read_telemetry_errors,
    validate_source_syntax,
    verify_backup_payload,
)


class TestDay17SelfRepair(unittest.TestCase):

    def test_read_recent_error_logs(self) -> None:
        """Verify reading recent error logs returns structured JSON envelope."""
        res = read_recent_error_logs(lines=10)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("returned_lines", res.get("data", {}))

    def test_read_own_source_code(self) -> None:
        """Verify reading valid project source file."""
        res = read_own_source_code(filename="zye_guard.py", start_line=1, end_line=20)
        self.assertEqual(res.get("status"), "success")
        data = res.get("data", {})
        self.assertEqual(data.get("filename"), "zye_guard.py")
        self.assertIn("source_code", data)

    def test_list_project_source_files(self) -> None:
        """Verify listing eligible project Python files."""
        res = list_project_source_files(directory=".", recursive=False)
        self.assertEqual(res.get("status"), "success")
        files = res.get("data", {}).get("files", [])
        self.assertTrue(any("zye_guard.py" in f for f in files))

    def test_inspect_source_file(self) -> None:
        """Verify metadata and syntax inspection."""
        res = inspect_source_file(filename="zye_guard.py")
        self.assertEqual(res.get("status"), "success")
        data = res.get("data", {})
        self.assertEqual(data.get("source_validation_status"), "VALID_PYTHON")
        self.assertTrue(len(data.get("sha256", "")) == 64)

    def test_validate_source_syntax(self) -> None:
        """Verify Day 17 validate_source_syntax tool."""
        res = validate_source_syntax(filename="zye_guard.py")
        self.assertEqual(res.get("status"), "success")
        data = res.get("data", {})
        self.assertEqual(data.get("status"), "PASS")
        self.assertTrue(data.get("ast_valid"))
        self.assertTrue(data.get("compile_valid"))

    def test_verify_backup_payload_missing(self) -> None:
        """Verify checking non-existent backup payload returns error response."""
        res = verify_backup_payload(backup_id="nonexistent_id_9999")
        self.assertEqual(res.get("status"), "error")

    def test_read_telemetry_errors(self) -> None:
        """Verify Day 17 read_telemetry_errors tool."""
        res = read_telemetry_errors(last_n_minutes=60)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("total_errors", res.get("data", {}))


if __name__ == "__main__":
    unittest.main()
