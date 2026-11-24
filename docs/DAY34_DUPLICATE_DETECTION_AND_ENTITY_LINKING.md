# ZYE AI — Day 34 Technical Architecture: SHA-256 Deduplication & Entity Linking

## Overview

Day 34 expands Phase 3 (**Big Data Intelligence, Cybersecurity & Engineering R&D Lab**) with two enterprise capabilities:
1. **SHA-256 Duplicate File Detection Engine**: Multi-stage scanning, 1MB chunked streaming hashing, hard-link resolution, zero-collision byte-for-byte verification, and storage reclamation estimation under strict read-only safety.
2. **Cross-Document Entity Linking & Knowledge Graph**: 9-category entity taxonomy, multi-format text extraction, canonical name normalization, disambiguation safeguards, provenance tracking (pages, sheets, lines, sections), and a persistent SQLite entity relationship graph.

---

## 1. SHA-256 Duplicate File Detection Engine

### Architecture & Pipeline
```
[Authorized File Discovery]
            │
            ▼
[Stage 1: Size Partitioning] ──(Unique sizes pruned immediately)
            │
            ▼ (Files sharing exact sizes)
[Stage 2: 1MB Streaming SHA-256] ──(Pre/Post mutation stability validation)
            │
            ▼ (Matching hashes)
[Stage 3: 1MB Streaming Byte Verification] ──(Zero-collision mathematical guarantee)
            │
            ▼
[Stage 4: Filesystem Inode & Hard-Link Resolution]
            │
            ▼
[Storage Reclamation Calculator & Read-Only Audit Report]
```

### Key Modules:
- `zye_computer_intelligence/deduplication/streaming_hasher.py`: 1MB streaming chunking via `hashlib.sha256()`. Detects pre- and post-read file mutations.
- `zye_computer_intelligence/deduplication/file_identity.py`: NTFS/POSIX filesystem identity detection (`dev:ino`). Separates physical files from hard links.
- `zye_computer_intelligence/deduplication/duplicate_candidate_filter.py`: Size partitioning that eliminates ~95% of unique files before computing hashes.
- `zye_computer_intelligence/deduplication/duplicate_verifier.py`: 1MB binary stream verification.
- `zye_computer_intelligence/deduplication/storage_calculator.py`: Reclaimable calculation preventing double-counting of hard links.
- `zye_computer_intelligence/deduplication/duplicate_report_generator.py`: Generates Markdown and JSON audit reports.
- `zye_computer_intelligence/deduplication/sha256_duplicate_engine.py`: High-level facade.

---

## 2. Cross-Document Entity Linking Engine

### 9-Category Entity Taxonomy:
1. `PERSON`: Individuals, engineers, executives, authors (with honorific normalization).
2. `ORGANIZATION`: Corporations, companies, institutes, foundations, teams.
3. `PROJECT`: Initiatives, software systems, projects (e.g., "Project Orion", "ZYE AI").
4. `PRODUCT`: Hardware, software releases, products.
5. `LOCATION`: Cities, facilities, addresses, geographical regions.
6. `TECHNICAL_ENTITY`: Programming languages, frameworks, database engines (Python, DuckDB, FastMCP, SQLite, etc.).
7. `IDENTIFIER`: UUIDs, Git commit hashes, ticket IDs, project codes.
8. `CONTACT_INFO`: Emails, phone numbers, endpoints, URLs.
9. `TEMPORAL_ENTITY`: Dates, quarters, ISO timestamps.

### Disambiguation Safeguards:
- Single first names (e.g. "Ramesh", "Kumar") appearing across distinct documents without corroborating last names, emails, or company context are classified as `AMBIGUOUS`.
- Credential and secret redaction (`EntityPrivacyPolicy`) scrubs API keys and tokens before extraction.

### Persistent Graph Schema (`data/document_entity_graph.db`):
- `documents`: Indexed file metadata and mention counts.
- `entities`: Canonical entities with confidence scores and resolution statuses.
- `entity_mentions`: Fine-grained mentions with page numbers, sheet names, line numbers, and snippets.
- `entity_aliases`: Alternative names and abbreviations.
- `entity_relationships`: Directed semantic relationships between entities and documents.
- `entity_match_candidates`: Candidate match scores and conflict reasons.

---

## 3. FastMCP 66-Tool Suite

`computer_intelligence_mcp.py` exposes 66 tools:
- 11 Big Data Tools (Tools 1–11)
- 17 Mathematical Intelligence Tools (Tools 12–28)
- 17 Hybrid Search Intelligence Tools (Tools 29–45)
- 9 SHA-256 Duplicate File Detection Tools (Tools 46–54)
- 12 Cross-Document Entity Linking Tools (Tools 55–66)
