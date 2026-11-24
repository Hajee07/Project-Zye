# ZYE AI — DAY 27: SMART RATE-LIMIT & COOLDOWN MANAGEMENT

## 1. Rate Limiting Subsystem Purpose
External commercial AI APIs strictly enforce Requests-Per-Minute (RPM) and Tokens-Per-Minute (TPM) quotas. Hitting an unmanaged 429 error wastes roundtrips and degrades user responsiveness.

The Day 27 Rate Limiter (`zye_ai_plugins/resilience/rate_limiter.py`) implements a high-performance **Token Bucket Algorithm** isolated per provider:
- Smooths out bursty requests.
- Tracks estimated prompt and completion tokens prior to network dispatch.
- Enforces an immediate backoff cooldown when an upstream 429 response is encountered.

---

## 2. Token Bucket Implementation
Each provider maintains two independent token buckets:
1. **Request Bucket (RPM):** Replenished at $\frac{\text{RPM}}{60}$ tokens per second up to the RPM limit.
2. **Token Bucket (TPM):** Replenished at $\frac{\text{TPM}}{60}$ tokens per second up to the TPM limit.

Before making an outbound call:
1. `check_capacity(estimated_tokens)` evaluates whether at least 1 request token and $N$ token units are available.
2. If available, `acquire()` consumes the units and proceeds.
3. If insufficient, returns required wait time (e.g. `wait: 1.2s`).

---

## 3. Dynamic 429 Cooldown Enforcement
When an upstream provider returns an HTTP 429 (Too Many Requests):
- The `retry_policy` inspects headers for `Retry-After`.
- The rate limiter calls `trigger_cooldown(cooldown_seconds)`.
- The request bucket is emptied, and the provider enters a hard cooldown lock for the specified duration (default: 15.0 seconds).
- Subsequent calls during the cooldown are rejected or failed over immediately without issuing redundant HTTP requests that would prolong the provider's ban.

---

## 4. Preservation of Gemini Quota Architecture
> [!IMPORTANT]
> The Day 27 Rate Limiter **only manages external advisory AI plugins**.
> Gemini Master Brain's 7-key multi-project quota manager (`zye_brain/gemini_gateway.py`) is completely independent and untouched.
