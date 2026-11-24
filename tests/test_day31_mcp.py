"""
Tests for Day 31 Computer Intelligence FastMCP Server and Tool Dispatching.
"""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import time

import computer_intelligence_mcp
from zye_computer_intelligence.security.resource_policy import JobManager


class TestDay31MCP(unittest.TestCase):
    """Verifies MCP tool registration, dispatcher routing, and basic invocation."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_test_mcp_"))
        self.sample_csv = self.temp_dir / "sample.csv"
        self.sample_csv.write_text(
            "id,item,price,quantity\n"
            "1,Widget A,10.5,5\n"
            "2,Widget B,20.0,2\n"
            "3,Widget C,15.0,4\n",
            encoding="utf-8"
        )

    def tearDown(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_all_11_tools_registered(self):
        """Verifies that all 11 required FastMCP tools are registered."""
        tools = getattr(computer_intelligence_mcp.mcp, "_tools", None)
        if tools is None and hasattr(computer_intelligence_mcp.mcp, "_tool_manager"):
            tools = getattr(computer_intelligence_mcp.mcp._tool_manager, "_tools", None)

        tool_names = set(tools.keys()) if tools else set()
        expected = {
            "inspect_dataset_schema",
            "profile_large_dataset",
            "analyze_large_dataset",
            "calculate_dataset_correlations",
            "aggregate_dataset_by_group",
            "analyze_dataset_trends",
            "detect_dataset_outliers",
            "compare_dataset_segments",
            "get_dataset_analysis_status",
            "cancel_dataset_analysis",
            "get_dataset_analysis_report",
        }
        self.assertTrue(expected.issubset(tool_names), f"Missing tools: {expected - tool_names}")
        self.assertGreaterEqual(len(tool_names), 11)

    def test_02_inspect_dataset_schema_tool(self):
        """Tests inspect_dataset_schema FastMCP tool."""
        res = computer_intelligence_mcp.inspect_dataset_schema(str(self.sample_csv))
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["row_count"], 3)
        self.assertEqual(res["column_count"], 4)
        self.assertIn("price", res["numeric_columns"])

    def test_03_profile_large_dataset_tool(self):
        """Tests profile_large_dataset FastMCP tool."""
        res = computer_intelligence_mcp.profile_large_dataset(str(self.sample_csv))
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("markdown", res)
        self.assertIn("voice_tanglish", res)
        self.assertIn("voice_en", res)
        self.assertEqual(res["dataset"]["rows"], 3)

    def test_04_job_lifecycle_tools(self):
        """Tests job creation, status lookup, and cancellation."""
        jm = JobManager()
        job = jm.create_job(str(self.sample_csv), "CORRELATION_MATRIX")
        self.assertEqual(job.status, "QUEUED")

        st = computer_intelligence_mcp.get_dataset_analysis_status(job.job_id)
        self.assertEqual(st["status"], "SUCCESS")
        self.assertEqual(st["job_status"], "QUEUED")

        canc = computer_intelligence_mcp.cancel_dataset_analysis(job.job_id)
        self.assertEqual(canc["status"], "SUCCESS")
        self.assertEqual(job.status, "CANCELLED")

        # Unknown job
        bad = computer_intelligence_mcp.get_dataset_analysis_status("job_nonexistent")
        self.assertEqual(bad["status"], "ERROR")
        self.assertEqual(bad["error_code"], "JOB_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
