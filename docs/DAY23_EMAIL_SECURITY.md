# Zye AI — Day 23 Outlook Email Security & Safeguards Specification

## 1. Zero-Trust Security Philosophy

Automated outbound email transmission carries severe organizational and data loss risks. To eliminate accidental sends, prompt injections, or unauthorized transmissions, Day 23 enforces a **Mandatory Two-Stage Authorization Pipeline**:

```
User Voice / MCP Request
         ↓
1. Stage 1: Draft Creation (Always Safe)
   - mail.Save() to Drafts folder
   - Inspect recipients, subject, body, and attachments
   - Return draft entry_id & send preview
         ↓
2. User Review & Confirmation Gate
   - Display summary: To, Subject, Attachment count
   - Await explicit user voice / UI confirmation
         ↓
3. Stage 2: Authorized Transmission
   - Only executed when confirmed=True
   - If confirmed=False, strictly raise OutlookSendConfirmationError!
   - mail.Send() executed
```

---

## 2. Safety Enforcement Implementation

In `zye_office/outlook/outlook_permissions.py`:
```python
class OutlookPermissionEngine:
    @staticmethod
    def enforce_send_confirmation(confirmed: bool) -> None:
        if not confirmed:
            raise OutlookSendConfirmationError(
                "Sending outbound email requires explicit user authorization (confirmed=True)."
            )
```

In `office_master_mcp.py`:
```python
@mcp.tool()
def outlook_send_authorized(entry_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Send an authorized email. Strictly fails if confirmed is not True."""
    _init_subsystems()
    try:
        return _day23_facade.ol_send_authorized(entry_id=entry_id, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="outlook_send_authorized", app_name="outlook")
```

---

## 3. Attachment Shield

- **Dangerous Extensions Filter**: Strictly blocks `.exe`, `.bat`, `.cmd`, `.vbs`, `.ps1`, `.scr`, `.js`, `.hta`, `.pif`.
- **Size Boundary**: Strictly enforces a 25MB maximum per-attachment limit.
- **Path Canonicalization**: Validates that files exist and resolves absolute system paths.
