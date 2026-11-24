# Microsoft Word Automation Security Policy & Zero-Trust Governance — Day 21

## 1. Zero-Trust Security Architecture

Zye AI enforces a strict zero-trust security architecture across all Microsoft Office and Word COM automation. No untrusted prompt, arbitrary code, or unverified script is ever passed directly to the Windows COM runtime or Word dispatch.

```
                      ┌──────────────────────────────┐
                      │    Incoming Agent Request    │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │ Allowlisted Typed Operations │
                      │  (word.* Operation Registry) │
                      └──────────────┬───────────────┘
                                     │
                   ┌─────────────────┴─────────────────┐
                   │                                   │
      Unverified / Arbitrary Code           Allowed Allowlisted Op
                   │                                   │
                   ▼                                   ▼
      ┌──────────────────────────────┐   ┌──────────────────────────────┐
      │   WordSecurityError Raised   │   │     WordPermissionEngine     │
      │   IMMEDIATELY TERMINATED     │   │   Risk Level Classification  │
      └──────────────────────────────┘   └─────────────┬────────────────┘
                                                       │
                 ┌─────────────────────────────────────┼─────────────────────────────────────┐
                 │                                     │                                     │
                 ▼                                     ▼                                     │
          [READ_ONLY / LOW]                      [HIGH_RISK]                                 ▼
                 │                                     │                                [CRITICAL]
                 │                           confirmed == True?                              │
                 │                            /             \                           VBA Macro /
                 │                          Yes              No                        Arbitrary Eval
                 │                          /                 \                              │
                 ▼                         ▼                   ▼                             ▼
        ┌──────────────────┐      ┌──────────────────┐ ┌──────────────────┐        ┌──────────────────┐
        │ Execute on STA   │      │ Execute on STA   │ │ WordSecurityError│        │ WordSecurityError│
        │ COM Worker       │      │ COM Worker       │ │ CONFIRMATION REQ │        │ BLOCKED PERMANENT│
        └──────────────────┘      └──────────────────┘ └──────────────────┘        └──────────────────┘
```

---

## 2. Risk Tier Classification

| Risk Level | Description | Behavior | Operations |
|---|---|---|---|
| `READ_ONLY` | Non-mutating queries of document state | Auto-approved, zero side effects | `inspect_document`, `get_statistics`, `inspect_toc`, `get_revisions`, `get_comments`, `inspect_accessibility` |
| `LOW_RISK` | Standard non-destructive formatting & insertion | Auto-approved with parameter bounds validation | `insert_text`, `format_text`, `format_paragraph`, `apply_style`, `create_bookmark`, `insert_hyperlink`, `save_document` |
| `MEDIUM_RISK` | Structural alterations or file creation | Monitored, parameters validated | `create_table`, `populate_table`, `set_page_margins`, `insert_section_break`, `export_pdf_advanced`, `save_document_as` |
| `HIGH_RISK` | Bulk transformation or deletion of content | Explicit user confirmation required (`confirmed=True`) | `delete_selected_text`, `replace_text` (bulk), `accept_all_revisions`, `reject_all_revisions`, `execute_mail_merge` |
| `CRITICAL` | Remote code execution, unverified scripting, macro runs | **Permanently Blocked Unconditionally** | `word.run_vba_macro`, `word.execute_arbitrary_script`, `word.auto_send_email` |

---

## 3. Defense Mechanisms & Guards

1. **VBA Macro Execution Shield**:
   Word allows embedded VBA macros. Zye strictly prohibits calling `app.Run()` with arbitrary macro strings. Any operation ID matching `word.run_vba_macro` immediately throws `WordSecurityError("WORD_MACRO_EXECUTION_BLOCKED")`.

2. **Canonical Path Traversal Protection**:
   All paths passed to `open_document`, `save_document_as`, `connect_merge_source`, and `create_document_backup` are validated via `OfficePathValidator`:
   - Checks against directory traversal (`..`, `../..`).
   - Restricts extensions strictly to allowlisted document formats (`.docx`, `.doc`, `.docm`, `.dotx`, `.rtf`, `.pdf`, `.csv`, `.xlsx`).
   - Normalizes path separators to canonical Windows paths.

3. **Hyperlink URL Scheme Shield**:
   Hyperlink creation validates the target URL scheme via `urllib.parse`. Only safe protocols (`http`, `https`, `mailto`) are permitted. Dangerous schemes (`javascript:`, `vbscript:`, `file:`, `data:`) throw `WordSecurityError("WORD_UNSAFE_HYPERLINK")`.

4. **Document Identity Verification**:
   Before performing mutative edits, `WordValidator.validate_document_identity()` verifies that the active document's name matches the caller's target document, preventing accidental edits if the user switched active windows.
