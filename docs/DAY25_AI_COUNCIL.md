# Zye AI — Day 25: AI Council Foundation & Parallel Deliberation

The **AI Council Foundation** empowers Zye AI to query multiple frontier and specialized AI models simultaneously, reconcile divergent views, and deliver a deeply balanced final decision to the user.

---

## 1. How the AI Council Works

1. **User Initiation:**
   The user asks a question requiring multi-angle comparison:
   - *"Compare what ChatGPT and Claude think about microservices vs monoliths."*
   - *"Convene the AI council on our database scaling strategy."*
   - *"Ask both ChatGPT and Claude for code review on this algorithm."*

2. **Parallel Dispatch (`asyncio.gather`):**
   `AICouncilEngine` dispatches the query concurrently across the specified council members (defaults to `["chatgpt", "claude"]`, expandable to `ollama`, `perplexity`, `deepseek`, etc.).

3. **Fault-Tolerant Resolution:**
   If one provider encounters an error (e.g. rate limit 429, temporary network timeout), the council **does not crash**. Successful responses from the other members are captured and synthesized.

4. **Perspective Structuring:**
   Each model's perspective is isolated with:
   - Model version used
   - Generated response content
   - Exact latency in milliseconds
   - Token consumption telemetry

5. **Supreme Arbiter Hand-Off to Gemini Master Brain:**
   The aggregated perspectives are packaged into a structured synthesis prompt:
   ```
   === AI COUNCIL DELIBERATION REPORT ===
   Question: ...
   Focus Area: code / security / general / creative / fact_check
   Council Members Queried: chatgpt, claude
   
   --- INDIVIDUAL PERSPECTIVES ---
   [CHATGPT (Model: gpt-4o, Latency: 420ms)]:
   ...
   
   [CLAUDE (Model: claude-3-5-sonnet, Latency: 510ms)]:
   ...
   
   --- SUPREME ARBITER INSTRUCTIONS FOR GEMINI MASTER BRAIN ---
   Review the perspectives above. Reconcile disagreements, verify factual claims,
   and synthesize the definitive final answer for the user. Speak the answer directly.
   ```

6. **Voice Synthesis (Edge-TTS):**
   Gemini reviews the council report, forms the definitive conclusion, and speaks directly to the user in Zye's signature voice (`en-IN-NeerjaNeural`).

---

## 2. Focus Areas

The AI Council supports specialized focus perspectives:

| Focus Area | Deliberation Focus |
| :--- | :--- |
| `general` | Clear, direct, and well-reasoned high-level perspective. |
| `code` | Optimal software engineering, correctness, performance, typing, and safety. |
| `security` | Rigorous threat modeling, vulnerability analysis, and zero-trust verification. |
| `creative` | Divergent brainstorming, innovative solutions, and alternative ideas. |
| `fact_check` | Strict factual verification, assumptions testing, and source analysis. |

---

## 3. FastMCP Tool Interface

```python
# Deliberate across providers
result = await ai_council_compare(
    question="What database should we choose for high-write telemetry?",
    providers=["chatgpt", "claude"],
    focus_area="code",
    max_tokens=1024,
)

# Inspect Council Readiness & Quorum
status = await get_ai_council_status()
```
