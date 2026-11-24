# ZYE AI — DAY 36: OPPONENT BEHAVIOUR PATTERN RECOGNITION & MARKOV PREDICTIVE INTELLIGENCE

## 1. System Architecture & Core Principles

Day 36 expands ZYE AI's Phase 3 Real-Time Tactical Intelligence suite with an empirical, zero-fabrication Opponent Behaviour Prediction Engine. Built directly on top of the in-memory tactical foundation (`realtime_tactical_mcp.py` and `zye_realtime_tactical/opponent/`), this engine ingests action sequences into bounded circular buffers and predicts upcoming attacks using empirical First-Order and Second-Order Markov chains, recurring tactical bigram/trigram patterns, and high-precision inter-action timing analysis.

### Architectural Tenets
1. **Zero Fabrication**: Predictions strictly reflect empirical transitions observed in memory. When fewer than 6 actions are observed, the system returns `INSUFFICIENT_DATA`. When an action has no historical outgoing transitions, the system returns `NO_REPEAT_TRANSITION_FOUND`.
2. **Probability Non-Renormalization**: The top 3 next-action candidates display their exact historical conditional probabilities ($\frac{\text{hits}}{\text{context transitions}} \times 100\%$) and are never artificially inflated to sum to 100%.
3. **Pure In-Memory Execution**: Operates exclusively using `collections.deque(maxlen=1000)` and NumPy in RAM. Zero disk I/O, zero database latency.
4. **Isolated Multi-Opponent Tracking**: Per-opponent `threading.RLock` synchronization guarantees zero cross-opponent contention or data leakage.

```
                      +---------------------------------------+
                      |       Observed Tactical Stream        |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   OpponentActionValidator (<=1000)    |
                      |   - Lowercase stripping & hygiene    |
                      |   - Monotonic Timestamp Check         |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      | OpponentSequenceBuffer (maxlen=1000)  |
                      |   - Circular bounded deque            |
                      |   - Overwrite & rollover tracking     |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |    PredictionEvidenceGuard (>= 6)     |
                      +---------------------------------------+
                             /            |             \
                            /             |              \
                           v              v               v
             +--------------------+ +-------------+ +--------------------+
             | First-Order Markov | | 2nd-Order   | | Bigram / Trigram   |
             | P(X_{t+1}|X_t)     | | P(X_{t+1}|  | | Pattern Detectors  |
             |                    | | X_{t-1},X_t)| | (Counts >= 2)      |
             +--------------------+ +-------------+ +--------------------+
                           \              /               |
                            v            v                v
                      +-----------------------+     +--------------------+
                      | MarkovContextSelector |     | Pattern Ranking    |
                      | - Prefers 2nd-Order   |     | Top 4 Bigrams &    |
                      |   if support >= 2     |     | Trigrams           |
                      | - Fallback: 1st-Order |     +--------------------+
                      +-----------------------+               |
                                  |                           |
                                  v                           v
                      +--------------------------------------------------+
                      |        InterActionTimingAnalyzer                 |
                      |        - np.diff(timestamps)                     |
                      |        - Filter [0.05s, 60.0s]                   |
                      |        - Expected next attack interval           |
                      +--------------------------------------------------+
                                          |
                                          v
                      +--------------------------------------------------+
                      |           OpponentPredictionResult               |
                      |           (Structured Pydantic Model)            |
                      +--------------------------------------------------+
```

---

## 2. Mathematical Formulations

### 2.1 First-Order Markov Chain Transitions
The first-order transition matrix computes the conditional probability of next action $j$ given current single action $i$:
$$P(X_{t+1} = j \mid X_t = i) = \frac{N(i \to j)}{\sum_k N(i \to k)}$$

### 2.2 Second-Order Markov Chain Transitions
The second-order transition matrix computes the conditional probability of action $k$ given a sequential two-action context $(i, j)$:
$$P(X_{t+1} = k \mid X_{t-1} = i, X_t = j) = \frac{N(i, j \to k)}{\sum_m N(i, j \to m)}$$

### 2.3 Context Selection Policy
1. If the current two-action context $(a_{t-1}, a_t)$ has at least $\mathbf{2}$ outgoing observations in historical data, the engine selects the **Second-Order Context** (`2nd-Order Sequence Context`).
2. If the two-action context has $< 2$ observations, the engine cleanly falls back to the **First-Order Context** $a_t$ (`1st-Order Transition Context`) if it has $\ge 1$ outgoing transition.
3. If neither context has ever been followed by an action, the engine returns status `NO_REPEAT_TRANSITION_FOUND`.

### 2.4 Inter-Action Timing Analysis
Given action timestamps $T = [t_1, t_2, \dots, t_N]$, intervals are derived using vector subtraction:
$$\Delta t_i = t_{i+1} - t_i \quad \text{for } i \in \{1, \dots, N-1\}$$
Intervals are filtered to exclude jitter and macro pauses:
$$\Omega = \{\Delta t_i \mid 0.05 \le \Delta t_i \le 60.0\}$$
If $|\Omega| > 0$, the expected attack interval is:
$$\mathbb{E}[\Delta t] = \frac{1}{|\Omega|} \sum_{\Delta t \in \Omega} \Delta t$$

---

## 3. FastMCP Tactical Tools (Tools 06–10)

`realtime_tactical_mcp.py` exposes 10 FastMCP tools (5 Telemetry + 5 Opponent Behaviour):

| Tool Name | Type | Decorator | Description |
|---|---|---|---|
| `predict_opponent_attack` | Mutation / Inference | `@zye_safe_skill(retry_safe=False)` | Ingests actions, computes Markov predictions, identifies patterns, and estimates attack timing. |
| `get_opponent_sequence_status` | Inspection | `@zye_safe_skill(retry_safe=True)` | Returns buffer action count, capacity, rollover count, and activity timestamps. |
| `list_tracked_opponents` | Inspection | `@zye_safe_skill(retry_safe=True)` | Lists all active opponents tracked in RAM with action counts. |
| `reset_opponent_sequence` | Mutation | `@zye_safe_skill(retry_safe=False)` | Clears buffered actions and resets counters for an opponent. |
| `get_opponent_pattern_summary` | Inspection | `@zye_safe_skill(retry_safe=True)` | Analyzes existing buffer for recurring bigrams, trigrams, and Markov state without adding actions. |

---

## 4. Security & Safety Controls

1. **Non-Idempotent Safeguards**: `predict_opponent_attack` and `reset_opponent_sequence` are permanently registered in `main.py`'s `NON_IDEMPOTENT_OPERATIONS` to prevent accidental replay during network retry storms.
2. **Strict In-Memory Isolation**: No temporary files or persistent databases are touched during opponent tracking.
3. **Identifier Sanitization**: Opponent IDs are strictly validated to alphanumeric characters, underscores, hyphens, and colons up to 64 characters.
4. **Bounded Buffers**: Circular ring buffers strictly cap memory at 1,000 actions per opponent with explicit overwrite accounting.
