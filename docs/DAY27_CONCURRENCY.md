# ZYE AI — DAY 27: ADAPTIVE CONCURRENCY & BULKHEAD ISOLATION

## 1. Concurrency Management Architecture
Without active concurrency limits, parallel operations (such as Day 26 Deep AI Council deliberations) can exhaust thread pools, trigger sudden HTTP 429 rate limits, and consume excessive memory.

The Day 27 Concurrency Controller (`zye_ai_plugins/resilience/concurrency_controller.py`) enforces:
1. **Per-Provider Concurrency Semaphores:** Bounded active slots per provider.
2. **Additive Increase / Multiplicative Decrease (AIMD):** Dynamically scales concurrency limits based on measured latency and error feedback.
3. **Bounded Waiting Queues:** Prevents uncontrolled task creation during traffic bursts.

---

## 2. AIMD Adaptive Algorithm

```
+--------------------------------------------------------------------------------+
|                         AIMD CONCURRENCY SCALING RULE                          |
+--------------------------------------------------------------------------------+
| Initial Concurrency: 5 slots                                                   |
| Bounds: Min = 2 slots, Max = 15 slots                                          |
|                                                                                |
| 1. Success Condition (Fast Response < 1500ms):                                 |
|    - Every 5 consecutive fast responses: limit = min(max_limit, limit + 1)     |
|                                                                                |
| 2. Overload / Failure Condition (Timeout, 429, or 503):                        |
|    - Immediate Multiplicative Decrease: limit = max(min_limit, int(limit * 0.7)|
+--------------------------------------------------------------------------------+
```

---

## 3. Backpressure & Queue Bounding
- **Maximum Queue Size:** 30 pending requests per provider pool.
- **Queue Timeout:** 10.0 seconds.
- If all active slots are saturated and the waiting queue hits 30 requests, new requests are rejected immediately with `Queue is full`, signaling backpressure to the caller rather than accumulating unbounded memory.

---

## 4. Bulkhead Isolation Benefits
By isolating provider connection pools:
- A slow model taking 25 seconds to respond will only saturate its own concurrency slots.
- Other models (e.g. fast local Ollama or Groq) continue processing requests in parallel at full speed.
- The user's core voice conversation with Gemini Master Brain remains instantaneous and unaffected.
