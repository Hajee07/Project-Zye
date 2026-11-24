# Zye AI — Day 21 Advanced Microsoft Word Automation Architecture

## Executive Architecture Summary

Day 21 expands Zye AI's Phase 2 foundation into an **Advanced Microsoft Word Automation and Document Intelligence System**. Built upon the Day 20 Single-Threaded Apartment (STA) COM runtime, Day 21 introduces 22 modular automation engines under `zye_office/word/`, comprehensive Pydantic data schemas under `zye_office/models/`, a unified facade under `zye_office/integration/word_mcp_integration.py`, and 52 registered Word tools on the `office_master_mcp` FastMCP server.

```
                                    ┌────────────────────────┐
                                    │  Natural Voice Command │
                                    │ (Tamil / Tanglish / En)│
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │     Gemini Brain       │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ Master MCP Orchestrator│
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ Negative Pre-Mortem &  │
                                    │ Zero-Trust Permission  │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │  office_master_mcp.py  │
                                    │    (52 Word Tools)     │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ WordMCPIntegration     │
                                    │        Facade          │
                                    └───────────┬────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
                 ▼                              ▼                              ▼
      ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
      │ Document & Content   │      │ Typography & Tables  │      │ Review & Mail Merge  │
      │  - Lifecycle Manager │      │  - Formatting Engine │      │  - Track Changes     │
      │  - Content Engine    │      │  - Style Manager     │      │  - Review Comments   │
      │  - Section Manager   │      │  - Table Engine      │      │  - Mail Merge Engine │
      │  - Page Layout       │      │  - Headers & Footers │      │  - Accessibility     │
      └──────────┬───────────┘      └──────────┬───────────┘      └──────────┬───────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │   Dedicated STA COM    │
                                    │      Worker Thread     │
                                    └───────────┬────────────┘
                                                │ pythoncom / win32com.client
                                                ▼
                                    ┌────────────────────────┐
                                    │ Microsoft Word COM App │
                                    │   (Word.Application)   │
                                    └────────────────────────┘
```

---

## Architectural Principles

1. **Strict STA Apartment Isolation**:
   Every Word COM call (`win32com.client.Dispatch`, `ActiveDocument`, `Selection`, `Content`) is strictly scheduled and executed within the dedicated background Single-Threaded Apartment (STA) COM Worker thread initialized with `pythoncom.CoInitialize()`. No cross-thread COM interface marshaling errors can occur.

2. **Zero-Trust Permission & Risk Gating**:
   Every operation passes through `WordPermissionEngine`:
   - `READ_ONLY`: Document inspection, metadata, statistics, accessibility, review queries (auto-allowed).
   - `LOW_RISK`: Content insertion, font formatting, style application, bookmarks, hyperlinks (auto-allowed with validation).
   - `MEDIUM_RISK`: Saving as new file, table formatting, page margins, sections, review status (validated and logged).
   - `HIGH_RISK`: Text deletion, bulk find-and-replace, bulk revision acceptance/rejection, mail merge execution (gated by explicit `confirmed=True`).
   - `CRITICAL`: Arbitrary Python execution, COM script execution, unverified VBA macro invocation (`word.run_vba_macro`) — strictly and permanently blocked.

3. **ActiveDocument Bounds & Safety**:
   Word COM raises COM HRESULT `0x800401E3` (`Operation unavailable`) if `ActiveDocument` is queried when no document is open (e.g. Word is on its splash/home screen or documents count is 0). All engines safely query `doc.Documents.Count > 0` before touching active document objects.

4. **Unicode & Tamil Script Preservation**:
   All text insertion, find-and-replace, table data, and review comments are passed through `WordValidator.validate_unicode_text()` ensuring lossless UTF-8 roundtripping for Tamil, Tanglish, and multi-byte Unicode glyphs.

---

## Subsystem Engines Overview

| Subsystem Engine | Implementation File | Key Responsibilities |
|---|---|---|
| `WordAdapter` | `zye_office/word/word_adapter.py` | STA worker bridge, connection policy, raw dispatch access. |
| `WordDocumentManager` | `zye_office/word/word_document_manager.py` | Create, open, save, save_as, close, metadata, backup snapshots. |
| `WordContentEngine` | `zye_office/word/word_content_engine.py` | Text insertion, paragraph addition, exact find-and-replace, page breaks. |
| `WordFormattingEngine` | `zye_office/word/word_formatting_engine.py` | Character styles, font sizes, bold, italic, color, paragraph alignment, line spacing. |
| `WordStyleManager` | `zye_office/word/word_style_manager.py` | Built-in styles, corporate presets (`BUSINESS_REPORT`, `ACADEMIC_REPORT`, etc.). |
| `WordTableEngine` | `zye_office/word/word_table_engine.py` | Dynamic tables, matrix data population, cell formatting, row management. |
| `WordHeaderFooterEngine` | `zye_office/word/word_header_footer.py` | Primary and first-page headers/footers, dynamic page numbers. |
| `WordSectionManager` | `zye_office/word/word_section_manager.py` | Section break creation, section queries, unlinking headers from previous. |
| `WordPageLayoutEngine` | `zye_office/word/word_page_layout.py` | Orientation (Portrait/Landscape), paper sizes (A4, Letter, etc.), margins, columns. |
| `WordListEngine` | `zye_office/word/word_list_engine.py` | Bulleted and numbered lists with Unicode preservation. |
| `WordTOCEngine` | `zye_office/word/word_toc_engine.py` | Heading hierarchy inspection, automated Table of Contents insertion and updates. |
| `WordHyperlinkEngine` | `zye_office/word/word_hyperlink_engine.py` | Hyperlink insertion, safe URL scheme validation (HTTP/HTTPS allowed). |
| `WordBookmarkEngine` | `zye_office/word/word_bookmark_engine.py` | Named bookmark creation, validation, queries, and deletion. |
| `WordTrackChangesEngine` | `zye_office/word/word_track_changes.py` | Revision tracking toggle, revision queries, accept/reject gating. |
| `WordReviewEngine` | `zye_office/word/word_review_engine.py` | Document markup summary, review readiness checks. |
| `WordCommentEngine` | `zye_office/word/word_comment_engine.py` | Comment insertion, author tagging, comment queries, resolution, and deletion. |
| `WordMailMergeEngine` | `zye_office/word/word_mail_merge.py` | CSV/Excel data source validation, OpenDataSource binding, merge execution. |
| `WordMetadataEngine` | `zye_office/word/word_metadata.py` | Built-in document properties (Title, Author, etc.) and exact word statistics. |
| `WordAccessibilityEngine` | `zye_office/word/word_accessibility.py` | Compliance audit: titles, headings, table headers, alt text, link quality. |
| `WordPermissionEngine` | `zye_office/word/word_permissions.py` | Zero-trust permission evaluation, risk tiers, confirmation gates. |
| `WordValidator` | `zye_office/word/word_validator.py` | Parameter bounds, table limits (500x50), font sizes, Unicode integrity. |
| `WordMCPIntegrationFacade` | `zye_office/integration/word_mcp_integration.py` | Unified high-level API coordinating all engines and FastMCP dispatch. |
