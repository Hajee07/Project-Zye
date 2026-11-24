# ZYE AI — DAY 26: EVIDENCE ANALYSIS & UNCERTAINTY QUANTIFICATION

## 1. Subsystem Architecture
LLMs are prone to asserting speculative claims with high linguistic confidence. The Evidence and Uncertainty Analyzer (`zye_ai_plugins/evidence_analyzer.py`) audits model assertions by scanning for empirical validation indicators, detecting linguistic hedge patterns, and isolating unsupported premises.

---

## 2. Linguistic Hedge Phrase Detection
The engine audits text against an extensive corpus of epistemic hedge patterns:
- Hedging phrases: *"maybe", "might", "could possibly", "presumably", "it appears", "seems likely", "to my knowledge", "i believe", "in theory", "assuming that"*.
- When a response relies heavily on hedge phrases, its uncertainty index increases.

---

## 3. Evidence Tiering Taxonomy
Each model response is categorized into one of four qualitative evidence tiers:

```
+-------------------------------------------------------------------------------+
|                            EVIDENCE SUPPORT TIERS                             |
+--------------------------+-----------------------+----------------------------+
| Tier                     | Empirical Indicators  | System Treatment           |
+--------------------------+-----------------------+----------------------------+
| HIGH EVIDENCE SUPPORT    | Numerical benchmarks, | Given highest weight in    |
|                          | official docs cited,  | Gemini synthesis;          |
|                          | 0 hedge phrases       | highly credible            |
+--------------------------+-----------------------+----------------------------+
| MODERATE EVIDENCE SUPPORT| Clear reasoning, code | Solid recommendation with  |
|                          | examples, minimal     | standard validation        |
|                          | hedging               | checks                     |
+--------------------------+-----------------------+----------------------------+
| LOW EVIDENCE SUPPORT     | $\ge 2$ hedge words,  | Flagged for mandatory      |
|                          | vague assertions,     | verification before state  |
|                          | no concrete metrics   | changes                    |
+--------------------------+-----------------------+----------------------------+
| INSUFFICIENT EVIDENCE    | Heavy hedging ($>4$), | Rejected as basis for      |
|                          | contradictory logic,  | operational execution      |
|                          | unverified statements |                            |
+--------------------------+-----------------------+----------------------------+
```

---

## 4. Unsupported Assumption Isolation
`identify_unsupported_assumptions()` scans for ungrounded prerequisites that could cause runtime failures if accepted uncritically:
- Infrastructure assumptions: *"assuming Kubernetes is deployed"*, *"assuming Redis is configured as a cluster"*.
- Data assumptions: *"assuming payload fits in memory"*, *"assuming zero packet loss"*.
- Security assumptions: *"assuming internal network is secure"*.

All isolated assumptions are extracted into a dedicated warning section in the Supreme Arbiter Dossier, alerting Gemini Master Brain to challenge or verify them before advising the user.
