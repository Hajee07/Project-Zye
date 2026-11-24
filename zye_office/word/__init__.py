"""
Microsoft Word Advanced Automation Package — Zye Day 21.
"""

from zye_office.word.word_constants import *
from zye_office.word.word_errors import (
    WordAutomationError,
    WordNotInstalledError,
    WordNoActiveDocumentError,
    WordDocumentNotFoundError,
    WordDocumentProtectedError,
    WordDocumentReadOnlyError,
    WordDocumentIdentityMismatchError,
    WordInvalidRangeError,
    WordTextNotFoundError,
    WordFormattingError,
    WordStyleNotFoundError,
    WordInvalidTableError,
    WordTableSizeExceededError,
    WordLayoutOperationError,
    WordRevisionNotFoundError,
    WordRevisionConfirmationRequiredError,
    WordMailMergeError,
    WordSecurityError,
    WordValidationError,
    format_word_error,
)
from zye_office.word.word_validator import WordValidator
from zye_office.word.word_permissions import WordPermissionEngine, WordRiskLevel
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_document_manager import WordDocumentManager
from zye_office.word.word_content_engine import WordContentEngine
from zye_office.word.word_formatting_engine import WordFormattingEngine
from zye_office.word.word_style_manager import WordStyleManager, STYLE_PRESETS
from zye_office.word.word_table_engine import WordTableEngine, TABLE_STYLE_PRESETS
from zye_office.word.word_header_footer import WordHeaderFooterEngine
from zye_office.word.word_section_manager import WordSectionManager
from zye_office.word.word_page_layout import WordPageLayoutEngine
from zye_office.word.word_list_engine import WordListEngine
from zye_office.word.word_toc_engine import WordTOCEngine
from zye_office.word.word_hyperlink_engine import WordHyperlinkEngine
from zye_office.word.word_bookmark_engine import WordBookmarkEngine
from zye_office.word.word_track_changes import WordTrackChangesEngine
from zye_office.word.word_review_engine import WordReviewEngine
from zye_office.word.word_comment_engine import WordCommentEngine
from zye_office.word.word_mail_merge import WordMailMergeEngine
from zye_office.word.word_metadata import WordMetadataEngine
from zye_office.word.word_accessibility import WordAccessibilityEngine

__all__ = [
    "WordAutomationError",
    "WordNotInstalledError",
    "WordNoActiveDocumentError",
    "WordDocumentNotFoundError",
    "WordDocumentProtectedError",
    "WordDocumentReadOnlyError",
    "WordDocumentIdentityMismatchError",
    "WordInvalidRangeError",
    "WordTextNotFoundError",
    "WordFormattingError",
    "WordStyleNotFoundError",
    "WordInvalidTableError",
    "WordTableSizeExceededError",
    "WordLayoutOperationError",
    "WordRevisionNotFoundError",
    "WordRevisionConfirmationRequiredError",
    "WordMailMergeError",
    "WordSecurityError",
    "WordValidationError",
    "format_word_error",
    "WordValidator",
    "WordPermissionEngine",
    "WordRiskLevel",
    "WordAdapter",
    "WordDocumentManager",
    "WordContentEngine",
    "WordFormattingEngine",
    "WordStyleManager",
    "STYLE_PRESETS",
    "WordTableEngine",
    "TABLE_STYLE_PRESETS",
    "WordHeaderFooterEngine",
    "WordSectionManager",
    "WordPageLayoutEngine",
    "WordListEngine",
    "WordTOCEngine",
    "WordHyperlinkEngine",
    "WordBookmarkEngine",
    "WordTrackChangesEngine",
    "WordReviewEngine",
    "WordCommentEngine",
    "WordMailMergeEngine",
    "WordMetadataEngine",
    "WordAccessibilityEngine",
]
