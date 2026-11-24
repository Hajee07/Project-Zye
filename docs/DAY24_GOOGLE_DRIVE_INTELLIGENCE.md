# Zye AI — Day 24: Google Drive Web Intelligence Adapter

## 1. Scope & Capabilities

The Google Drive Adapter provides **read-only** discovery of files, folders, and documents stored in Google Drive.
- **Read-Only Default:** No file deletions, renames, or permission modifications.
- **Session Preservation:** Once logged in via the persistent context, Drive stays authenticated.

---

## 2. Authentication Gate Detection

If unauthenticated, redirects to `accounts.google.com` raise `DriveLoginRequiredError`, informing the user to sign in once in the opened Chrome window.

---

## 3. Extracted File Metadata

- **`name`**: File or folder display name.
- **`item_type`**: Categorized into `doc`, `sheet`, `slide`, `pdf`, `folder`, or `file`.
- **`owner`**: Displayed owner name.
- **`last_modified`**: Date modified.
- **`url`**: Direct document link.
- **`is_shared`**: Whether shared icon is present.

---

## 4. Supported Operations

- `browser_drive_list_items(max_results=15)`: Reads visible file and folder rows in current folder.
- `browser_drive_search(query, max_results=15)`: Queries Drive search bar (`input[aria-label="Search in Drive"]`) and returns matching item summaries.
