# Day 33 Quality Assurance & Verification Methodology

## 1. Test Suite Architecture

Day 33 implements seven dedicated automated test suites in `tests/`:

1. **`test_day33_search_security.py` (12 tests):**
   - Path traversal defenses, root boundary enforcement, forbidden extensions, directory pruning.
   - SSRF defenses: localhost, private IP subnets, cloud metadata, non-HTTP protocols, internal domains.
   - Untrusted content guard: adversarial injection detection, HTML tag stripping, truncation.
2. **`test_day33_query_planner.py` (7 tests):**
   - Multilingual intent classification: English, Tamil, Tanglish.
   - Mode assignment (`LOCAL_ONLY`, `WEB_ONLY`, `HYBRID`, `AUTO`).
   - Entity extraction, filter extraction, query expansion.
3. **`test_day33_local_search.py` (7 tests):**
   - Multi-format document extraction (Markdown, Python, CSV, JSON).
   - SQLite FTS5 table initialization, incremental rebuilding, skipping unchanged files.
   - Exact phrase matching, extension filtering, FTS5 boosted queries.
4. **`test_day33_web_search.py` (6 tests):**
   - DOM sanitization, script/style tag dropping, heading and paragraph extraction.
   - DuckDuckGo URL encoding, site filtering, HTML result parsing.
5. **`test_day33_ranking_citations.py` (5 tests):**
   - Schema normalization, URL/path deduplication.
   - Multi-factor relevance scoring with exact phrase bonuses and authority tier boosts.
   - Evidence corroboration, version conflict detection.
   - Markdown footnote formatting and bilingual voice summaries.
6. **`test_day33_hybrid_search.py` (4 tests):**
   - Hybrid search orchestrator execution.
   - In-memory cache TTL hit/miss and invalidation.
   - Cross-source comparison (`compare_local_web_sources`).
7. **`test_day33_search_mcp.py` (9 tests):**
   - FastMCP registration of all 45 unique tools.
   - Tool invocations: `search_local_sources`, `search_local_code`, `get_local_index_status`, `extract_web_content`, `verify_search_evidence`, `get_search_citations`, `refresh_search_results`, `rebuild_local_search_index`.

---

## 2. Test Execution Summary

- **Total Day 33 Tests:** **50 tests**
- **Pass Rate:** **100% (50/50 PASS)**
- **Execution Latency:** **1.007 seconds**
- **Doctor Stage 28 Diagnostics:** **10/10 PASS**
- **Regression Tests (Days 30-32):** **97/97 PASS**
