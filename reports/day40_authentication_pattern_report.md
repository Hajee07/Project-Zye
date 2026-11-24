# Day 40 Authentication Attack Pattern Analysis Report

## 1. Executive Summary
This report details the multi-dimensional pattern analysis engine developed for Day 40 of ZYE AI. The engine evaluates incoming normalized Event ID 4625 authentication events against four distinct attack taxonomies:
1. **Brute-Force Attack Pattern:** Repeated failed authentication against a single account from a single source IP.
2. **Password-Spraying Attack Pattern (1-to-N):** A single source IP attempting logins across multiple distinct target accounts.
3. **Distributed Authentication Attack Pattern (N-to-1):** Multiple distinct source IPs targeting a single victim account.
4. **Remote Desktop (RDP) Authentication Failure Pattern:** Concentrated failed logins over LogonType 10 / 12.

## 2. Classification Taxonomy & Risk Formulation
| Attack Taxonomy | Pattern Signature | Severity Scale | Typical Threshold |
|---|---|---|---|
| **Brute Force** | Single IP -> Single Account | MEDIUM (>=3), HIGH (>=6), CRITICAL (RDP >=3 or >=9) | 3 attempts in 5 min |
| **Password Spray** | Single IP -> >=3 Distinct Accounts | MEDIUM (>=3), HIGH (>=3 in 15 min), CRITICAL (>=6) | 3 accounts in 15 min |
| **Distributed Attack** | >=3 Distinct IPs -> Single Account | HIGH (>=3), CRITICAL (>=5) | 3 IPs in 30 min |
| **RDP Failures** | LogonType 10/12 Remote Attempts | HIGH (>=3), CRITICAL (>=5) | 3 attempts in 30 min |

## 3. LAN Device Enrichment
Detected source IPs are cross-referenced against the Day 39 LAN Device Discovery cache (`_dedup` / `LanScanner`). If a private IP matches an observed ARP device, the hardware MAC, discovery method, and observation status are enriched into the security finding details.

## 4. Verification & Efficacy
Evaluated against synthetic event streams in unit tests (Tests 21–27), achieving 100% detection precision with zero false positives on unrelated baseline failed events.
