# Day 40 Password-Spraying Detection Report

## 1. Executive Summary
This report analyzes the horizontal password-spraying detection engine implemented in `PasswordSprayDetector` (`zye_cybersecurity/authentication/password_spray_detector.py`) for Day 40 of ZYE AI.

## 2. Horizontal Attack Mechanics & Detection
Password spraying avoids account lockouts by attempting a single common password across multiple distinct accounts rather than bombarding a single account.
- **Aggregation:** Ingested events are grouped by `source_ip`.
- **Set Cardinality Evaluation:** The set of unique target usernames probed by that IP is evaluated: `distinct_accounts = {e.target_username for e in ev_list}`.
- **Threshold Matching:** If `len(distinct_accounts) >= min_distinct_accounts` (default: 3) within the rolling analysis window (15.0 minutes), a `PASSWORD_SPRAY` finding is generated.
- **Severity Formulation:**
  - 3–5 distinct accounts: `HIGH`
  - >= 6 distinct accounts: `CRITICAL`

## 3. Verification & Separation
- **Test 25:** Single source IP (`192.168.1.200`) attempting logins across 4 accounts (`admin`, `root`, `guest`, `test_user`) triggered `PASSWORD_SPRAY` finding with HIGH severity.
- **Test 26:** Multiple failures against a single account did not trigger spraying detector.
- **Test 27:** Distinct IPs attacking separate single accounts did not trigger false spraying alarms.
