"""
Microsoft Outlook Windows COM Constants & Enumerations — Zye Day 23.
"""

from __future__ import annotations


class OutlookConstants:
    """Official Microsoft Outlook Object Model Enumerations."""

    # Item Types (OlItemType)
    olMailItem = 0
    olAppointmentItem = 1
    olContactItem = 2
    olTaskItem = 3
    olJournalItem = 4
    olNoteItem = 5
    olPostItem = 6

    # Default Folders (OlDefaultFolders)
    olFolderDeletedItems = 3
    olFolderOutbox = 4
    olFolderSentMail = 5
    olFolderInbox = 6
    olFolderCalendar = 9
    olFolderContacts = 10
    olFolderJournal = 11
    olFolderNotes = 12
    olFolderTasks = 13
    olFolderDrafts = 16
    olFolderJunk = 23

    # Importance (OlImportance)
    olImportanceLow = 0
    olImportanceNormal = 1
    olImportanceHigh = 2

    # Recipient Types (OlMailRecipientType)
    olTo = 1
    olCC = 2
    olBCC = 3

    # Body Format (OlBodyFormat)
    olFormatUnspecified = 0
    olFormatPlain = 1
    olFormatHTML = 2
    olFormatRichText = 3

    # Save Format (OlSaveAsType)
    olTXT = 0
    olRTF = 1
    olMSG = 3
    olHTML = 5
