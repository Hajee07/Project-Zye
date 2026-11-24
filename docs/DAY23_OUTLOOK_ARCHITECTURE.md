# Zye AI — Day 23 Outlook Architecture & COM Model Specification

## 1. Executive Summary

Day 23 introduces native Microsoft Outlook automation using the `Outlook.Application` COM interface on Windows. Unlike offline email clients, Day 23 interacts directly with the active Windows desktop Outlook application, accessing MAPI stores, cached Exchange profiles, and default folders without external network credentials.

---

## 2. Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Zye Main / FastMCP Client                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                Day23MCPIntegrationFacade
                               │
                         OutlookAdapter
                               │
               MAPI Namespace (app.GetNamespace("MAPI"))
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
Mailbox Inspector        Draft Engine           Contact & Task
(Inbox, Counts,          (Save to Drafts,       (Contacts, Tasks,
 Search, Read)            Replies, Forwards)     Calendar Appointments)
                               │
                               ▼
                       OutlookSendEngine
                   (Strict User Confirmation)
                               │
                    mail.Send() (Authorized)
```

---

## 3. Subsystem Breakdown

1. **OutlookAdapter (`zye_office/outlook/outlook_adapter.py`)**:
   - Manages connection lifecycle via `OfficeCOMRuntime`.
   - Default policy is `ConnectionPolicy.ATTACH_EXISTING` to avoid modal login dialog hangs when Outlook is not running.
   - Provides safe access to `MAPI` namespace and default folders (`olFolderInbox`, `olFolderDrafts`, `olFolderCalendar`, etc.).

2. **MailboxInspector (`zye_office/outlook/outlook_mailbox_inspector.py`)**:
   - Queries unread email count, recent message summaries, and folder statistics.

3. **MessageReader & Search (`zye_office/outlook/outlook_message_reader.py`, `outlook_search_engine.py`)**:
   - Searches messages by sender, subject substring, or unread status.
   - Retrieves full message headers, body previews, and attachment manifests.

4. **DraftEngine (`zye_office/outlook/outlook_draft_engine.py`)**:
   - **Draft-First Policy**: All new emails, replies, and forwards are saved immediately to the Drafts folder using `mail.Save()`. Under no circumstances are messages automatically transmitted.

5. **AttachmentManager (`zye_office/outlook/outlook_attachment_manager.py`)**:
   - Attaches files to draft messages. Strictly blocks dangerous executable extensions (`.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, etc.) and enforces a 25MB maximum attachment boundary.

6. **Category & Folder Managers (`zye_office/outlook/outlook_category_manager.py`, `outlook_folder_manager.py`)**:
   - Organizes messages into subfolders and applies color categories.

7. **Contact & Task Management (`zye_office/outlook/outlook_contact_manager.py`)**:
   - Provides address book search, contact creation, task assignment, and calendar appointment scheduling.
