"""
Pydantic Data Models for Zye Windows Automation and System OS Control (Day 16).
Provides structured, validated schemas for application discovery, UI elements,
window state, WhatsApp communications, hardware metrics, and file search.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class InstallationType(str, Enum):
    WIN32 = "WIN32"
    STORE = "STORE"
    UWP = "UWP"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


class AppInfo(BaseModel):
    application_name: str
    app_id: str = ""
    installation_type: InstallationType = InstallationType.UNKNOWN
    available: bool = True
    executable_path: Optional[str] = None
    publisher: Optional[str] = None
    launch_target: Optional[str] = None


class AppDiscoveryResult(BaseModel):
    query: str = ""
    count: int = 0
    apps: list[AppInfo] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UIControl(BaseModel):
    name: str = ""
    control_type: str = ""
    automation_id: str = ""
    enabled: bool = True
    visible: bool = True
    rectangle: dict[str, int] = Field(default_factory=dict)
    patterns: list[str] = Field(default_factory=list)
    is_password: bool = False


class UIInspectResult(BaseModel):
    application: str = ""
    window: str = ""
    process_id: int = 0
    hwnd: int = 0
    controls_count: int = 0
    controls: list[UIControl] = Field(default_factory=list)
    truncated: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WindowInfo(BaseModel):
    title: str = ""
    hwnd: int = 0
    process_id: int = 0
    visible: bool = True
    is_minimized: bool = False
    is_maximized: bool = False
    is_active: bool = False
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    monitor_id: Optional[int] = None


class WhatsAppContact(BaseModel):
    name: str
    phone_or_status: str = ""
    is_group: bool = False
    unread_count: int = 0


class WhatsAppMessage(BaseModel):
    recipient: str
    message: str
    status: str = "PENDING"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confirmed: bool = False
    verification: str = ""


class WhatsAppCallState(BaseModel):
    contact: str
    call_type: str = "VOICE"  # VOICE or VIDEO
    status: str = "INITIATED"  # INITIATED, CONNECTED, ENDED, FAILED
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: str = ""


class BatteryInfo(BaseModel):
    percent: float = 0.0
    is_plugged: bool = False
    has_battery: bool = False
    status: str = "UNKNOWN"
    estimated_time_remaining_minutes: Optional[int] = None


class FileSearchResult(BaseModel):
    filename: str
    path: str
    size_bytes: int = 0
    modified_at: str = ""
    containing_folder: str = ""


class ProcessInfo(BaseModel):
    pid: int
    name: str
    ppid: int = 0
    create_time: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    num_threads: int = 0
    status: str = "unknown"
    cmdline: list[str] = Field(default_factory=list)
    is_protected: bool = False


class ProcessTree(BaseModel):
    pid: int
    name: str
    parent: Optional[dict[str, Any]] = None
    children: list[dict[str, Any]] = Field(default_factory=list)
    children_count: int = 0


class ProcessResourceUsage(BaseModel):
    pid: int
    name: str = ""
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    num_threads: int = 0


class AppLifecycleStatus(BaseModel):
    app_name: str
    is_running: bool = False
    process_count: int = 0
    primary_pid: Optional[int] = None
    is_responsive: bool = False
    has_window: bool = False
    window_count: int = 0


# ============================================================================
# Day 18 Data Models: Workspace, Multi-Monitor, Clipboard & Media
# ============================================================================

class DisplayInfo(BaseModel):
    display_id: int
    name: str = ""
    width: int = 0
    height: int = 0
    left: int = 0
    top: int = 0
    is_primary: bool = False
    is_available: bool = True


class VirtualDesktopInfo(BaseModel):
    desktop_id: str
    index: int = 0
    name: str = ""
    is_current: bool = False


class ClipboardMetadata(BaseModel):
    char_count: int = 0
    line_count: int = 0
    word_count: int = 0
    is_empty: bool = True
    has_unicode: bool = False
    has_whitespace: bool = False
    format_type: str = "text/plain"


class MediaSessionInfo(BaseModel):
    session_id: str = ""
    source_app_id: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    playback_status: str = "UNKNOWN"
    can_play: bool = True
    can_pause: bool = True
    can_skip_next: bool = True
    can_skip_previous: bool = True


class ScreenshotInfo(BaseModel):
    file_path: str
    size_bytes: int = 0
    width: int = 0
    height: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified: bool = True


class RecycleBinSummary(BaseModel):
    total_items: int = 0
    total_size_bytes: int = 0
    total_size_mb: float = 0.0
    status: str = "READY"


