# ZYE AI — DAY 27: INTELLIGENT AI PROVIDER ROUTING

## 1. Overview & System Purpose
The Day 27 Intelligent AI Provider Router (`zye_ai_plugins/routing/provider_router.py`) replaces static model bindings with a mathematically grounded dynamic selection engine. When Zye AI needs an external or local AI model to answer a question, summarize text, or assist the user, the router evaluates all configured providers and selects the optimal engine based on:
1. Operational availability & circuit-breaker state.
2. Latency percentiles (P50) from live telemetry.
3. Official model pricing rate cards.
4. Historical reliability score with sample-size confidence damping.
5. Task capability match (coding, reasoning, general speed).
6. User instructions and privacy constraints.

---

## 2. Supported Routing Modes

```
+-----------------------------------------------------------------------------------------------+
|                                      ROUTING MODES                                            |
+---------------------+--------------------+----------------------------------------------------+
| Mode                | Primary Objective  | Weighting Profile (Quality / Speed / Cost / Rel)   |
+---------------------+--------------------+----------------------------------------------------+
| BALANCED            | Balanced Trade-off | 30% Quality, 25% Speed, 20% Cost, 25% Reliability  |
| QUALITY_FIRST       | Maximum Reasoning  | 60% Quality, 15% Speed, 5% Cost, 20% Reliability   |
| SPEED_FIRST         | Lowest Latency     | 15% Quality, 60% Speed, 10% Cost, 15% Reliability  |
| COST_FIRST          | Economy / Free     | 15% Quality, 15% Speed, 55% Cost, 15% Reliability  |
| RELIABILITY_FIRST   | Uptime & Stability | 20% Quality, 10% Speed, 10% Cost, 60% Reliability  |
| LOCAL_ONLY          | Strict Privacy     | Exclusively routes to local Ollama (100% offline)  |
| USER_SELECTED       | Explicit Pinning   | Honors user request without silent substitution    |
| COUNCIL_MODE        | Multi-Model Quorum | Preserves exact participant list for Day 26 Council|
| PRIVACY_RESTRICTED  | Data Protection    | Forbids cloud transmission of sensitive payloads   |
+---------------------+--------------------+----------------------------------------------------+
```

---

## 3. Composite Routing Score Formulation
For each candidate provider $P$ under mode $M$, the normalized routing score $S(P, M)$ is computed as:

$$S(P, M) = w_q \cdot Q(P) + w_s \cdot \text{Speed}(P) + w_c \cdot \text{Cost}(P) + w_r \cdot \text{Rel}(P)$$

Where:
- $Q(P)$: Model capability rating (0.0 to 1.0) based on verified architectural benchmarks.
- $\text{Speed}(P)$: Latency score computed from rolling P50 latency: $\max\left(0.1, 1.0 - \frac{\text{P50}}{3000\text{ms}}\right)$.
- $\text{Cost}(P)$: Cost score ($1.0$ for free local compute, down to $0.1$ for expensive models).
- $\text{Rel}(P)$: Empirical reliability score adjusted for sample size.

---

## 4. Explainable Decision Output Schema
Every routing decision generates a transparent, audit-ready record:

```json
{
  "request_id": "route_1795210212_16059b",
  "routing_mode": "BALANCED",
  "selected_provider": "chatgpt",
  "selected_model": "gpt-4o-mini",
  "decision_reasons": [
    "Selected under 'BALANCED' routing policy with top composite score 0.8124",
    "Circuit state is healthy and rate limits clear",
    "Reliability confidence: HIGH_SAMPLE_CONFIDENCE"
  ],
  "rejected_candidates": [
    {
      "provider": "claude",
      "model": "claude-3-5-sonnet",
      "score": 0.7420,
      "reason": "Lower composite score under BALANCED mode (higher token cost)"
    }
  ],
  "estimated_cost": {
    "cost_status": "CALCULATED",
    "estimated_cost_usd": 0.000225,
    "currency": "USD"
  },
  "estimated_latency_ms": 310.2,
  "fallback_allowed": true,
  "routing_status": "SELECTED"
}
```
