"""
Data Models & Type Definitions — Zye Day 20 Microsoft Office Live COM Automation.
Pydantic schemas for session metadata, document state, operation registrations, and PDF exports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class OfficeAppType(str, Enum):
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    OUTLOOK = "outlook"
    UNKNOWN = "unknown"


class ConnectionPolicy(str, Enum):
    ATTACH_EXISTING = "ATTACH_EXISTING"
    LAUNCH_NEW = "LAUNCH_NEW"
    AUTO_ATTACH_OR_LAUNCH = "AUTO_ATTACH_OR_LAUNCH"
    INSPECT_ONLY = "INSPECT_ONLY"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class RiskCategory(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class OfficeAppInfo(BaseModel):
    app_name: str
    prog_id: str
    is_installed: bool = False
    is_registered: bool = False
    version: Optional[str] = None
    running_instances: int = 0
    capabilities: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class OfficeSessionMetadata(BaseModel):
    session_id: str
    app_name: str
    prog_id: str
    connection_policy: ConnectionPolicy = ConnectionPolicy.ATTACH_EXISTING
    process_id: int = 0
    active_document_name: Optional[str] = None
    active_document_path: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    session_status: SessionStatus = SessionStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by_zye: bool = False

    @property
    def is_active(self) -> bool:
        return self.session_status == SessionStatus.ACTIVE

    @property
    def app_type(self) -> OfficeAppType:
        try:
            return OfficeAppType(self.app_name.lower())
        except ValueError:
            return OfficeAppType.UNKNOWN


class WordDocumentMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "word"
    filename: Optional[str] = None
    path: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    page_count: int = 0
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    section_count: int = 0
    track_changes_active: bool = False
    preview_text: Optional[str] = None
    message: Optional[str] = None


class ExcelWorkbookMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "excel"
    filename: Optional[str] = None
    path: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    active_sheet_name: Optional[str] = None
    sheet_names: list[str] = Field(default_factory=list)
    active_cell: Optional[str] = None
    selected_range: Optional[str] = None
    used_rows: int = 0
    used_columns: int = 0
    calculation_mode: Optional[str] = None
    message: Optional[str] = None


class PowerPointPresentationMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "powerpoint"
    filename: Optional[str] = None
    path: Optional[str] = None
    is_saved: bool = True
    is_read_only: bool = False
    slide_count: int = 0
    active_slide_index: int = 0
    slide_titles: list[str] = Field(default_factory=list)
    slide_width: float = 0.0
    slide_height: float = 0.0
    message: Optional[str] = None


class OutlookSessionMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "outlook"
    application_version: Optional[str] = None
    is_connected: bool = False
    current_folder_name: Optional[str] = None
    explorer_count: int = 0
    inspector_count: int = 0
    profile_name: Optional[str] = None
    message: Optional[str] = None


class OfficeOperation(BaseModel):
    operation_id: str
    app_name: str
    description: str
    risk_level: RiskCategory = RiskCategory.READ_ONLY
    requires_confirmation: bool = False
    input_schema: dict[str, Any] = Field(default_factory=dict)
    handler_name: str


class PDFExportResult(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "office"
    source_app: Optional[OfficeAppType] = None
    source_document: Optional[str] = None
    output_pdf_path: Optional[str] = None
    output_path: Optional[str] = None
    file_size_bytes: int = 0
    pages_exported: Optional[int] = None
    elapsed_ms: float = 0.0
    success: bool = True
    verified: bool = True
    message: Optional[str] = None
