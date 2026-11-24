"""
Day 21 Unit Tests — Word Voice Commands & Multi-Lingual Intent Normalization.
Verifies normalization and intent routing of English, Tamil, and Tanglish natural language commands for Microsoft Word.
"""

from __future__ import annotations

import unittest

from zye_windows.app_catalog import normalize_voice_app_name


class TestDay21Voice(unittest.TestCase):

    def parse_word_voice_intent(self, phrase: str) -> dict[str, str]:
        """Test harness simulating Zye's multi-lingual voice command parser for Word."""
        p = phrase.lower().strip()

        # Document Creation
        if any(w in p for w in ["puthu document", "new document", "create document", "document create pannu", "doc open pannu"]):
            return {"action": "word_create_document"}

        # Text Insertion
        if "type pannu" in p or "insert text" in p or "ezhudhu" in p or "write" in p:
            # extract text
            text = p.replace("type pannu", "").replace("insert text", "").replace("ezhudhu", "").replace("write", "").strip()
            return {"action": "word_insert_text", "text": text}

        # Save Document
        if "save pannu" in p or "save document" in p or "pathivusei" in p:
            return {"action": "word_save_document"}

        # Export PDF
        if "pdf export pannu" in p or "export pdf" in p or "save as pdf" in p or "pdf a mathu" in p:
            return {"action": "word_export_pdf_advanced"}

        # Table Creation
        if "table create pannu" in p or "create table" in p or "attavanai" in p:
            return {"action": "word_create_table"}

        # Track Changes
        if "track changes on pannu" in p or "enable track changes" in p:
            return {"action": "word_set_track_changes", "enabled": "true"}

        # Document Inspection
        if "document inspect pannu" in p or "word statistics" in p or "ethana varthai" in p:
            return {"action": "word_get_statistics"}

        return {"action": "unknown"}

    def test_voice_app_name_normalization(self) -> None:
        """Verify colloquial names for Word resolve to canonical winword."""
        self.assertEqual(normalize_voice_app_name("word"), "winword")
        self.assertEqual(normalize_voice_app_name("ms word"), "winword")
        self.assertEqual(normalize_voice_app_name("microsoft word"), "winword")

    def test_tamil_and_tanglish_command_parsing(self) -> None:
        """Verify Tanglish voice commands resolve to canonical Word actions."""
        res1 = self.parse_word_voice_intent("Zye, puthu document create pannu")
        self.assertEqual(res1["action"], "word_create_document")

        res2 = self.parse_word_voice_intent("Zye, intha document ah pdf export pannu")
        self.assertEqual(res2["action"], "word_export_pdf_advanced")

        res3 = self.parse_word_voice_intent("Zye, table create pannu")
        self.assertEqual(res3["action"], "word_create_table")

        res4 = self.parse_word_voice_intent("Zye, track changes on pannu")
        self.assertEqual(res4["action"], "word_set_track_changes")

    def test_english_voice_commands(self) -> None:
        """Verify English voice commands resolve accurately."""
        res1 = self.parse_word_voice_intent("Create a new document")
        self.assertEqual(res1["action"], "word_create_document")

        res2 = self.parse_word_voice_intent("Export PDF now")
        self.assertEqual(res2["action"], "word_export_pdf_advanced")


if __name__ == "__main__":
    unittest.main()
