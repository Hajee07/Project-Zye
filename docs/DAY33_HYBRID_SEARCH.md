# Day 33 Hybrid Search Orchestrator & Cross-Source Comparison

## 1. Overview

The **Hybrid Search Engine (`HybridSearchEngine`)** coordinates local and web information retrieval into a single coherent workflow. When answering user queries, it automatically decides whether to query local files, the live web, or both, synthesizes the results, corroborates facts, and generates unified citations.

---

## 2. Execution Flow

1. **Intent Analysis:** The `SearchQueryPlanner` evaluates the query and assigns a `SearchMode`:
   - `LOCAL_ONLY`: Executes only `LocalSearchEngine`.
   - `WEB_ONLY`: Executes only `WebSearchEngine`.
   - `HYBRID`: Executes both local and web search concurrently using `asyncio.gather()`.
   - `AUTO`: Dynamically classifies query keywords and routing.
2. **Cache Check:** `SearchCache` verifies if an unexpired result exists for `(query, mode, domain)`. If cached, returns instantly without disk or network I/O.
3. **Concurrent Retrieval:** Queries local files and web pages simultaneously.
4. **Result Normalization:** `SearchResultNormalizer` creates a uniform schema with unique citation IDs (`local_1`, `web_2`).
5. **Relevance Ranking:** `SearchResultRanker` scores and sorts items.
6. **Evidence Corroboration:** `EvidenceValidationEngine` verifies factual consensus and flags discrepancies.
7. **Citation Construction:** `CitationBuilder` formats footnotes and generates bilingual speech summaries.

---

## 3. Cross-Source Comparison: Local vs Web

The `compare_local_web_sources` tool specializes in comparing local project configurations against upstream web documentation:
- **Version Discrepancy Detection:** Regex-based version extractor identifies installed packages vs online releases.
- **Structured Markdown Matrix:** Generates side-by-side comparison tables.
- **Bilingual Alert:** Summarizes findings in Tanglish and English for Gemini Live voice alerts.

---

## 4. MCP Tool Interface

The following tools on `computer_intelligence_mcp` power Hybrid Search:
- `execute_hybrid_search(query, search_mode, max_results, force_refresh)`
- `compare_local_web_sources(local_query, web_query, domain_filter)`
- `verify_search_evidence(query, claim)`
- `get_search_citations(query)`
- `refresh_search_results()`
