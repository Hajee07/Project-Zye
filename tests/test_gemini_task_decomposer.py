"""
Unit tests for GeminiTaskDecomposer — 7 logical worker roles, task decomposition, and prompt construction.
"""

import unittest
from gemini_task_decomposer import ALL_LOGICAL_ROLES, GeminiTaskDecomposer


class TestGeminiTaskDecomposer(unittest.TestCase):
    def setUp(self):
        self.decomposer = GeminiTaskDecomposer(db_path=":memory:")

    def test_01_all_seven_logical_roles_present(self):
        self.assertEqual(len(ALL_LOGICAL_ROLES), 7)
        expected = ["TECHNICAL", "ARCHITECTURE", "DATA", "SECURITY", "RESEARCH", "ALTERNATIVES", "QUALITY"]
        self.assertEqual(ALL_LOGICAL_ROLES, expected)

    def test_02_decompose_full_roles(self):
        subtasks = self.decomposer.decompose("Design SQLite WAL sync mechanism")
        self.assertEqual(len(subtasks), 7)
        roles = [s["role"] for s in subtasks]
        self.assertEqual(roles, ALL_LOGICAL_ROLES)
        for s in subtasks:
            self.assertIn("Design SQLite WAL sync mechanism", s["prompt"])

    def test_03_decompose_subset_of_roles(self):
        subset = ["SECURITY", "QUALITY"]
        subtasks = self.decomposer.decompose("Evaluate user input sanitization", requested_roles=subset)
        self.assertEqual(len(subtasks), 2)
        self.assertEqual([s["role"] for s in subtasks], subset)


if __name__ == "__main__":
    unittest.main()
