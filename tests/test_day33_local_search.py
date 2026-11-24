"""
Tests for Day 33 Local Search: Multi-Format Document Extraction, SQLite FTS5 Indexing, and Fast Engine.
"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from zye_computer_intelligence.search.local_document_extractor import LocalDocumentExtractor
from zye_computer_intelligence.search.local_index_manager import LocalIndexManager
from zye_computer_intelligence.search.local_search_engine import LocalSearchEngine
from zye_computer_intelligence.security.local_search_policy import LocalSearchPolicy


class TestDay33LocalSearch(unittest.TestCase):
    """Verifies document extraction, FTS5 full-text indexing, and search engine query execution."""

    def setUp(self):
        self.root = Path("d:/Zye/scratch/test_local_search_env").resolve()
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)

        # Create sample test files
        (self.root / "README.md").write_text(
            "# Zye Architecture\nThis is an autonomous personal AI assistant built with Gemini Live.",
            encoding="utf-8",
        )
        (self.root / "main.py").write_text(
            "import os\n\ndef run_assistant():\n    print('Zye Assistant Online')\n",
            encoding="utf-8",
        )
        (self.root / "data.csv").write_text(
            "id,name,role\n1,Alice,Engineer\n2,Bob,Architect\n",
            encoding="utf-8",
        )
        (self.root / "config.json").write_text(
            '{"app": "Zye", "version": "33.0.0", "engine": "DuckDB"}',
            encoding="utf-8",
        )

        # Index DB inside dedicated scratch db directory
        self.db_dir = Path("d:/Zye/scratch/test_local_search_db").resolve()
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.index_db_path = self.db_dir / "test_search_fts.db"
        if self.index_db_path.exists():
            self.index_db_path.unlink()

        self.policy = LocalSearchPolicy(allowed_roots=[self.root])
        self.index_mgr = LocalIndexManager(db_path=self.index_db_path, policy=self.policy)
        self.search_engine = LocalSearchEngine(
            policy=self.policy,
            index_manager=self.index_mgr,
        )

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
        if self.db_dir.exists():
            shutil.rmtree(self.db_dir, ignore_errors=True)

    # --- Document Extractor Tests ---

    def test_01_extract_markdown_and_python(self):
        """Verifies text extraction from markdown and python files."""
        md_doc = LocalDocumentExtractor.extract_document(self.root / "README.md")
        self.assertIn("autonomous personal AI assistant", md_doc["content"])
        self.assertEqual(md_doc["file_type"], "md")

        py_doc = LocalDocumentExtractor.extract_document(self.root / "main.py")
        self.assertIn("run_assistant", py_doc["content"])
        self.assertEqual(py_doc["file_type"], "py")

    def test_02_extract_csv_and_json(self):
        """Verifies structured text extraction from CSV and JSON files."""
        csv_doc = LocalDocumentExtractor.extract_document(self.root / "data.csv")
        self.assertIn("Alice", csv_doc["content"])
        self.assertIn("Engineer", csv_doc["content"])

        json_doc = LocalDocumentExtractor.extract_document(self.root / "config.json")
        self.assertIn("33.0.0", json_doc["content"])

    # --- FTS5 Index Manager Tests ---

    def test_03_fts5_indexing_and_incremental_rebuild(self):
        """Verifies FTS5 table initialization, document indexing, and status reporting."""
        status_before = self.index_mgr.get_index_status()
        self.assertEqual(status_before["indexed_documents_count"], 0)

        # Index files in root
        rebuild_res = self.index_mgr.rebuild_index([self.root], self.policy)
        self.assertTrue(rebuild_res["indexed_files"] >= 4)

        status_after = self.index_mgr.get_index_status()
        self.assertTrue(status_after["indexed_documents_count"] >= 4)

        # Query FTS5 for term
        results = self.index_mgr.search_fts("Gemini", limit=5)
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["file_name"], "README.md")
        self.assertIn("assistant", results[0]["snippet"].lower())

    def test_04_fts5_incremental_skips_unchanged_files(self):
        """Verifies incremental indexing skips files whose mtime and hash have not changed."""
        self.index_mgr.rebuild_index([self.root], self.policy)
        # Second run should skip unchanged files
        res2 = self.index_mgr.rebuild_index([self.root], self.policy)
        self.assertEqual(res2["indexed_files"], 0)
        self.assertTrue(res2["skipped_count"] >= 4)

    # --- Local Search Engine Execution Tests ---

    def test_05_search_exact_phrase(self):
        """Verifies local search engine locates exact phrases in files."""
        res = self.search_engine.search_local_sources(
            query="Zye Assistant Online",
            root_path=self.root,
            max_results=5,
            exact_phrase=True,
        )
        self.assertEqual(res["status"], "SUCCESS")
        matches = res["results"]
        self.assertTrue(len(matches) >= 1)
        self.assertTrue(any("main.py" in m.get("file_path", "") for m in matches))

    def test_06_search_with_extension_filter(self):
        """Verifies search results honor file extension filters."""
        res = self.search_engine.search_local_sources(
            query="Zye",
            root_path=self.root,
            file_types=[".py"],
            max_results=5,
        )
        self.assertEqual(res["status"], "SUCCESS")
        matches = res["results"]
        self.assertTrue(all(m.get("file_path", "").endswith(".py") for m in matches))

    def test_07_search_with_fts5_boost(self):
        """Verifies hybrid local search combines FTS5 index hits with file scan."""
        self.index_mgr.rebuild_index([self.root], self.policy)
        res = self.search_engine.search_local_sources(
            query="Architect",
            root_path=self.root,
            max_results=5,
        )
        self.assertEqual(res["status"], "SUCCESS")
        matches = res["results"]
        self.assertTrue(len(matches) >= 1)
        self.assertTrue(any("data.csv" in m.get("file_path", "") for m in matches))


if __name__ == "__main__":
    unittest.main()
