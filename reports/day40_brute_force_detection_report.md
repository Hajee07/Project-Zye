# Day 40 Brute-Force Pattern Detection Report

## 1. Executive Summary
This report analyzes the architecture, algorithmic grouping, and detection mechanics of `BruteForceDetector` (`zye_cybersecurity/authentication/brute_force_detector.py`) implemented for Day 40.

## 2. Detection Algorithm
1. **Window Filtering:** Events are evaluated over a configurable sliding time window (default: 5.0 to 15.0 minutes). Older events outside the window boundary are excluded.
2. **Composite Key Grouping:** Events are grouped by composite key `(source_ip, target_account)`.
3. **Threshold Gate:** If `len(attempts) >= attempt_threshold` (default: 3), a `BRUTE_FORCE` finding is synthesized.
4. **Severity Escalation:**
   - Attempt count >= 3x threshold: escalated to `HIGH`.
   - Attempt count >= 2x threshold: escalated to `HIGH`.
   - Any RDP (LogonType 10) brute-force meeting threshold: escalated to `CRITICAL`.
   - Standard burst: `MEDIUM`.

## 3. Test Suite Results
- **Test 21:** Repeated failures against single account (`Admin` from `192.168.1.100` x 6) successfully triggered `BRUTE_FORCE` with HIGH severity.
- **Test 22:** Unrelated failed logins across diverse accounts/IPs below threshold produced 0 false alarms.
- **Test 23:** Sliding window properly expired older events past 10 minutes.
- **Test 24:** RDP repeated failures escalated to CRITICAL severity as specified.
