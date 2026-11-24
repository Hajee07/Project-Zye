# ZYE AI — DAY 26: MULTI-CRITERIA DECISION ENGINE

## 1. Overview
The Decision Engine (`zye_ai_plugins/decision_engine.py`) provides mathematically grounded Multi-Criteria Decision Analysis (MCDA) for evaluating competing technical solutions and architectures proposed by council members.

Each candidate solution is evaluated across 7 core dimensions:
1. `correctness`: Algorithmic and logical soundness (0.0 to 1.0).
2. `security`: Robustness against vulnerabilities and least-privilege compliance (0.0 to 1.0).
3. `performance`: Latency, throughput, and CPU/RAM efficiency (0.0 to 1.0).
4. `scalability`: Horizontal and vertical scaling potential (0.0 to 1.0).
5. `maintainability`: Code clarity, testability, and refactorability (0.0 to 1.0).
6. `implementation_complexity`: Simplicity of deployment and maintenance (0.0 to 1.0).
7. `resource_efficiency`: Cost, memory footprint, and bandwidth footprint (0.0 to 1.0).

---

## 2. Priority Profiles
The engine defines 7 preset priority modes that rebalance the weights according to operational context:

```
+---------------------------------------------------------------------------------------------------+
|                                     MCDA WEIGHT PRESETS                                           |
+---------------------+-------------+----------+-------------+---------------+---------------------+
| Priority Mode       | Security Wt | Perf Wt  | Scalability | Complexity Wt | Maintainability Wt  |
+---------------------+-------------+----------+-------------+---------------+---------------------+
| BALANCED            | 0.20        | 0.15     | 0.15        | 0.15          | 0.15                |
| MAXIMUM_SAFETY      | 0.40        | 0.05     | 0.10        | 0.10          | 0.15                |
| SPEED_CRITICAL      | 0.10        | 0.35     | 0.20        | 0.10          | 0.10                |
| LOW_RESOURCE        | 0.15        | 0.15     | 0.10        | 0.15          | 0.15 (0.30 Res)     |
| HIGH_RELIABILITY    | 0.25        | 0.10     | 0.15        | 0.10          | 0.20 (0.20 Correct) |
| MAINTAINABILITY_FIRST| 0.15       | 0.10     | 0.10        | 0.25          | 0.30                |
| USER_CUSTOM         | Dynamic     | Dynamic  | Dynamic     | Dynamic       | Dynamic             |
+---------------------+-------------+----------+-------------+---------------+---------------------+
```

### Weight Normalization
When custom weights are provided, `normalize_weights()` guarantees that:
$$\sum_{i=1}^{n} w_i = 1.0$$
preventing score inflation or under-weighting.

---

## 3. Composite Scoring Algorithm
For each candidate solution $S$, the composite score $C(S)$ is computed as the normalized dot product:

$$C(S) = \sum_{k} w_k \cdot s_k(S)$$

Solutions are then ranked in descending order of composite score:
$$\text{Rank 1} > \text{Rank 2} > \dots > \text{Rank } N$$

---

## 4. Score Separation & Provisional Decision Rules
To prevent misleading certainty when two architectures have nearly identical merit:
- The engine calculates the **Score Separation**:
$$\Delta = C(S_{\text{Rank 1}}) - C(S_{\text{Rank 2}})$$
- **Provisional Rule:** If $\Delta < 0.05$, the decision is marked:
  - `is_provisional = True`
  - `confidence = "LOW_CONFIDENCE"`
  - Reason: *"Top candidates are within 0.05 score separation. Solution depends heavily on specific operational trade-offs."*
- **Trade-Off Summary:** When $\Delta < 0.05$, the engine automatically isolates which criteria Solution A excelled at vs Solution B, providing Gemini Master Brain with the exact trade-off dimensions.
