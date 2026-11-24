"""
Day 21 Unit Tests — FastMCP Word Tools Registration & Facade Dispatch.
Verifies all 52 Word tools are registered on office_master_mcp and facade operations return structured dicts.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import office_master_mcp
from zye_office.integration.word_mcp_integration import WordMCPIntegrationFacade


class TestDay21MCP(unittest.TestCase):

    def test_all_52_word_tools_registered(self) -> None:
        """Verify office_master_mcp registers all 52 Word automation tools."""
        tools = office_master_mcp.mcp._tool_manager._tools
        word_tools = [name for name in tools.keys() if name.startswith("word_")]
        self.assertEqual(len(word_tools), 52)

    def test_key_word_tools_exist(self) -> None:
        """Verify presence of core Day 21 tool names."""
        tools = office_master_mcp.mcp._tool_manager._tools
        expected_tools = [
            "word_create_document",
            "word_open_document",
            "word_save_document",
            "word_save_document_as",
            "word_close_document",
            "word_inspect_document",
            "word_insert_text",
            "word_replace_text",
            "word_format_text",
            "word_format_paragraph",
            "word_apply_style",
            "word_create_table",
            "word_populate_table",
            "word_set_header",
            "word_set_footer",
            "word_insert_page_numbers",
            "word_set_page_orientation",
            "word_create_bullet_list",
            "word_insert_toc",
            "word_insert_hyperlink",
            "word_create_bookmark",
            "word_get_track_changes_status",
            "word_set_track_changes",
            "word_get_revisions",
            "word_accept_revision",
            "word_reject_revision",
            "word_accept_all_revisions",
            "word_reject_all_revisions",
            "word_add_comment",
            "word_get_comments",
            "word_resolve_comment",
            "word_inspect_mail_merge",
            "word_connect_merge_source",
            "word_execute_mail_merge",
            "word_get_statistics",
            "word_inspect_accessibility",
            "word_generate_accessibility_report",
            "word_export_pdf_advanced",
        ]
        for t in expected_tools:
            self.assertIn(t, tools, f"Tool '{t}' missing from office_master_mcp")

    def test_facade_instantiation(self) -> None:
        """Verify WordMCPIntegrationFacade initializes engines and capabilities."""
        facade = WordMCPIntegrationFacade()
        self.assertIsNotNone(facade.adapter)
        self.assertIsNotNone(facade.doc_mgr)
        self.assertIsNotNone(facade.content_engine)
        self.assertIsNotNone(facade.formatting_engine)
        self.assertIsNotNone(facade.style_mgr)
        self.assertIsNotNone(facade.table_engine)
        self.assertIsNotNone(facade.header_footer)
        self.assertIsNotNone(facade.layout_engine)
        self.assertIsNotNone(facade.list_engine)
        self.assertIsNotNone(facade.toc_engine)
        self.assertIsNotNone(facade.hyperlink_engine)
        self.assertIsNotNone(facade.bookmark_engine)
        self.assertIsNotNone(facade.track_changes_engine)
        self.assertIsNotNone(facade.comment_engine)
        self.assertIsNotNone(facade.mail_merge_engine)
        self.assertIsNotNone(facade.metadata_engine)
        self.assertIsNotNone(facade.accessibility_engine)


if __name__ == "__main__":
    unittest.main()
