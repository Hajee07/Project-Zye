"""
Zye Office Package
Advanced Microsoft Office Live COM Automation Foundation.
"""

from zye_office.models import (
    OfficeAppType,
    ConnectionPolicy,
    SessionStatus,
    RiskCategory,
    OfficeAppInfo,
    OfficeSessionMetadata,
    WordDocumentMetadata,
    ExcelWorkbookMetadata,
    PowerPointPresentationMetadata,
    OutlookSessionMetadata,
    OfficeOperation,
    PDFExportResult,
)
from zye_office.errors import (
    OfficeAutomationError,
    OfficeCOMError,
    OfficeConnectionError,
    OfficeSessionError,
    OfficeOperationError,
    OfficeSecurityError,
    OfficeValidationError,
    OfficeInspectionError,
    OfficeFileExportError,
    format_office_error,
)
from zye_office.path_validator import OfficePathValidator
from zye_office.app_registry import OfficeAppRegistry
from zye_office.com_worker import STACOMWorker, get_shared_sta_worker
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.session_manager import OfficeSessionManager
from zye_office.state_inspector import OfficeStateInspector
from zye_office.capability_registry import OfficeCapabilityRegistry, CapabilityDef
from zye_office.operation_registry import OfficeOperationRegistry, OperationDef, ParamDef
from zye_office.operation_executor import OfficeOperationExecutor
from zye_office.file_exporter import OfficeFileExporter
from zye_office.ribbon_accelerator import OfficeRibbonAccelerator
from zye_office.integration_health import OfficeIntegrationHealth

__all__ = [
    "OfficeAppType",
    "ConnectionPolicy",
    "SessionStatus",
    "RiskCategory",
    "OfficeAppInfo",
    "OfficeSessionMetadata",
    "WordDocumentMetadata",
    "ExcelWorkbookMetadata",
    "PowerPointPresentationMetadata",
    "OutlookSessionMetadata",
    "OfficeOperation",
    "PDFExportResult",
    "OfficeAutomationError",
    "OfficeCOMError",
    "OfficeConnectionError",
    "OfficeSessionError",
    "OfficeOperationError",
    "OfficeSecurityError",
    "OfficeValidationError",
    "OfficeInspectionError",
    "OfficeFileExportError",
    "format_office_error",
    "OfficePathValidator",
    "OfficeAppRegistry",
    "STACOMWorker",
    "get_shared_sta_worker",
    "OfficeCOMRuntime",
    "OfficeSessionManager",
    "OfficeStateInspector",
    "OfficeCapabilityRegistry",
    "CapabilityDef",
    "OfficeOperationRegistry",
    "OperationDef",
    "ParamDef",
    "OfficeOperationExecutor",
    "OfficeFileExporter",
    "OfficeRibbonAccelerator",
    "OfficeIntegrationHealth",
]
