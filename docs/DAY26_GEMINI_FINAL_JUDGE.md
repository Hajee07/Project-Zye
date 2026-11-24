# ZYE AI — DAY 26: GEMINI MASTER BRAIN SUPREME ARBITER ROLE

## 1. Absolute Sovereign Authority
Within the Zye AI architecture, the Council of external models is **purely advisory**.
- **Gemini is the Supreme Arbiter and sole voice of Zye AI.**
- ChatGPT, Claude, Perplexity, DeepSeek, Groq, and Ollama have **zero authority** to execute system actions, issue final recommendations, or speak directly to the user.
- Any attempt by an external model to assert authority is stripped by the council formatting pipeline.

---

## 2. Supreme Arbiter Deliberation Dossier
When the Council concludes deliberation, `_build_gemini_synthesis_prompt()` generates an exhaustive Dossier:

```text
=== AI COUNCIL SUPREME ARBITER DOSSIER ===
Original Question: {question}
Council Quorum: {N} models queried.

--- INDEPENDENT MODEL PROPOSALS ---
[CHATGPT (Model: gpt-4o, Latency: 110ms) - Chatgpt recommendation]:
...

[CLAUDE (Model: claude-3-5-sonnet, Latency: 140ms) - Claude recommendation]:
...

--- CROSS-EXAMINATION & CRITIQUES ---
[CLAUDE PEER CRITIQUE]:
...

--- DISAGREEMENT MATRIX ---
- [CRITICAL] security: ChatGPT and Claude assert conflicting positions on memory safety.

--- MULTI-CRITERIA DECISION SCORING ---
- Rank 1: Modular Monolith Path (Composite Score: 0.812)
- Rank 2: Microservices Path (Composite Score: 0.745)

--- SUPREME ARBITER INSTRUCTIONS FOR GEMINI MASTER BRAIN ---
Gemini Master Brain is the Supreme Arbiter and sole voice of Zye AI. Review the independent proposals, cross-critiques, and decision ranking above. Reconcile technical disagreements, reject false premises, and synthesize the definitive, authoritative recommendation for the user. Speak the final verdict directly via Edge-TTS (en-IN-NeerjaNeural).
```

---

## 3. Gemini Reconciliation Responsibilities
As the Supreme Arbiter, Gemini executes four specific tasks upon receiving the Dossier:
1. **Reconcile Disagreements:** Review why models disagreed (e.g. ChatGPT emphasized speed while Claude emphasized safety). Evaluate which trade-off matches the user's implicit or explicit constraints.
2. **Reject False Premises:** If a model recommended a deprecated library or invalid security pattern, Gemini explicitly rejects that premise in its synthesis.
3. **Synthesize Optimal Hybrid:** Where appropriate, Gemini blends the best elements of multiple proposals (e.g. adopting Claude's data schema with ChatGPT's caching layer).
4. **Vocal Delivery:** Delivers a concise, natural, spoken response in Tamil, English, or Tanglish through Edge-TTS (`en-IN-NeerjaNeural`).

---

## 4. Voice Persona Protocol 17
`SYSTEM_PERSONA` in `zye_brain/gemini_agent.py` establishes the definitive voice protocol:
- **English Command:** *"Convene the AI council on database architecture"* $\rightarrow$ Invokes `run_ai_council` or `run_quick_council`, presents external opinions as advisory witnesses, and delivers Gemini's final verdict.
- **Tamil Command:** *"AI council kooti andha bug pathi kelunga"* $\rightarrow$ Convenes council, translates consensus and trade-offs into natural Tamil, and speaks Gemini's conclusion.
- **Tanglish Command:** *"ChatGPT and Claude compare panni best solution sollu"* $\rightarrow$ Concurrently queries both, detects contradictions, and speaks the balanced recommendation.
