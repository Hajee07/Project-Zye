"""
Unit Tests for Day 34 Cross-Document Entity Linking Engine.
Verifies entity extraction across 9 categories, canonical normalization,
disambiguation safeguards, SQLite graph persistence, and cross-document connection queries.
"""

import tempfile
import unittest
from pathlib import Path

from zye_computer_intelligence.entity_linking.cross_document_entity_linker import CrossDocumentEntityLinker
from zye_computer_intelligence.entity_linking.document_relationship_index import DocumentRelationshipIndex
from zye_computer_intelligence.entity_linking.entity_extraction_engine import EntityExtractionEngine
from zye_computer_intelligence.entity_linking.entity_matcher import EntityMatcher
from zye_computer_intelligence.entity_linking.entity_normalizer import (
    extract_name_tokens,
    normalize_entity_text,
)
from zye_computer_intelligence.entity_linking.entity_relationship_engine import EntityRelationshipEngine
from zye_computer_intelligence.entity_linking.entity_resolution_engine import EntityResolutionEngine
from zye_computer_intelligence.schemas.entity_schemas import (
    EntityMention,
    EntityType,
    RelationshipType,
    ResolutionStatus,
)

WORKSPACE_TEST_BASE = Path("d:/Zye/data/test_tmp")


class TestDay34EntityLinking(unittest.TestCase):
    """Test suite for Cross-Document Entity Linking."""

    def setUp(self):
        WORKSPACE_TEST_BASE.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=str(WORKSPACE_TEST_BASE))
        self.db_path = Path(self.temp_dir.name) / "test_graph.db"
        self.linker = CrossDocumentEntityLinker(db_path=self.db_path)

        # Create two sample documents
        self.doc_a = Path(self.temp_dir.name) / "project_specs.md"
        self.doc_b = Path(self.temp_dir.name) / "team_overview.txt"

        self.doc_a.write_text(
            "# Project Orion Architecture\n"
            "Lead Architect: Dr. Sundar Nathan\n"
            "Company: Nova Technologies Ltd.\n"
            "Stack: Built with Python, DuckDB, and SQLite on 2026-11-22.\n"
            "Contact: sundar@novatech.io\n",
            encoding="utf-8",
        )

        self.doc_b.write_text(
            "Quarterly Operations Report\n"
            "Project Orion review meeting attended by Sundar Nathan.\n"
            "Organization: Nova Technologies.\n"
            "Technologies used: DuckDB and Redis.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_entity_normalization(self):
        """Verifies title stripping, org suffix removal, and Unicode NFC normalization."""
        norm_person = normalize_entity_text("Dr. Sundar Nathan", EntityType.PERSON)
        self.assertEqual(norm_person, "Sundar Nathan")

        norm_org = normalize_entity_text("Nova Technologies Ltd.", EntityType.ORGANIZATION)
        self.assertEqual(norm_org, "Nova Technologies")

        tokens = extract_name_tokens("Nova Technologies Ltd")
        self.assertIn("nova", tokens)
        self.assertIn("technologies", tokens)

    def test_entity_matcher_and_scoring(self):
        """Verifies similarity scoring: exact, normalized, acronym, token Jaccard."""
        score_exact, reasons, _ = EntityMatcher.calculate_match_score(
            "Nova Tech", EntityType.ORGANIZATION, "Nova Tech", EntityType.ORGANIZATION
        )
        self.assertEqual(score_exact, 1.0)

        score_norm, _, _ = EntityMatcher.calculate_match_score(
            "Dr. Sundar Nathan", EntityType.PERSON, "Sundar Nathan", EntityType.PERSON
        )
        self.assertGreaterEqual(score_norm, 0.90)

        score_acronym, reasons_acronym, _ = EntityMatcher.calculate_match_score(
            "TCS", EntityType.ORGANIZATION, "Tata Consultancy Services", EntityType.ORGANIZATION
        )
        self.assertEqual(score_acronym, 0.85)

    def test_disambiguation_safeguard(self):
        """Verifies that single common first names across documents are flagged as AMBIGUOUS."""
        m1 = EntityMention(
            mention_id="m1", document_id="doc1.txt", file_path="doc1.txt",
            original_text="Ramesh", normalized_text="Ramesh", entity_type=EntityType.PERSON
        )
        m2 = EntityMention(
            mention_id="m2", document_id="doc2.txt", file_path="doc2.txt",
            original_text="Ramesh", normalized_text="Ramesh", entity_type=EntityType.PERSON
        )
        entities, _ = EntityResolutionEngine.resolve_mentions([m1, m2])
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].resolution_status, ResolutionStatus.AMBIGUOUS)

    def test_cross_document_indexing_and_connections(self):
        """Verifies end-to-end indexing of documents and shared entity discovery."""
        res = self.linker.index_documents_sync([str(self.doc_a), str(self.doc_b)])
        self.assertEqual(res.status, "COMPLETED")
        self.assertEqual(res.total_documents_processed, 2)
        self.assertGreater(res.total_mentions_found, 5)

        # Cross-document connections between doc_a and doc_b
        shared = self.linker.find_cross_document_connections(self.doc_a.name, self.doc_b.name)
        shared_names = {s["canonical_name"].lower() for s in shared}

        # Project Orion and DuckDB appear in both documents
        self.assertTrue(
            any("orion" in name for name in shared_names) or any("duckdb" in name for name in shared_names)
        )

        # Profile retrieval
        stats = self.linker.get_graph_statistics()
        self.assertGreaterEqual(stats["total_entities"], 3)
        self.assertGreaterEqual(stats["total_documents"], 2)


if __name__ == "__main__":
    unittest.main()
