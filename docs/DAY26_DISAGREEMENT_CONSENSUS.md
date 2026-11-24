# ZYE AI — DAY 26: DISAGREEMENT DETECTION & CONSENSUS ANALYSIS

## 1. Subsystem Purpose & Architecture
When multiple state-of-the-art models analyze complex systems, differences in training data, inductive bias, and alignment guidelines cause conflicting recommendations. The Disagreement and Consensus subsystem (`claim_extractor.py`, `disagreement_detector.py`, `consensus_analyzer.py`) transforms free-form AI responses into structured, verifiable atomic claims to identify points of convergence and divergence.

---

## 2. Claim Extraction & Normalization
Free-form text is parsed sentence by sentence into `NormalizedClaim` objects with the following schema:
- `claim_id`: Deterministic hash (`clm_<md5_prefix>`).
- `provider_id`: Originating model (`chatgpt`, `claude`, `ollama`, etc.).
- `claim_text`: Exact textual assertion.
- `claim_type`: Categorization into:
  - `recommendation`: Architectural advice or proposal.
  - `technical`: Code or framework factual statements.
  - `numerical`: Concrete benchmarks (ms, MB, QPS, %).
  - `security`: Statements regarding vulnerabilities, auth, encryption.
  - `assumption`: Hypotheses or unverified premises.
  - `factual`: Verified facts.
- `topic`: Domain area (`performance`, `scalability`, `security`, `maintainability`, `cost`, `architecture`, `general`).

### Normalization and Deduplication
`normalize_claims()` strips punctuation, canonicalizes whitespace, and unifies identical points asserted across multiple models to avoid redundant reporting.

---

## 3. Disagreement Detection Engine
`detect_disagreements()` executes pairwise comparisons across all models using `classify_disagreement()`:

```
+-------------------------------------------------------------------------------+
|                        DISAGREEMENT SEVERITY TAXONOMY                         |
+----------+---------------------------------------------------+----------------+
| Severity | Trigger Criteria                                  | Resolution Gate|
+----------+---------------------------------------------------+----------------+
| CRITICAL | Conflicting security claims (e.g. "Safe" vs       | Mandatory user |
|          | "Vulnerable to SSRF / RCE")                       | confirmation   |
+----------+---------------------------------------------------+----------------+
| HIGH     | Mutually exclusive architectural recommendations  | Gemini arbiter |
|          | (e.g. "Microservices" vs "Modular Monolith")      | trade-off review|
+----------+---------------------------------------------------+----------------+
| MEDIUM   | Divergent numerical benchmarks or runtime costs   | Evidence tier  |
|          | (e.g. "15ms latency" vs "75ms latency")          | verification   |
+----------+---------------------------------------------------+----------------+
| LOW      | Minor stylistic or idiomatic naming differences    | Information    |
|          | (e.g. "Use pydantic-settings vs dotenv")         | advisory only  |
+----------+---------------------------------------------------+----------------+
```

---

## 4. Consensus Analysis Engine
`analyze_consensus()` computes the aggregate agreement score across all claims:

$$\text{Agreement Ratio} = \frac{\text{Shared Claims}}{\text{Shared Claims} + \text{Unique Claims} + \text{Critical Contradictions}}$$

### Consensus States
1. **FULL_AGREEMENT** ($\ge 0.85$ and 0 contradictions): All models align on key premises and recommendations.
2. **PARTIAL_AGREEMENT** ($0.40 \le \text{Ratio} < 0.85$ and 0 critical contradictions): Core direction is shared, but secondary details or trade-offs diverge.
3. **NO_AGREEMENT** ($< 0.40$): Models offer fundamentally divergent paradigms.
4. **CONTRADICTORY_POSITIONS**: Triggered immediately if any `CRITICAL` severity disagreement is detected, regardless of numerical agreement ratio.

### Preservation of Minority Perspectives
Unlike naive majority-voting systems, the consensus engine preserves unique arguments raised by a single model (e.g. a model warning about a niche memory fragmentation bug in Python sub-interpreters). These minority insights are isolated in `minority_positions` so Gemini Master Brain can give them full analytical consideration.
