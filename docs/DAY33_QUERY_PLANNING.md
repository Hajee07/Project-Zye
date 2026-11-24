# Day 33 Query Planning & Multi-Lingual Intent Classification

## 1. Overview

The Search Query Planner (`SearchQueryPlanner`) is the reasoning engine behind ZYE AI's search dispatch. It analyzes user instructions in English, Tamil, and Tanglish, identifies search modality (`LOCAL_ONLY`, `WEB_ONLY`, `HYBRID`, `AUTO`), parses scope (code, documents, tabular datasets), extracts domain filters (`site:python.org`), and expands keyword synonyms to maximize information recall.

---

## 2. Intent Classification Engine

### 2.1 Multi-Lingual Heuristics

The engine natively understands commands across three languages:

1. **English:**
   - `"search my local documents for invoices"` $\rightarrow$ `LOCAL_ONLY`, scope: `DOCUMENTS`.
   - `"search web for python 3.12 release notes"` $\rightarrow$ `WEB_ONLY`, domain: `docs.python.org`.
   - `"compare local budget against online tax rates"` $\rightarrow$ `HYBRID`, comparison: `True`.

2. **Tanglish (Tamil-English Hybrid):**
   - `"laptop la resume enga irukku paaru"` $\rightarrow$ `LOCAL_ONLY`.
   - `"net la python tutorial thedu"` $\rightarrow$ `WEB_ONLY`.
   - `"en documents la report file compare pannu web kooda"` $\rightarrow$ `HYBRID`.

3. **Pure Tamil (Unicode Script):**
   - `"என் கணினியில் உள்ள கோப்புகளை தேடு"` $\rightarrow$ `LOCAL_ONLY`.
   - `"இணையத்தில் புதிய செய்திகளை தேடு"` $\rightarrow$ `WEB_ONLY`.

### 2.2 Entity & Filter Extraction

The planner extracts targeted structural constraints:
- **File Extensions:** Maps user terms (`pdf`, `word`, `excel`, `code`, `python`) to concrete extensions (`.pdf`, `.docx`, `.xlsx`, `.py`).
- **Domain Targeting:** Extracts explicit syntax (`site:example.com`) and infers official documentation portals (e.g. `"official python docs"` $\rightarrow$ `docs.python.org`).
- **Entity Names:** Preserves exact casing for CamelCase and snake_case identifiers (e.g. `DuckDBEngine`, `computer_intelligence_mcp`).

---

## 3. Query Expansion

The `expand_query` method builds keyword variants to enhance recall:
- Generates clean queries without site prefixes for semantic search.
- Constructs site-constrained query variations.
- Synthesizes technical keywords for multilingual queries.
