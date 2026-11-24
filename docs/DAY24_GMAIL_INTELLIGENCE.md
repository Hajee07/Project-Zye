# Zye AI — Day 24: Gmail Web Intelligence Adapter

## 1. Scope & Security Guarantees

The Gmail Web Adapter provides **read-only** extraction of email threads, headers, and bodies via DOM inspection.
- **Zero Email Sending:** Automatic sending is disabled.
- **Zero Email Deletion:** Trash and delete buttons are blocked.
- **Zero Credential Scraping:** Passwords and OAuth tokens are never accessed.

---

## 2. Authentication Gate Detection

If a profile has not authenticated in Gmail, `GmailAdapter` detects the login redirect and raises `GmailLoginRequiredError`:
```json
{
  "status": "ERROR",
  "error_code": "ERR_GMAIL_LOGIN_REQUIRED",
  "message": "Gmail requires manual user login for this profile.",
  "remediation": "Log in to your Google Account once in the opened Chrome window. The session will persist automatically."
}
```

---

## 3. Supported Operations

### `browser_gmail_list_threads(max_results=10, label=None)`
Extracts visible thread rows from inbox or designated label:
- Sender name and address
- Subject line
- Date snippet
- Visible body snippet
- Unread status (`is_unread`)
- Starred status (`is_starred`)
- Attachment indicator (`has_attachments`)

### `browser_gmail_read_thread(index=0)`
Navigates into thread, extracts visible message body, recipients, timestamps, and attachment filenames (bounded to 12,000 characters).

### `browser_gmail_search(query, max_results=10)`
Executes search in Gmail via `input[aria-label="Search mail"]` or hash navigation `#search/<query>`.
