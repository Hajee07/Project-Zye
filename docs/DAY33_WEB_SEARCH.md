# Day 33 Web Search Intelligence & DOM Extraction

## 1. Overview

The Web Search Engine provides ZYE AI with zero-credential, privacy-preserving live internet search capabilities. It retrieves current documentation, API changes, library release notes, and real-time facts while strictly sandboxing external content to prevent SSRF vulnerabilities and prompt injection exploits.

---

## 2. Key Components

### 2.1 Web Search Provider Abstraction (`BaseWebSearchProvider`)
- Extensible base interface for web search providers.
- **`DuckDuckGoHtmlProvider`:** Default zero-credential search provider. Encodes queries with site filters, user-agent rotation, and parses clean HTML search results into structured objects.

### 2.2 Web Content Extractor (`WebContentExtractor`)
- **HTML DOM Parsing:** Uses `lxml.html` to parse web pages into structured documents.
- **DOM Sanitization:** Strips `<script>`, `<style>`, `<nav>`, `<footer>`, and tracking tags.
- **Content Hierarchy:** Extracts page `<title>`, `<meta name="description">`, headings (`h1`-`h3`), and narrative paragraphs.
- **Safe Fallback:** Emits text excerpts if the HTML structure is non-standard or malformed.

### 2.3 SSRF Protection Policy (`SSRFProtectionPolicy`)
- Validates every URL prior to HTTP dispatch:
  - Protocol whitelist: `http`, `https`.
  - Blocked hostnames: `localhost`, `localhost.localdomain`, `ip6-localhost`.
  - Blocked IP ranges: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (link-local/metadata).
  - Blocked domain suffixes: `.local`, `.internal`, `.lan`, `.corp`, `.home`, `.arpa`.

---

## 3. MCP Tool Interface

The following tools on `computer_intelligence_mcp` interface with Web Search:
- `search_web_sources(query, max_results, domain_filter)`
- `search_web_domain(domain, query, max_results)`
- `fetch_web_page(url, timeout_seconds)`
- `extract_web_content(html_content, url)`
