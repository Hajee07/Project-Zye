"""
ZYE AI — Day 37 Monte Carlo Performance Benchmark.
Executes multi-iteration benchmarks across sample counts: 1,000, 5,000, 10,000, 20,000, and 50,000.
Measures p50, p95, min, max, memory usage, and throughput (scenarios/sec).
"""

import gc
import json
import os
import sys
import time
import numpy as np

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zye_realtime_tactical.kinematics.kinematic_models import KinematicState, UncertaintyConfig
from zye_realtime_tactical.kinematics.monte_carlo_engine import MonteCarloSimulationEngine


def run_benchmark():
    host = KinematicState(
        entity_id="host_benchmark",
        position=[0.0, 0.0],
        velocity=[20.0, 0.0],
        radius=1.5,
    )
    target = KinematicState(
        entity_id="target_benchmark",
        position=[120.0, 3.0],
        velocity=[-20.0, 0.0],
        radius=1.5,
    )
    unc = UncertaintyConfig(
        position_std=[1.5, 1.5],
        velocity_std=[1.0, 1.0],
    )

    sample_tiers = [1000, 5000, 10000, 20000, 50000]
    iterations_per_tier = 10

    print("================================================================================")
    print(" ZYE AI — DAY 37 VECTORIZED MONTE CARLO PERFORMANCE BENCHMARK")
    print("================================================================================")
    print(f"{'Sample Count':<14} | {'Min (ms)':<10} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'Max (ms)':<10} | {'Throughput (scen/s)':<20}")
    print("--------------------------------------------------------------------------------")

    results_summary = {}

    for count in sample_tiers:
        latencies = []
        # Warmup
        MonteCarloSimulationEngine.run_simulation(
            entity_a=host,
            entity_b=target,
            sample_count=count,
            uncertainty_b=unc,
            random_seed=42,
        )

        for _ in range(iterations_per_tier):
            gc.disable()
            t0 = time.perf_counter_ns()
            res = MonteCarloSimulationEngine.run_simulation(
                entity_a=host,
                entity_b=target,
                sample_count=count,
                uncertainty_b=unc,
                random_seed=None,
            )
            t1 = time.perf_counter_ns()
            gc.enable()
            latencies.append((t1 - t0) / 1_000_000.0)

        latencies_arr = np.array(latencies)
        min_l = float(np.min(latencies_arr))
        p50_l = float(np.percentile(latencies_arr, 50))
        p95_l = float(np.percentile(latencies_arr, 95))
        max_l = float(np.max(latencies_arr))
        throughput = count / (p50_l / 1000.0) if p50_l > 0 else 0.0

        results_summary[str(count)] = {
            "sample_count": count,
            "min_ms": round(min_l, 3),
            "p50_ms": round(p50_l, 3),
            "p95_ms": round(p95_l, 3),
            "max_ms": round(max_l, 3),
            "throughput_scenarios_per_sec": round(throughput, 1),
        }

        print(f"{count:<14} | {min_l:<10.3f} | {p50_l:<10.3f} | {p95_l:<10.3f} | {max_l:<10.3f} | {throughput:<20,.1f}")

    print("================================================================================")
    print(" Benchmark completed successfully.")
    print("================================================================================")
    return results_summary


if __name__ == "__main__":
    run_benchmark()
