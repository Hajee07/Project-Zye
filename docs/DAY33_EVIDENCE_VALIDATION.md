# Day 33 Evidence Validation & Conflict Detection

## 1. Overview

The **Evidence Validation Engine (`EvidenceValidationEngine`)** ensures that ZYE AI acts as a grounded, trustworthy research assistant. It corroborates factual assertions across multiple independent local documents and live web pages, establishes confidence tiers, and explicitly alerts the user to version mismatches or conflicting claims.

---

## 2. Validation Mechanism

### 2.1 Corroboration Tiers

Evidence is assigned confidence levels based on source diversity:
- **`HIGH` (`MULTI_SOURCE_CORROBORATED`):** Supported by $\ge 3$ sources spanning both local project files and verified web documentation, with no detected contradictions.
- **`MEDIUM` (`PARTIALLY_CORROBORATED`):** Supported by $\ge 2$ sources, or supported by a single high-authority primary documentation domain (`docs.python.org`, `duckdb.org`).
- **`LOW` (`SINGLE_SOURCE_UNVERIFIED`):** Found in only 1 source.
- **`NONE` (`NO_SOURCES_FOUND`):** No relevant documents retrieved.

### 2.2 Conflict & Version Discrepancy Detection

The engine applies regex pattern matching across snippets to isolate version numbers:
$$\text{Version Pattern: } \backslash\text{bv}?(\backslash\text{d}+\backslash.\backslash\text{d}+(\backslash.\backslash\text{d}+)?)\backslash\text{b}$$
- Identifies if a local project file states an older version (e.g. `v32.0.0`) while online release notes state a newer version (e.g. `v33.0.0`).
- Flags contradictions explicitly in the structured output and generates contextual alerts.
