"""Synthetic Benchmark Profiles and Workloads for Zye AI (Day 27).

Defines standardized synthetic benchmark prompts and configurations:
- Never uses private user conversations
- Evaluates latency, throughput, reasoning speed, and concurrency behavior
- Differentiates mock harness tests from live API calls
"""

from __future__ import annotations

from typing import Any, Dict, List

SYNTHETIC_BENCHMARK_PROMPTS = [
    {
        "id": "bench_ping",
        "category": "latency",
        "prompt": "Respond with the single word 'READY'.",
        "max_tokens": 10,
    },
    {
        "id": "bench_arithmetic",
        "category": "reasoning",
        "prompt": "Calculate (123 * 45) + 678 and output only the final integer.",
        "max_tokens": 20,
    },
    {
        "id": "bench_python_func",
        "category": "code",
        "prompt": "Write a Python function `def is_prime(n: int) -> bool:` with type hints and docstring.",
        "max_tokens": 150,
    },
]

BENCHMARK_WORKLOADS: Dict[str, Dict[str, Any]] = {
    "QUICK": {
        "description": "Single-sample lightweight latency probe",
        "rounds": 1,
        "concurrency": 1,
        "prompts": ["bench_ping"],
    },
    "STANDARD": {
        "description": "Multi-prompt reliability and latency evaluation",
        "rounds": 2,
        "concurrency": 2,
        "prompts": ["bench_ping", "bench_arithmetic"],
    },
    "CONCURRENCY_STRESS": {
        "description": "Parallel workload testing bulkhead limits and queueing",
        "rounds": 3,
        "concurrency": 4,
        "prompts": ["bench_ping"],
    },
}
