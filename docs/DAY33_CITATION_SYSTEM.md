# Day 33 Citation System: Markdown Footnotes & Bilingual Voice

## 1. Overview

The **Citation System (`CitationBuilder`)** establishes end-to-end traceability for every claim ZYE presents. Citations are formatted dynamically for two distinct interfaces:
1. **Desktop Chat UI:** Clean GitHub-Flavored Markdown footnote links and reference sections.
2. **Gemini Live Native Audio:** Ultra-concise, natural spoken citations in Tanglish and English.

---

## 2. Structured Citation Formats

### 2.1 Markdown Citation Formatting

Every search result receives an immutable citation marker:
- **Local Source:** `- **[1]** `filename.py` — `d:/Zye/src/filename.py``
- **Web Source:** `- **[2]** [Page Title](https://example.com) — `example.com``

Footnotes integrate cleanly beneath generated Markdown reports with zero visual clutter.

### 2.2 Bilingual Voice Synthesis

For voice responses, reading raw file paths or lengthy URLs causes unacceptable speech delays. `CitationBuilder.format_voice_citations` synthesizes speech-friendly summaries:

- **Tanglish:**
  > *"Idhuku 3 sources irukku (1 local, 2 web). Mukkiyamana sources: main.py, docs.python.org."*
- **English:**
  > *"Found 3 sources (1 local, 2 web). Key references include: main.py, docs.python.org."*
