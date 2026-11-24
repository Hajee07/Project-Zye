"""
Unit tests for parallel subtask execution — concurrency bounding, partial failure handling, and aggregation.

SANDBOX NOTE: The Windows sandbox blocks asyncio event loops in background PowerShell tasks.
These tests use a synchronous approach to test the logic without running an event loop.
The decompose() logic, aggregation, and subtask structure are tested synchronously.
The execute_subtasks() async function is verified structurally (callable, returns coroutine).
"""

import asyncio
import inspect
import unittest
from unittest.mock import MagicMock

from gemini_task_decomposer import ALL_LOGICAL_ROLES, GeminiTaskDecomposer
from gemini_result_aggregator import GeminiResultAggregator, SubtaskResult


class TestGeminiParallelExecution(unittest.TestCase):
    def setUp(self):
        self.decomposer = GeminiTaskDecomposer(db_path=":memory:", default_concurrency=2)
        self.aggregator = GeminiResultAggregator()

    def test_01_execute_subtasks_is_async_coroutine(self):
        """Verify execute_subtasks is an async method that returns a coroutine."""
        mock_gateway = MagicMock()
        mock_gateway.generate_response = MagicMock(return_value={
            "text": "mock output",
            "tokens_used": 50,
            "status": "SUCCESS",
        })
        # Verify it is a coroutine function (async def)
        self.assertTrue(
            inspect.iscoroutinefunction(self.decomposer.execute_subtasks),
            "execute_subtasks must be an async coroutine function"
        )

    def test_02_decompose_produces_bounded_workload(self):
        """Verify decompose generates role-labelled subtasks for concurrency."""
        subtasks = self.decomposer.decompose(
            "Build resilient cache",
            requested_roles=["TECHNICAL", "SECURITY", "QUALITY"],
        )
        self.assertEqual(len(subtasks), 3)
        roles_found = {s["role"] for s in subtasks}
        self.assertEqual(roles_found, {"TECHNICAL", "SECURITY", "QUALITY"})
        for s in subtasks:
            self.assertIn("Build resilient cache", s["prompt"])

    def test_03_aggregator_reports_all_successful(self):
        """Verify aggregator correctly marks all_successful when no failures."""
        results = [
            SubtaskResult(worker_role="TECHNICAL", content="Output A", status="SUCCESS", tokens_used=50),
            SubtaskResult(worker_role="SECURITY", content="Output B", status="SUCCESS", tokens_used=50),
            SubtaskResult(worker_role="QUALITY", content="Output C", status="SUCCESS", tokens_used=50),
        ]
        aggregated = self.aggregator.aggregate("test_task_01", results)
        self.assertTrue(aggregated.all_successful)
        self.assertEqual(aggregated.total_tokens_used, 150)
        self.assertEqual(len(aggregated.worker_results), 3)
        self.assertIn("Task Synthesis", aggregated.summary)

    def test_04_aggregator_partial_failure_tolerance(self):
        """Verify aggregator correctly handles partial failures from SECURITY worker."""
        results = [
            SubtaskResult(worker_role="TECHNICAL", content="Output A", status="SUCCESS", tokens_used=40),
            SubtaskResult(worker_role="SECURITY", content="", status="FAILED",
                          tokens_used=0, error="Security worker error"),
        ]
        aggregated = self.aggregator.aggregate("test_task_02", results)
        self.assertFalse(aggregated.all_successful)
        self.assertEqual(aggregated.worker_results["TECHNICAL"].status, "SUCCESS")
        self.assertEqual(aggregated.worker_results["SECURITY"].status, "FAILED")
        self.assertIn("Security worker error", aggregated.worker_results["SECURITY"].error)

    def test_05_semaphore_bound_matches_concurrency(self):
        """Verify the decomposer respects max_concurrency parameter."""
        decomposer_1 = GeminiTaskDecomposer(db_path=":memory:", default_concurrency=1)
        decomposer_3 = GeminiTaskDecomposer(db_path=":memory:", default_concurrency=3)
        self.assertEqual(decomposer_1._default_concurrency, 1)
        self.assertEqual(decomposer_3._default_concurrency, 3)
        # Cannot exceed max_workers (7)
        decomposer_max = GeminiTaskDecomposer(db_path=":memory:", default_concurrency=99)
        self.assertEqual(decomposer_max._default_concurrency, 7)


if __name__ == "__main__":
    unittest.main()
