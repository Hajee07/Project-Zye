# ZYE AI — DAY 33 PRE-IMPLEMENTATION AUDIT
## HYBRID LOCAL + WEB SEARCH INTELLIGENCE ENGINE

### 1. Audit Overview
- **Date**: 2026-11-22
- **Phase**: Phase 3 — Big Data Intelligence, Cybersecurity & Engineering R&D Lab
- **Milestone**: Day 33 / 60
- **Scope**: Hybrid Local + Web Search Intelligence, Local Document Retrieval, Live Internet Search, Multi-Source Verification, Intelligent Query Routing, Source Citations, Security & SSRF Protection.

---

### 2. Environment & Dependency Audit
| Library / Engine | Version | Status | Capability / Usage in Day 33 |
|---|---|---|---|
| **Python** | 3.12.x AMD64 | AVAILABLE | Core execution environment |
| **SQLite FTS5** | Built-in | AVAILABLE | High-performance full-text search indexing |
| **httpx** | 0.28.1 | AVAILABLE | Asynchronous/Synchronous HTTP client for live web search and page fetching |
| **lxml** | 6.1.3 | AVAILABLE | High-speed HTML parsing, DOM sanitization, text extraction (`lxml.html`) |
| **pypdf** | 7.1.1 | AVAILABLE | Local PDF extraction, page metadata, text segmentation |
| **python-docx** | 1.2.0 | AVAILABLE | Local DOCX document extraction (paragraphs, tables, headings) |
| **openpyxl** | 3.1.5 | AVAILABLE | Local XLSX spreadsheet extraction (sheets, headers, cells) |
| **pandas** | 3.1.1 | AVAILABLE | Tabular dataset search and dataframe conversion |
| **duckdb** | 2.0.1 | AVAILABLE | SQL database search and analytical queries |
| **sympy** | 1.14.0 | AVAILABLE | Day 32 symbolic mathematics preservation |
| **scipy** | 1.18.1 | AVAILABLE | Day 32 numerical mathematics preservation |
| **playwright** | Available | AVAILABLE | Chrome automation & browser account search fallback |

---

### 3. Existing Repository Capabilities & Reusable Components
1. **Existing FastMCP Server (`computer_intelligence_mcp.py`)**:
   - Currently hosts 28 FastMCP tools (11 Big Data analytics tools + 17 SymPy/SciPy mathematics tools).
   - Day 33 will expand this server by adding 17 search tools (total: 45 tools), maintaining single-point orchestration.
2. **Existing Local Document Handlers**:
   - `zye_personal_assistant/document_engine.py`: Contains basic text snippet extractors for PDF, DOCX, XLSX, CSV, TXT, MD, JSON, and PY.
   - `zye_computer_intelligence/data_engine/dataset_loader.py`: Ingests CSV and Excel files with backend routing.
3. **Existing Browser & Web Capabilities**:
   - `browser_accounts_mcp.py`: Exposes `browser_navigate`, `browser_search`, `browser_extract_page_snapshot`, `browser_summarize_page`.
   - `zye_personal_assistant/research_engine.py`: Defines research depths, prompt injection sanitization patterns, and citation structures.
4. **Existing Job Manager**:
   - `zye_computer_intelligence/security/resource_policy.py`: Hosts `JobManager` and `AnalysisJob` with job states (`QUEUED`, `RUNNING`, `COMPLETED`, `CANCELLED`, `FAILED`).
5. **Existing Security Framework**:
   - `zye_guard.py` & Negative Pre-Mortem Brain: Safety barriers and sensitive path protections.

---

### 4. Gaps Identified & Architectural Solutions
1. **Intelligent Query Intent Routing**:
   - *Gap*: No unified query classifier to decide whether a user's natural query requires `LOCAL_ONLY`, `WEB_ONLY`, `HYBRID`, or `AUTO` search.
   - *Solution*: Implement `SearchQueryPlanner` and `QueryIntentClassifier` with multi-lingual support (Tamil, English, Tanglish).
2. **Local Incremental Full-Text Index**:
   - *Gap*: Files were read on-demand without an incremental SQLite FTS5 index.
   - *Solution*: Implement `LocalIndexManager` with FTS5 virtual table, mtime/hash tracking, and incremental updates.
3. **Live Web Search & Content Extraction**:
   - *Gap*: Need a robust, independent web search provider that does not rely on hardcoded browser UI or external paid API keys.
   - *Solution*: Implement `WebSearchEngine` with provider abstraction (`DuckDuckGoHtmlProvider` / `BrowserSearchProvider`), safe `httpx` transport, and `lxml.html` content extraction.
4. **Web Security & SSRF Protection**:
   - *Gap*: External URLs must not access localhost, internal IPs, cloud metadata endpoints (`169.254.169.254`), or trigger prompt injection.
   - *Solution*: Implement `WebURLSecurityValidator` and `SSRFProtectionPolicy` with IP resolution checks, redirect counters, and size limits.
5. **Multi-Source Evidence Validation & Citations**:
   - *Gap*: Claims from multiple sources need automated corroboration, contradiction detection, and traceable citations.
   - *Solution*: Implement `EvidenceValidationEngine` and `CitationBuilder` producing structured local and web citations.

---

### 5. Implementation Strategy
- Implement package under `zye_computer_intelligence/search/` and security under `zye_computer_intelligence/security/`.
- Extend `computer_intelligence_mcp.py` to register all 17 search tools.
- Update `main.py` dispatcher prefixes.
- Extend `doctor.py` with `--day33-check` diagnostics.
- Add comprehensive test suites under `tests/test_day33_*.py`.
- Ensure 100% zero-regression on Day 30, Day 31, and Day 32 capabilities.
