# Zye AI — Day 20 Microsoft Office Security & Zero-Trust Governance

## 1. Zero-Trust Security Architecture

Automation of office productivity suites presents serious security risks if exposed to uncontrolled language model execution. Attack vectors include arbitrary macro injection, unauthorized file exfiltration, destructive overwrites, and misdirected keystrokes.

Zye Day 20 enforces a multi-layer defense-in-depth model:

```
[Voice / Prompt Input]
       ↓
[Negative Pre-Mortem Audit & Risk Classification]
       ↓
[Office Operation Allowlist (Zero eval/exec/VBA)]
       ↓
[Canonical Path Validation & Traversal Shield]
       ↓
[Active Foreground Window Verification (Ribbon Hotkeys)]
       ↓
[STA COM Worker Execution]
       ↓
[Post-Execution Verification & Non-Zero Size Audit]
```

---

## 2. Prohibition of Dynamic Code & Unverified VBA

Zye implements strict allowlisting in `OfficeOperationRegistry`:
- **Zero Dynamic Evaluation:** Dynamic Python `eval()`, `exec()`, or `compile()` invocations are strictly prohibited and architecturally impossible.
- **Zero Arbitrary Macros:** Execution of unverified VBA strings, `Application.Run("<macro>")`, or dynamic VBScript is completely disallowed.
- **Strict Parameter Schema:** Every operation must match its registered `ParamDef` types (e.g. `int`, `str`, `bool`) and value boundaries. Unrecognized parameters are rejected immediately.

---

## 3. Canonical Path Validation & Traversal Defense

The `OfficePathValidator` validates all input and output document paths:
1. **Directory Traversal Blocking:** Any path containing `..` or relative parent navigation is rejected with `OfficeSecurityError`.
2. **Authorized Extensions:** Enforces allowed file formats:
   - Word: `.docx`, `.doc`, `.dotx`, `.docm`
   - Excel: `.xlsx`, `.xls`, `.xltx`, `.xlsm`, `.csv`
   - PowerPoint: `.pptx`, `.ppt`, `.potx`, `.pptm`
   - Export: `.pdf`
3. **Workspace Boundary:** Restricts execution to authorized project/data paths when configured.
4. **Destructive Overwrite Gate:** If an export destination already exists, the operation halts and requires explicit user confirmation (`overwrite=True`).

---

## 4. Foreground Window Verification for Ribbon Acceleration

To prevent sending keystrokes to unauthorized background windows (e.g. terminal, browser, password manager), `OfficeRibbonAccelerator` verifies the active foreground window before emitting any key:
1. Queries `win32gui.GetForegroundWindow()` and resolves PID via `win32process.GetWindowThreadProcessId()`.
2. Matches process binary name against `WINWORD.EXE`, `EXCEL.EXE`, `POWERPNT.EXE`, or `OUTLOOK.EXE`.
3. If the target application is not active, attempts one safe restore/focus sequence; if focus cannot be guaranteed, keystroke dispatch is blocked.
4. Filters dangerous key combinations: `alt+f4`, `ctrl+alt+del`, `win`, `delete`.

---

## 5. Outlook Draft Protection

Outlook email operations are restricted to **Draft Creation**:
- `mail.Save()` places the drafted item into the user's `Drafts` folder.
- Under no circumstance does Zye execute `mail.Send()` automatically without explicit secondary user confirmation.
