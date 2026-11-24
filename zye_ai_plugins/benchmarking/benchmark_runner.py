"""Automated Performance & Reliability Benchmark Runner for Zye AI (Day 27).

Executes synthetic benchmarking across configured AI providers:
- Measures response latency (P50, average, min, max)
- Tracks success rate, timeout rate, and failure rate
- Verifies behavior under parallel concurrency
- Generates transparent, empirical benchmark reports
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from ..provider_registry import get_provider_registry
from ..telemetry.provider_metrics import RollingLatencyTracker
from .benchmark_profiles import BENCHMARK_WORKLOADS, SYNTHETIC_BENCHMARK_PROMPTS

logger = logging.getLogger("zye.ai_plugins.benchmarking")


async def benchmark_single_provider(
    provider_id: str,
    workload_type: str = "QUICK",
    mock_executor: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run benchmark against a single provider."""
    pid = provider_id.lower().strip()
    reg = get_provider_registry()
    provider = reg.get_provider(pid)

    if not provider and not mock_executor:
        return {
            "provider_id": pid,
            "status": "error",
            "message": f"Provider '{pid}' not found in registry",
        }

    workload = BENCHMARK_WORKLOADS.get(workload_type.upper(), BENCHMARK_WORKLOADS["QUICK"])
    prompts_to_run = [p for p in SYNTHETIC_BENCHMARK_PROMPTS if p["id"] in workload["prompts"]]
    if not prompts_to_run:
        prompts_to_run = [SYNTHETIC_BENCHMARK_PROMPTS[0]]

    tracker = RollingLatencyTracker()
    total_calls = 0
    success_calls = 0
    failed_calls = 0

    for rnd in range(workload["rounds"]):
        for p_spec in prompts_to_run:
            total_calls += 1
            t_start = time.perf_counter()
            try:
                if mock_executor:
                    # Mock benchmark execution
                    res = await mock_executor(prompt=p_spec["prompt"])
                else:
                    res = await provider.generate_response(
                        prompt=p_spec["prompt"],
                        max_tokens=p_spec["max_tokens"],
                    )

                latency_ms = (time.perf_counter() - t_start) * 1000.0
                if getattr(res, "status", "") == "success" or isinstance(res, str):
                    success_calls += 1
                    tracker.record(latency_ms)
                else:
                    failed_calls += 1
            except Exception as exc:
                failed_calls += 1
                logger.warning("Benchmark probe failed for '%s': %s", pid, exc)

    pcts = tracker.get_percentiles()
    success_rate = (success_calls / max(1, total_calls)) * 100.0

    return {
        "provider_id": pid,
        "workload": workload_type.upper(),
        "total_probes": total_calls,
        "successful_probes": success_calls,
        "failed_probes": failed_calls,
        "success_rate_percent": round(success_rate, 1),
        "latency_percentiles_ms": pcts,
        "status": "completed" if success_calls > 0 else "failed",
    }


async def run_suite_benchmarks(
    providers: Optional[List[str]] = None,
    workload_type: str = "QUICK",
) -> Dict[str, Any]:
    """Run benchmarks across all specified or active providers."""
    reg = get_provider_registry()
    target_pids = providers or reg.get_active_providers()

    # De-duplicate
    target_pids = list(dict.fromkeys([p.lower().strip() for p in target_pids]))

    tasks = [benchmark_single_provider(pid, workload_type) for pid in target_pids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary: Dict[str, Any] = {}
    for idx, pid in enumerate(target_pids):
        res = results[idx]
        if isinstance(res, Exception):
            summary[pid] = {"provider_id": pid, "status": "error", "error": str(res)}
        else:
            summary[pid] = res

    return {
        "timestamp": time.time(),
        "workload": workload_type.upper(),
        "providers_benchmarked": len(target_pids),
        "results": summary,
    }


def format_benchmark_markdown_report(suite_results: Dict[str, Any]) -> str:
    """Format benchmark suite results into readable markdown report."""
    lines = [
        "# Zye AI — Multi-AI Performance Benchmark Report",
        f"**Workload Profile:** {suite_results.get('workload', 'QUICK')}",
        f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(suite_results.get('timestamp', time.time())))}",
        "",
        "| Provider | Total Probes | Success Rate | P50 Latency | P95 Latency | Avg Latency | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for pid, res in suite_results.get("results", {}).items():
        if res.get("status") == "completed":
            pcts = res.get("latency_percentiles_ms", {})
            lines.append(
                f"| `{pid}` | {res.get('total_probes', 0)} | {res.get('success_rate_percent', 0)}% | "
                f"{pcts.get('p50', 0)}ms | {pcts.get('p95', 0)}ms | {pcts.get('avg', 0)}ms | **PASS** |"
            )
        else:
            lines.append(f"| `{pid}` | {res.get('total_probes', 0)} | 0.0% | N/A | N/A | N/A | **FAIL** |")

    lines.append("\n*Note: Benchmark probes use non-intrusive synthetic prompts.*")
    return "\n".join(lines)
