# Zye AI — Day 20 FastMCP Tool Reference (`office_master_mcp`)

The `office_master_mcp.py` FastMCP server exposes 12 high-level tools for Microsoft Office automation.

---

## Tool 1: `office_connect`
Connect to a live Microsoft Office application.
- **Parameters:**
  - `app_name` (*str*, required): Target application (`word`, `excel`, `powerpoint`, `outlook`).
  - `connection_policy` (*str*, default: `"ATTACH_EXISTING"`): `ATTACH_EXISTING`, `LAUNCH_NEW`, `AUTO_ATTACH_OR_LAUNCH`, `INSPECT_ONLY`.
- **Returns:**
  - `status`: `"SUCCESS"` or `"ERROR"`
  - `session_id`: Unique session string (e.g. `sess_word_a1b2c3d4`)
  - `connection_type`: `"ATTACH_EXISTING"` or `"LAUNCH_NEW"`
- **Example Voice Command:**
  - *"Connect to Word"* / *"Word app-a attach pannu"*

---

## Tool 2: `office_disconnect`
Disconnect an active Office session and release COM references.
- **Parameters:**
  - `session_id_or_app` (*str*, required): Session ID or app name.
- **Returns:**
  - `status`: `"SUCCESS"` or `"NOT_FOUND"`
  - `message`: Confirmation string.

---

## Tool 3: `office_get_session_details`
Retrieve active session metadata and verify COM responsiveness.
- **Parameters:**
  - `session_id_or_app` (*str*, required): Session ID or app name.
- **Returns:**
  - `session_id`, `app_name`, `prog_id`, `session_status`, `is_live_connected`, `last_accessed_at`.

---

## Tool 4: `office_list_sessions`
List all tracked Office sessions.
- **Parameters:** None.
- **Returns:**
  - `count`: Number of active sessions.
  - `sessions`: List of `OfficeSessionMetadata` records.

---

## Tool 5: `office_inspect_document`
Inspect currently open active document, workbook, presentation, or Outlook folder.
- **Parameters:**
  - `app_name` (*str*, required): `word`, `excel`, `powerpoint`, `outlook`.
  - `max_preview_chars` (*int*, default: `1500`): Maximum characters in text preview.
- **Returns:**
  - Word: `word_count`, `page_count`, `paragraph_count`, `track_changes_active`, `preview_text`.
  - Excel: `sheet_names`, `active_cell`, `active_sheet_name`, `calculation_mode`.
  - PowerPoint: `slide_count`, `active_slide_index`, `slide_titles`.
  - Outlook: `explorer_count`, `inspector_count`, `current_folder_name`, `unread_count`.
- **Example Voice Command:**
  - *"How many words are in my Word document?"* / *"Excel sheet summary sollu"*

---

## Tool 6: `office_execute_operation`
Execute an allowlisted typed operation on a connected Office application.
- **Parameters:**
  - `session_id_or_app` (*str*, required): Session ID or application name.
  - `operation_id` (*str*, required): Allowlisted operation (e.g. `word.insert_text`, `excel.set_cell_value`).
  - `params` (*dict*, optional): Parameter dictionary matching the operation schema.
- **Supported Operations:**
  - `word.insert_text` (`text`, `location`="end"|"selection"|"start")
  - `word.insert_heading` (`text`, `level`=1..9)
  - `word.apply_style` (`style_name`)
  - `word.set_track_changes` (`enabled`=True|False)
  - `word.save_document` (`path` optional)
  - `excel.set_cell_value` (`cell`, `value`, `sheet` optional)
  - `excel.set_cell_formula` (`cell`, `formula`, `sheet` optional)
  - `excel.format_range` (`range_address`, `bold`, `font_size`, etc.)
  - `excel.calculate` ()
  - `excel.save_workbook` (`path` optional)
  - `powerpoint.get_slide_details` (`slide_index`)
  - `powerpoint.insert_slide` (`index`, `layout`)
  - `powerpoint.set_slide_title` (`slide_index`, `title`)
  - `powerpoint.save_presentation` (`path` optional)
  - `outlook.create_draft` (`subject`, `body`, `to`, `cc`, `is_html`)
  - `outlook.get_unread_count` (`folder_name`)

---

## Tool 7: `office_export_pdf`
Export active document, workbook, or presentation directly to PDF.
- **Parameters:**
  - `session_id_or_app` (*str*, required): Target session or app.
  - `output_path` (*str*, required): Destination PDF file path.
  - `overwrite` (*bool*, default: `False`): Confirm overwrite if file exists.
- **Returns:**
  - `success`: `True`
  - `output_path`: Absolute path to created PDF.
  - `file_size_bytes`: Verified size on disk ($> 0$).
  - `pages_exported`: Page/slide count.
- **Example Voice Command:**
  - *"Export this document to PDF as report.pdf"* / *"PDF export pannu"*

---

## Tool 8: `office_accelerate_ribbon`
Execute verified Ribbon hotkeys or menu keytips.
- **Parameters:**
  - `app_name` (*str*, required): `word`, `excel`, `powerpoint`, `outlook`.
  - `action_or_keys` (*str*, required): Predefined action (`save`, `bold`, `italic`, `undo`, `redo`, `find`, `home_tab`, `insert_tab`, `review_tab`, `new_slide`, `new_item`) or key sequence (`ctrl+b`, `alt+h`).
  - `auto_focus` (*bool*, default: `True`): Auto-focus application window if not active.
- **Returns:**
  - `success`: `True`
  - `action`: Name of executed action.

---

## Tool 9: `office_health_check`
Execute non-invasive diagnostic health checks across all Office automation subsystems.
- **Returns:**
  - `status`: `"healthy"` or `"degraded"`
  - `checks`: Results for COM, STA worker, registry, sessions, operations, capabilities, export.

---

## Tool 10: `office_check_installation`
Inspect Windows Registry and process status for Office applications.
- **Parameters:**
  - `app_name` (*str*, optional): Specific app or `None` for all apps.
- **Returns:**
  - `installed_count`: Installed Office apps count.
  - `applications`: Detailed info per application.

---

## Tool 11: `office_list_capabilities`
Query capabilities matrix and version requirements.
- **Parameters:**
  - `app_name` (*str*, optional).
- **Returns:**
  - List or dictionary of capability definitions.

---

## Tool 12: `office_list_operations`
Query allowlisted typed operations and schemas.
- **Parameters:**
  - `app_name` (*str*, optional).
- **Returns:**
  - List of allowlisted operations, parameters, and risk categories.
