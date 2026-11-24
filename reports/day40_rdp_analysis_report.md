# Day 40 Remote Desktop (RDP) Authentication Analysis Report

## 1. Executive Summary
This report documents the specialized RDP authentication intelligence engine implemented in `RdpAuthAnalyzer` (`zye_cybersecurity/authentication/rdp_auth_analyzer.py`) for Day 40.

## 2. Windows RDP Authentication Significance
Remote Desktop logons are recorded under two primary logon types:
- **LogonType 10 (RemoteInteractive):** Direct RDP session logon via Terminal Services.
- **LogonType 12 (CachedRemoteInteractive):** RDP logon using cached domain credentials.
Because RDP exposed to external networks is an attractive target for initial access and credential guessing, `RdpAuthAnalyzer` isolates and analyzes RDP events independently of console or batch logons.

## 3. Detection & Threat Evaluation
- **Filter:** Isolates events where `LogonType in (10, 12)`.
- **Grouping:** Grouped by `(source_ip, target_account)`.
- **Threshold:** Triggers when failures reach `failure_threshold` (default: 3 attempts).
- **Severity Escalation:** RDP failures are inherently high-risk; any sustained burst escalates immediately to `HIGH` (>=3 attempts) or `CRITICAL` (>=5 attempts).

## 4. Test Verification
Unit tests verified that RDP logons meeting threshold trigger `RDP_AUTH_FAILURE` alerts, while local console (LogonType 2) or network shares (LogonType 3) are excluded from RDP findings.
