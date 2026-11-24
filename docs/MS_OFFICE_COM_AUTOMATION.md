# ZYE AI — Microsoft Office COM Automation Engine

## 1. Architectural Philosophy

The Microsoft Office COM Automation Server (`office_master_mcp.py` & `zye_office/`) exposes **183 tools** covering Word, Excel, PowerPoint, and Outlook. 

**Zero Code Injection Policy**: Unlike naive automation setups that pass raw VBScript or `exec(com_script)`, ZYE AI uses strictly typed Python methods interacting with Windows COM interfaces via `pywin32` / `win32com.client`.

---

## 2. STA Thread Safety & Dispatch Model

COM automation on Windows requires Single-Threaded Apartment (STA) compliance. 
- All COM operations execute on a dedicated STA worker thread (`zye_office/com_worker.py`).
- Every worker initializes COM with `pythoncom.CoInitialize()` and cleans up with `pythoncom.CoUninitialize()`.
- Thread locks prevent cross-thread COM pointer corruption.

---

## 3. Application Capabilities

### 3.1 Microsoft Word
- `word_create_document`, `word_open_document`, `word_insert_text`, `word_format_selection`
- Paragraph styles, headings, tables, hyperlinks, headers/footers
- `word_save_document`, `word_export_pdf`

### 3.2 Microsoft Excel
- `excel_create_workbook`, `excel_open_workbook`
- `excel_set_cell_value`, `excel_set_cell_formula` (with dynamic recalculation)
- Cell formatting, borders, fonts, colors
- Chart creation (Column, Bar, Line, Pie)
- `excel_save_workbook`, `excel_export_pdf`

### 3.3 Microsoft PowerPoint
- `powerpoint_create_presentation`, `powerpoint_open_presentation`
- Slide insertion with predefined layouts (Title, Content, Comparison)
- Shape creation, textbox formatting, image insertion
- `powerpoint_save_presentation`, `powerpoint_export_pdf`

### 3.4 Microsoft Outlook
- `outlook_get_version`, `outlook_create_email_draft`
- Safe draft inspection, recipient validation, subject/body formatting
- Never sends email without explicit secondary authorization.
