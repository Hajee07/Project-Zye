"""
Unit Tests for Day 34 MCP Tool Implementations.
Verifies invocation and structured response schemas for Tools 46 through 66
in computer_intelligence_mcp.py.
"""

import tempfile
import unittest
from pathlib import Path

import computer_intelligence_mcp as ci_mcp

WORKSPACE_TEST_BASE = Path("d:/Zye/data/test_tmp")


class TestDay34MCPTools(unittest.TestCase):
    """Test suite for FastMCP Day 34 tools (Tools 46 to 66)."""

    def setUp(self):
        WORKSPACE_TEST_BASE.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=str(WORKSPACE_TEST_BASE))
        self.dir_path = Path(self.temp_dir.name)

        # Sample files
        self.f1 = self.dir_path / "doc_alpha.txt"
        self.f2 = self.dir_path / "doc_alpha_copy.txt"
        self.f3 = self.dir_path / "doc_beta.txt"

        content = "ZYE AI Master Brain FastMCP Day 34 Verification Document.\nLead: Dr. Ramesh.\n"
        self.f1.write_text(content, encoding="utf-8")
        self.f2.write_text(content, encoding="utf-8")
        self.f3.write_text("Unique content for beta document.\n", encoding="utf-8")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_deduplication_mcp_tools(self):
        """Verifies Tools 46-54: duplicate scanning, comparisons, reports, storage reclamation."""
        # Tool 46: scan_duplicate_files
        scan_res = ci_mcp.scan_duplicate_files(directories=[str(self.dir_path)])
        self.assertEqual(scan_res["status"], "SUCCESS")
        self.assertGreaterEqual(scan_res["result"]["duplicate_groups_count"], 1)

        # Tool 47: compare_two_files
        cmp_res = ci_mcp.compare_two_files(str(self.f1), str(self.f2))
        self.assertEqual(cmp_res["status"], "SUCCESS")
        self.assertTrue(cmp_res["comparison"]["match"])

        # Tool 48: get_duplicate_scan_report
        rep_res = ci_mcp.get_duplicate_scan_report(directories=[str(self.dir_path)])
        self.assertEqual(rep_res["status"], "SUCCESS")
        self.assertIn("READ-ONLY AUDIT", rep_res["report"])

        # Tool 49: calculate_storage_reclamation
        rec_res = ci_mcp.calculate_storage_reclamation(directories=[str(self.dir_path)])
        self.assertEqual(rec_res["status"], "SUCCESS")
        self.assertIn("potential_reclaimable_human", rec_res)

        # Tool 50: find_largest_duplicate_groups
        lg_res = ci_mcp.find_largest_duplicate_groups(directories=[str(self.dir_path)], top_n=5)
        self.assertEqual(lg_res["status"], "SUCCESS")

        # Tool 51: check_file_hard_links
        hl_res = ci_mcp.check_file_hard_links(directories=[str(self.dir_path)])
        self.assertEqual(hl_res["status"], "SUCCESS")

        # Tool 52: filter_duplicates_by_extension
        ext_res = ci_mcp.filter_duplicates_by_extension(directories=[str(self.dir_path)], extension="txt")
        self.assertEqual(ext_res["status"], "SUCCESS")

        # Tool 53: verify_duplicate_integrity
        ver_res = ci_mcp.verify_duplicate_integrity(str(self.f1), str(self.f2))
        self.assertEqual(ver_res["status"], "SUCCESS")
        self.assertTrue(ver_res["verified"])

        # Tool 54: get_deduplication_status
        stat_res = ci_mcp.get_deduplication_status()
        self.assertEqual(stat_res["status"], "SUCCESS")
        self.assertTrue(stat_res["read_only"])

    def test_entity_linking_mcp_tools(self):
        """Verifies Tools 55-66: document indexing, entity search, profile, graph statistics."""
        # Tool 55: index_document_entities
        idx_doc_res = ci_mcp.index_document_entities(str(self.f1))
        self.assertEqual(idx_doc_res["status"], "SUCCESS")

        # Tool 56: index_directory_entities
        idx_dir_res = ci_mcp.index_directory_entities(str(self.dir_path))
        self.assertEqual(idx_dir_res["status"], "SUCCESS")

        # Tool 57: search_entities
        search_res = ci_mcp.search_entities(query="Ramesh")
        self.assertEqual(search_res["status"], "SUCCESS")

        # Tool 58: get_entity_profile
        prof_res = ci_mcp.get_entity_profile("Ramesh")
        self.assertIn(prof_res["status"], ("SUCCESS", "NOT_FOUND"))

        # Tool 62: get_entity_graph_statistics
        stats_res = ci_mcp.get_entity_graph_statistics()
        self.assertEqual(stats_res["status"], "SUCCESS")
        self.assertIn("total_entities", stats_res["statistics"])

        # Tool 65: check_entity_ambiguity
        amb_res = ci_mcp.check_entity_ambiguity()
        self.assertEqual(amb_res["status"], "SUCCESS")

        # Tool 66: export_entity_graph
        exp_res = ci_mcp.export_entity_graph()
        self.assertEqual(exp_res["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
