# Microsoft Word MCP Operations & Tools Reference — Day 21

## Summary

The `office_master_mcp.py` FastMCP server exposes 52 specialized Microsoft Word tools categorized into 14 functional suites. All operations return structured JSON dictionaries with a canonical `status` field (`SUCCESS`, `ERROR`, `NOT_FOUND`, `BLOCKED`).

---

## 1. Document Lifecycle Suite

### `word_create_document`
- **Description**: Spawns a new blank Microsoft Word document.
- **Parameters**: None.
- **Risk Level**: `LOW_RISK`.
- **Returns**: `{"status": "SUCCESS", "document_name": "Document1", "path": null}`.

### `word_open_document`
- **Description**: Opens an existing document from disk with directory traversal validation.
- **Parameters**: `file_path` (str, required), `read_only` (bool, default `False`).
- **Risk Level**: `LOW_RISK`.

### `word_save_document`
- **Description**: Commits changes to the active document.
- **Parameters**: `path` (str, optional).
- **Risk Level**: `LOW_RISK`.

### `word_save_document_as`
- **Description**: Saves active document under a new path.
- **Parameters**: `file_path` (str, required).
- **Risk Level**: `MEDIUM_RISK`.

### `word_close_document`
- **Description**: Closes active document safely.
- **Parameters**: `save_changes` (bool, default `False`).
- **Risk Level**: `MEDIUM_RISK`.

### `word_inspect_document`
- **Description**: Aggregates comprehensive document metadata and statistics.
- **Parameters**: None.
- **Risk Level**: `READ_ONLY`.

---

## 2. Content & Text Manipulation Suite

### `word_insert_text`
- **Description**: Appends or prepends text with multi-byte Unicode/Tamil support.
- **Parameters**: `text` (str, required), `location` (str: `end`, `start`, `selection`, default `end`).
- **Risk Level**: `LOW_RISK`.

### `word_replace_text`
- **Description**: Finds exact text match and replaces with target text.
- **Parameters**: `old_text` (str, required), `new_text` (str, required), `replace_all` (bool, default `False`).
- **Risk Level**: `HIGH_RISK` (Requires confirmation for bulk replace).

### `word_delete_selected_text`
- **Description**: Removes currently selected range.
- **Parameters**: None.
- **Risk Level**: `HIGH_RISK`.

### `word_insert_page_break`
- **Description**: Inserts a hard page break at cursor position.
- **Risk Level**: `MEDIUM_RISK`.

### `word_insert_section_break`
- **Description**: Inserts a section break (Next Page or Continuous).
- **Parameters**: `break_type` (int, default `2`).
- **Risk Level**: `MEDIUM_RISK`.

---

## 3. Formatting & Typography Suite

### `word_format_text`
- **Description**: Formats font properties (Name, Size, Bold, Italic, Color, Underline).
- **Parameters**: `font_name`, `font_size`, `bold`, `italic`, `underline`, `color`.
- **Risk Level**: `LOW_RISK`.

### `word_format_paragraph`
- **Description**: Sets paragraph alignment (`left`, `center`, `right`, `justify`), line spacing, and margins.
- **Parameters**: `alignment`, `line_spacing`, `space_before`, `space_after`.
- **Risk Level**: `LOW_RISK`.

---

## 4. Style & Corporate Preset Suite

### `word_apply_style`
- **Description**: Applies named style (`Heading 1`, `Normal`, `Title`) to selection.
- **Parameters**: `style_name` (str, required).
- **Risk Level**: `LOW_RISK`.

### `word_create_custom_style`
- **Description**: Defines and saves a custom corporate style in the document catalog.
- **Risk Level**: `MEDIUM_RISK`.

---

## 5. Table Automation Suite

### `word_create_table`
- **Description**: Inserts dynamic table with dimension validation (max 500 rows x 50 columns).
- **Parameters**: `rows` (int), `columns` (int), `autofit` (str), `style` (str).
- **Risk Level**: `MEDIUM_RISK`.

### `word_populate_table`
- **Description**: Writes 2D matrix data into table cells with Unicode preservation.
- **Parameters**: `table_id` (int), `data` (List[List[Any]]).
- **Risk Level**: `MEDIUM_RISK`.

### `word_add_table_row` / `word_delete_table_row`
- **Description**: Appends or removes a 1-based row index.
- **Risk Level**: `MEDIUM_RISK`.

---

## 6. Review & Collaboration Suite

### `word_set_track_changes`
- **Description**: Toggles revision tracking mode.
- **Parameters**: `enabled` (bool, required).
- **Risk Level**: `LOW_RISK`.

### `word_get_revisions`
- **Description**: Lists pending author revisions and edits.
- **Risk Level**: `READ_ONLY`.

### `word_accept_revision` / `word_reject_revision`
- **Description**: Accepts or rejects a single revision by index.
- **Risk Level**: `MEDIUM_RISK`.

### `word_accept_all_revisions` / `word_reject_all_revisions`
- **Description**: Bulk accepts or rejects all revisions.
- **Parameters**: `confirmed` (bool, required `True`).
- **Risk Level**: `HIGH_RISK`.

### `word_add_comment` / `word_get_comments` / `word_resolve_comment`
- **Description**: Review comment lifecycle management.
- **Risk Level**: `LOW_RISK` / `READ_ONLY` / `LOW_RISK`.

---

## 7. Mail Merge Suite

### `word_inspect_mail_merge`
- **Description**: Inspects mail merge fields and active document state.
- **Risk Level**: `READ_ONLY`.

### `word_connect_merge_source`
- **Description**: Binds verified CSV or Excel spreadsheet as data source.
- **Parameters**: `source_path` (str, required).
- **Risk Level**: `MEDIUM_RISK`.

### `word_execute_mail_merge`
- **Description**: Merges data records into new output document.
- **Parameters**: `confirmed` (bool, required `True`).
- **Risk Level**: `HIGH_RISK`.

---

## 8. Export & Accessibility Suite

### `word_export_pdf_advanced`
- **Description**: Native COM PDF export with bookmarks, doc structure tags, and size validation.
- **Parameters**: `output_path` (str, required), `optimize_for_print` (bool, default `True`).
- **Risk Level**: `MEDIUM_RISK`.

### `word_inspect_accessibility` / `word_generate_accessibility_report`
- **Description**: Audits document for WCAG & Section 508 compliance (title, headings, table headers, alt text, link quality).
- **Risk Level**: `READ_ONLY`.
