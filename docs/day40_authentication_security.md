# ZYE AI — Day 40 Documentation: Windows Authentication Security Intelligence

## 1. Overview
The Day 40 module implements an enterprise-grade Windows Authentication Security Intelligence Engine that continuously monitors Windows Security Event ID 4625 ("An account failed to log on"), deciphers low-level NTSTATUS codes and logon types, and recognizes brute-force, password-spraying, distributed, and Remote Desktop (RDP) attack patterns in real time.

## 2. Architectural Architecture
```
+-------------------------------------------------------------+
|              Windows Security Event Log                     |
|           (Event ID 4625: Failed Authentication)            |
+-------------------------------------------------------------+
                              |
                              v  (PowerShell Get-WinEvent FilterHashtable)
+-------------------------------------------------------------+
|              EventRetriever (event_retriever.py)             |
|  - Bounded time window & max events                         |
|  - Subprocess timeout protection (5.0s)                     |
|  - Mock provider injection for offline tests                |
+-------------------------------------------------------------+
                              |
                              v  (Namespace-safe XML ElementTree)
+-------------------------------------------------------------+
|             EventXmlParser (event_xml_parser.py)            |
|  - TargetUserName, IpAddress, Status, SubStatus, LogonType  |
|  - UTC ISO 8601 timestamp normalization                     |
|  - Record ID deduplication                                  |
+-------------------------------------------------------------+
                              |
                              v  (NormalizedAuthEvent instances)
+-------------------------------------------------------------+
|           Multi-Dimensional Pattern Detectors               |
|  1. BruteForceDetector (Single IP -> Single Account)        |
|  2. PasswordSprayDetector (Single IP -> Multiple Accounts)  |
|  3. DistributedAuthDetector (Multiple IPs -> Single Account)|
|  4. RdpAuthAnalyzer (LogonType 10 / 12 Failures)            |
+-------------------------------------------------------------+
                              |
                              v  (Day 39 LAN Device Enrichment)
+-------------------------------------------------------------+
|           AuthSecurityEngine (Master Facade)                |
|  - Cross-references IP against local ARP inventory          |
|  - Cooldown deduplication (10 min)                          |
|  - Writes structured alerts to logs/zye_security_alerts.log |
+-------------------------------------------------------------+
                              |
                              v  (FastMCP & Voice Integration)
+-------------------------------------------------------------+
|  cyber_security_mcp.py  |  main.py Rule 6  |  Live Rule 11  |
+-------------------------------------------------------------+
```

## 3. FastMCP Tools
1. `detect_unauthorized_access(time_window_minutes, threshold_failed_attempts)`: Full audit combining Event ID 4625 failed logins, exposed sensitive listening ports, and socket anomalies.
2. `get_failed_login_events(time_window_minutes, max_events, source_ip, target_account, logon_type)`: Retrieves normalized failed login records with masked usernames and NTSTATUS explanations.
3. `analyze_authentication_patterns(time_window_minutes, brute_force_threshold, password_spray_threshold)`: Identifies active attack signatures across rolling windows.
4. `get_authentication_security_status()`: Diagnostic status of the query engine, audit policy, and cooldown tracker.
5. `get_security_alerts(limit, severity)`: Reads recent security alerts logged to disk.

## 4. Privacy & Safety Standards
- **Zero Fabrication:** Never hallucinates failed logins or security events.
- **Account Masking:** Accounts masked by default (`Administrator` -> `A***r`).
- **Zero Passwords:** Passwords are never collected, logged, or serialized.
- **Zero Raw XML Leakage:** Raw XML is stripped before reaching Gemini.
- **Strictly Detection-Only:** Never modifies firewalls, blocks IPs, or locks accounts automatically.
