"""
Office Data Models Package — Zye Day 20 & Day 21.
Exposes common Office models alongside specialized Word models.
"""

from zye_office.models.office_models import (
    OfficeAppType,
    ConnectionPolicy,
    SessionStatus,
    RiskCategory,
    OfficeAppInfo,
    OfficeSessionMetadata,
    ExcelWorkbookMetadata,
    PowerPointPresentationMetadata,
    OutlookSessionMetadata,
    OfficeOperation,
    PDFExportResult,
)

from zye_office.models.word_models import (
    WordDocumentMetadata,
    WordFormatOptions,
    WordTableConfig,
    WordPageLayoutConfig,
    WordHeaderFooterConfig,
    WordRevisionItem,
    WordCommentItem,
    WordMailMergeConfig,
    WordAccessibilityIssue,
    WordAccessibilityReport,
)

from zye_office.models.excel_models import (
    ExcelWorkbookMetadata as ExcelWorkbookDetailMetadata,
    ExcelWorksheetMetadata,
    ExcelCellMetadata,
    ExcelRangeData,
    ExcelFormatOptions,
    ExcelConditionalFormattingRule,
    ExcelChartConfig,
    ExcelPivotConfig,
    ExcelTableConfig,
    ExcelDataValidationConfig,
    ExcelSortConfig,
    ExcelFilterConfig,
    ExcelDataCleanConfig,
    ExcelReportConfig,
    ExcelPageSetupConfig,
    ExcelCalculationMode,
    ExcelChartType,
    ExcelPivotAggregation,
)

from zye_office.models.day23_models import (
    PowerPointPresentationMetadata,
    PowerPointSlideMetadata,
    PowerPointShapeMetadata,
    PowerPointTransitionConfig,
    PowerPointAnimationConfig,
    OutlookMailboxSummary,
    OutlookMessageMetadata,
    OutlookDraftConfig,
    OutlookAttachmentMetadata,
    DesktopWindowMetadata,
    DesktopUIControlMetadata,
    DesktopKeyboardSequenceConfig,
)

__all__ = [
    "OfficeAppType",
    "ConnectionPolicy",
    "SessionStatus",
    "RiskCategory",
    "OfficeAppInfo",
    "OfficeSessionMetadata",
    "ExcelWorkbookMetadata",
    "PowerPointPresentationMetadata",
    "OutlookSessionMetadata",
    "OfficeOperation",
    "PDFExportResult",
    "WordDocumentMetadata",
    "WordFormatOptions",
    "WordTableConfig",
    "WordPageLayoutConfig",
    "WordHeaderFooterConfig",
    "WordRevisionItem",
    "WordCommentItem",
    "WordMailMergeConfig",
    "WordAccessibilityIssue",
    "WordAccessibilityReport",
]
