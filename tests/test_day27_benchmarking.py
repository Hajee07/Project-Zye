"""Day 27 Unit Tests: Performance Benchmarking Harness.

Tests:
- Synthetic benchmark prompt specs and workloads
- Single provider benchmarking with mock executor
- Markdown benchmark report formatting
"""

import time
import unittest

from zye_ai_plugins.benchmarking import (
    BENCHMARK_WORKLOADS,
    SYNTHETIC_BENCHMARK_PROMPTS,
    benchmark_single_provider,
    format_benchmark_markdown_report,
)


def run_coro(coro):
    """Run an async coroutine synchronously without creating a Windows Proactor loopback socket."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError(f"Coroutine {coro} yielded unexpectedly")


class TestDay27Benchmarking(unittest.TestCase):
    """Test suite for performance benchmarking."""

    def test_01_synthetic_prompts_configured(self):
        """Verify synthetic benchmark prompts exist and avoid private user text."""
        self.assertGreaterEqual(len(SYNTHETIC_BENCHMARK_PROMPTS), 3)
        categories = {p["category"] for p in SYNTHETIC_BENCHMARK_PROMPTS}
        self.assertIn("latency", categories)
        self.assertIn("reasoning", categories)
        self.assertIn("code", categories)

    def test_02_workload_definitions(self):
        """Verify standard workloads QUICK, STANDARD, and CONCURRENCY_STRESS."""
        self.assertIn("QUICK", BENCHMARK_WORKLOADS)
        self.assertIn("STANDARD", BENCHMARK_WORKLOADS)
        self.assertIn("CONCURRENCY_STRESS", BENCHMARK_WORKLOADS)

    def test_03_benchmark_single_provider_mocked(self):
        """Verify benchmark execution using a mocked provider coroutine."""
        async def mock_exec(prompt, **kwargs):
            return "READY"

        res = run_coro(benchmark_single_provider("ollama", workload_type="QUICK", mock_executor=mock_exec))
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["provider_id"], "ollama")
        self.assertEqual(res["total_probes"], 1)
        self.assertEqual(res["success_rate_percent"], 100.0)
        self.assertIn("p50", res["latency_percentiles_ms"])

    def test_04_format_benchmark_markdown_report(self):
        """Verify markdown report generation structure."""
        suite_data = {
            "workload": "STANDARD",
            "timestamp": time.time(),
            "results": {
                "chatgpt": {
                    "provider_id": "chatgpt",
                    "status": "completed",
                    "total_probes": 2,
                    "success_rate_percent": 100.0,
                    "latency_percentiles_ms": {"p50": 110.0, "p95": 140.0, "avg": 125.0},
                },
                "claude": {
                    "provider_id": "claude",
                    "status": "completed",
                    "total_probes": 2,
                    "success_rate_percent": 100.0,
                    "latency_percentiles_ms": {"p50": 130.0, "p95": 160.0, "avg": 145.0},
                },
            },
        }
        report = format_benchmark_markdown_report(suite_data)
        self.assertIn("# Zye AI — Multi-AI Performance Benchmark Report", report)
        self.assertIn("| `chatgpt` |", report)
        self.assertIn("| `claude` |", report)
        self.assertIn("**PASS**", report)


if __name__ == "__main__":
    unittest.main()
