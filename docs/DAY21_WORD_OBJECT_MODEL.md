# Microsoft Word COM Object Model Architecture Map — Day 21

## Overview

Microsoft Word exposes a comprehensive, hierarchical Component Object Model (COM) interface rooted at `Word.Application`. Zye AI interacts with this hierarchy strictly through late-bound automation (`win32com.client.Dispatch`) hosted in the dedicated STA COM worker thread.

---

## Core COM Hierarchy

```
Word.Application (Top-Level Dispatch)
 │
 ├── Documents (Documents Collection)
 │    │
 │    └── Document (Individual Document Instance)
 │         ├── Content (Range representing entire document story)
 │         ├── Selection (Currently selected text or insertion point)
 │         │    ├── Font (Typography: Name, Size, Bold, Italic, Color)
 │         │    └── ParagraphFormat (Alignment, LineSpacing, SpaceBefore/After)
 │         │
 │         ├── Paragraphs (Collection of Paragraph objects)
 │         │    └── Paragraph
 │         │         ├── Range
 │         │         └── Format / Style
 │         │
 │         ├── Tables (Collection of Table objects)
 │         │    └── Table
 │         │         ├── Rows (Rows Collection: Add, Delete, HeadingFormat)
 │         │         ├── Columns (Columns Collection)
 │         │         └── Cell(row, col) (Individual Cell Range & Text)
 │         │
 │         ├── Sections (Collection of Section objects)
 │         │    └── Section
 │         │         ├── PageSetup (Orientation, Margins, PaperSize)
 │         │         ├── Headers (Primary, FirstPage, EvenPages)
 │         │         └── Footers (Primary, FirstPage, EvenPages)
 │         │
 │         ├── TablesOfContents (TOC Collection: Add, Update)
 │         ├── Bookmarks (Named bookmarks collection: Add, Delete, Exists)
 │         ├── Hyperlinks (Hyperlinks collection: Add, Delete, Range)
 │         ├── Revisions (Track Changes revisions: Accept, Reject, AcceptAll)
 │         ├── Comments (Review comments: Add, Delete, Scope, Done)
 │         ├── Fields (Dynamic fields: Page, NumPages, Date, Time, TOC)
 │         ├── MailMerge (Mail Merge engine: OpenDataSource, Execute)
 │         └── BuiltInDocumentProperties (Title, Author, Subject, Keywords)
```

---

## Key COM Enumerations (`wdConstants`)

| Enumeration Group | Constant Name | Value | Purpose |
|---|---|---|---|
| **Save Behavior** | `wdDoNotSaveChanges` | `0` | Discard document changes on close |
| | `wdSaveChanges` | `-1` | Commit document changes on close |
| | `wdPromptToSaveChanges` | `-2` | Display user prompt to save changes |
| **Export Formats** | `wdExportFormatPDF` | `17` | Native high-fidelity PDF export |
| | `wdFormatDocumentDefault` | `16` | Standard .docx document format |
| **Paragraph Alignment** | `wdAlignParagraphLeft` | `0` | Left-aligned text |
| | `wdAlignParagraphCenter` | `1` | Centered text |
| | `wdAlignParagraphRight` | `2` | Right-aligned text |
| | `wdAlignParagraphJustify` | `3` | Justified block text |
| **Page Orientation** | `wdOrientPortrait` | `0` | Vertical page orientation (8.5x11 / A4) |
| | `wdOrientLandscape` | `1` | Horizontal page orientation (11x8.5 / A4) |
| **Paper Sizes** | `wdPaperLetter` | `0` | Standard Letter size (8.5 x 11 in) |
| | `wdPaperLegal` | `4` | Legal size (8.5 x 14 in) |
| | `wdPaperA4` | `7` | ISO A4 size (210 x 297 mm) |
| | `wdPaperA3` | `6` | ISO A3 size (297 x 420 mm) |
| **Breaks** | `wdPageBreak` | `7` | Hard page break |
| | `wdSectionBreakNextPage` | `2` | Section break advancing to next page |
| | `wdSectionBreakContinuous` | `3` | Section break within same page |
| **Fields** | `wdFieldPage` | `33` | Current page number field |
| | `wdFieldNumPages` | `26` | Total document pages count field |
| | `wdFieldDate` | `31` | Dynamic current date field |
| | `wdFieldTOC` | `13` | Dynamic Table of Contents field |
| **Header/Footer Types**| `wdHeaderFooterPrimary` | `1` | Default main document header/footer |
| | `wdHeaderFooterFirstPage` | `2` | Dedicated first-page header/footer |
| | `wdHeaderFooterEvenPages` | `3` | Even-pages header/footer for duplexing |

---

## Safety Guidelines for COM Interop

1. **Range Collapsing**: Before inserting text at document boundaries, always call `range.Collapse(0)` (`wdCollapseEnd = 0`) to prevent overwriting existing content.
2. **Collection Bounds**: Word COM collections are **1-based** (`1..Count`). Indexing at `0` raises a COM exception `0x8002000B` (`DISP_E_BADINDEX`).
3. **Property Verification**: Check `hasattr()` or catch COM exceptions when accessing version-dependent properties (e.g. `Comment.Done` introduced in Word 2013).
