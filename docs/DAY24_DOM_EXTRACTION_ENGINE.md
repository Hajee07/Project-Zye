# Zye AI — Day 24: DOM Content Extraction, Sanitization & AI Synthesis

## 1. Pipeline Overview

```
Active Page DOM
       │
       ▼
innerText Extraction (Scripts & Styles filtered)
       │
       ▼
VisibleTextCleaner
  - Normalize whitespace (limit to 2 newlines)
  - Neutralize Prompt Injections
  - Strip cookie & privacy boilerplate
       │
       ▼
ContentFilter (Optional: urgent, action_items, invoices, keywords)
       │
       ▼
Bounded Snapshot (Default limit: 12,000 characters)
       │
       ▼
Gemini Web Bridge (Central Gemini Gateway)
```

---

## 2. Prompt Injection Neutralization Engine

Scans extracted text for malicious instruction overrides:
- `ignore previous instructions`
- `system prompt override`
- `you are now in developer mode`
- `disregard all prior rules`
- `exfiltrate tokens to ...`

Neutralized matches are replaced with:
`[SAFETY_NEUTRALIZED_UNTRUSTED_CONTENT]`
and the event is flagged for Gemini AI.

---

## 3. Targeted Content Filters

- **Urgent Only (`filter_urgent`):** Isolates paragraphs containing urgency cues (`urgent`, `deadline`, `asap`, `immediate`, `அவசரம்`).
- **Action Items (`filter_action_items`):** Isolates tasks, todo checkboxes, and imperative verbs (`please submit`, `review`, `approve`).
- **Financials & Invoices (`filter_finance_and_invoices`):** Isolates invoice numbers, due dates, and currencies (`$`, `₹`, `eur`, `total amount`).
