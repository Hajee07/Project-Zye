# Microsoft Word Mail Merge Automation Specification — Day 21

## 1. Pipeline Overview

Zye AI's Mail Merge Engine provides enterprise automated bulk document generation. The engine validates external data sources, connects them to Word's native MailMerge object model, and executes the merge directly into a new document.

```
 ┌──────────────────┐
 │ Data Source File │
 │  (CSV or Excel)  │
 └────────┬─────────┘
          │
          ▼
 ┌───────────────────────────┐
 │ validate_data_source()    │ ─── Validates path, canonicalizes, parses headers,
 │ (Header & Record Preview) │     and counts records.
 └────────┬──────────────────┘
          │
          ▼
 ┌───────────────────────────┐
 │ connect_merge_source()    │ ─── Invokes doc.MailMerge.OpenDataSource()
 │ (Word MailMerge Binding)  │     with LinkToSource=True and ReadOnly=True.
 └────────┬──────────────────┘
          │
          ▼
 ┌───────────────────────────┐
 │ execute_mail_merge()      │ ─── Gated by confirmed=True.
 │ (Merge to New Document)   │     Executes doc.MailMerge.Destination = wdSendToNewDocument.
 └────────┬──────────────────┘
          │
          ▼
 ┌───────────────────────────┐
 │ Merged Output Document    │ ─── Contains completed personalized records, ready
 │                           │     for saving or exporting to high-fidelity PDF.
 └───────────────────────────┘
```

---

## 2. API Reference

### `WordMailMergeEngine.validate_data_source(file_path: str) -> Dict[str, Any]`
- **Validates**: File existence, allowed extension (`.csv`, `.xlsx`, `.xls`), and directory traversal.
- **Extracts**: Column headers (e.g. `["FirstName", "LastName", "Email", "Company"]`).
- **Counts**: Total data records available for merge.

### `WordMailMergeEngine.connect_mail_merge_source(source_path: str) -> Dict[str, Any]`
- **Executes**: Binds the validated source to `doc.MailMerge.OpenDataSource(Name=canonical, LinkToSource=True, ReadOnly=True)`.
- **Returns**: Connected source path, record count, and column names.

### `WordMailMergeEngine.execute_mail_merge(output_dir: Optional[str] = None, confirmed: bool = False) -> Dict[str, Any]`
- **Security Gate**: Requires `confirmed=True`. Attempting merge with `confirmed=False` raises `WordRevisionConfirmationRequiredError`.
- **Destination**: `WD_SEND_TO_NEW_DOCUMENT` (`0`). Produces a new Microsoft Word document containing all merged pages.

---

## 3. Example Voice Workflow

1. User: *"Zye, connect clients.csv to this document for mail merge."*
2. Gemini Brain routes to `word_connect_merge_source(source_path="clients.csv")`.
3. Zye validates CSV, parses 150 records, and binds to active Word document.
4. User: *"Zye, execute the mail merge."*
5. Zye requests confirmation: *"Mail merge will generate 150 personalized letters. Confirm execution?"*
6. User: *"Yes, confirm."*
7. Zye executes `word_execute_mail_merge(confirmed=True)` and announces completion.
