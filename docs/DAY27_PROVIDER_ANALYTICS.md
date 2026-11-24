# ZYE AI — DAY 27: PROVIDER HEALTH & PERFORMANCE ANALYTICS

## 1. Analytics & Telemetry Architecture
The Day 27 Telemetry Engine (`zye_ai_plugins/telemetry/`) provides real-time visibility into the operational state and performance of all external and local AI providers.

---

## 2. Formal Health State Taxonomy

```
+------------------+-------------------------------------------------------------+
| Health State     | Description & System Status                                 |
+------------------+-------------------------------------------------------------+
| AVAILABLE        | Fully operational, responding to health probes with low error|
| DEGRADED         | Responding, but with recent intermittent errors or high latency|
| RATE_LIMITED     | Active cooldown in effect due to an upstream HTTP 429 error |
| CIRCUIT_OPEN     | Blocked from receiving requests due to 3 consecutive failures|
| AUTH_FAILED      | Unauthorized (HTTP 401/403) or invalid API key provided     |
| CONFIGURED       | Settings and endpoints present, but not yet probed          |
| DISABLED         | Turned off in configuration (`enabled = false`)             |
| UNKNOWN          | Uninitialized or unmonitored provider                       |
+------------------+-------------------------------------------------------------+
```

---

## 3. Rolling Percentile Latencies
`RollingLatencyTracker` maintains a circular buffer of up to 200 observed response times and calculates:
- **P50 (Median):** Represents typical interactive latency.
- **P90 & P95:** Reflects tail latency under load.
- **P99:** Extreme tail latency used to detect provider degradation.
- **Average (Mean):** Overall arithmetic mean.

---

## 4. Reliability Ranking with Sample-Size Confidence
Naive ranking algorithms often rank a provider with 1 lucky fast request ahead of a battle-tested provider with 10,000 requests at 99.8% uptime.

Zye AI eliminates this flaw by applying **Sample-Size Confidence Damping**:
- $N < 5$ requests: `LOW_SAMPLE_CONFIDENCE`. Score is damped towards a conservative prior ($0.50$).
- $5 \le N < 15$ requests: `MODERATE_SAMPLE_CONFIDENCE`. Minor damping applied.
- $N \ge 15$ requests: `HIGH_SAMPLE_CONFIDENCE`. Fully earned empirical score.

Providers are ranked in descending order of reliability score, breaking ties by P50 latency.
