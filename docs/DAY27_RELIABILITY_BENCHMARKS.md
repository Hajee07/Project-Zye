# ZYE AI — DAY 27: PERFORMANCE & RELIABILITY BENCHMARKS

## 1. Benchmark Harness Overview
The Day 27 Benchmarking Engine (`zye_ai_plugins/benchmarking/`) provides a synthetic, automated harness for measuring model response latency, throughput, and error recovery without risking confidential user data.

---

## 2. Standardized Synthetic Prompts
- `bench_ping`: Simple latency ping prompt (*"Respond with the single word 'READY'"*).
- `bench_arithmetic`: Deterministic reasoning prompt (*"Calculate (123 * 45) + 678"*).
- `bench_python_func`: Code generation prompt (*"Write a Python function def is_prime(n: int) -> bool:"*).

---

## 3. Workload Profiles
1. **`QUICK`:** 1 round, single concurrency probe. Minimal overhead.
2. **`STANDARD`:** 2 rounds across ping and reasoning prompts with dual concurrency.
3. **`CONCURRENCY_STRESS`:** 3 rounds with 4 concurrent slots to verify bulkhead limits, queue bounded waiting, and backpressure handling.

---

## 4. MCP Tools & Reporting
- `run_provider_benchmark(provider_name, workload_type)`: Executes authorized benchmark run.
- `get_provider_benchmark_report()`: Retrieves the latest markdown and structured benchmark data.
