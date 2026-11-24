"""
Zye Windows Automation & Advanced Workspace Control Package — Day 16, Day 17 & Day 18.
Provides comprehensive desktop automation, UI Automation inspection, WhatsApp control,
power management, window snapping/moving/resizing, media control, safe local file searching,
advanced process lifecycle management, virtual desktop switching, multi-monitor coordination,
and privacy-preserving clipboard & dictation utilities.
"""

from __future__ import annotations

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.app_lifecycle import WindowsAppLifecycle
from zye_windows.application_controller import WindowsApplicationController
from zye_windows.application_execution_schema import ApplicationExecutionResult, ApplicationExecutionStatus
from zye_windows.application_resolver import ApplicationResolver
from zye_windows.window_verifier import WindowVerifier
from zye_windows.brightness_manager import WindowsBrightnessManager
from zye_windows.clipboard_manager import WindowsClipboardManager
from zye_windows.display_manager import WindowsDisplayManager
from zye_windows.file_search import WindowsFileSearch
from zye_windows.hardware_manager import WindowsHardwareManager
from zye_windows.input_controller import INPUT_LOCK, NAMED_SHORTCUTS, WindowsInputController
from zye_windows.integration_health import WindowsIntegrationHealth
from zye_windows.media_controller import WindowsMediaController
from zye_windows.os_integration import WindowsOSIntegration
from zye_windows.power_manager import WindowsPowerManager
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.process_monitor import WindowsProcessMonitor
from zye_windows.recycle_bin_manager import WindowsRecycleBinManager
from zye_windows.screenshot_manager import WindowsScreenshotManager
from zye_windows.ui_automation import WindowsUIAutomation
from zye_windows.uia_inspector import WindowsUIAInspector
from zye_windows.uia_interaction import WindowsUIAInteraction
from zye_windows.volume_manager import WindowsVolumeManager
from zye_windows.whatsapp_controller import WhatsAppController
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.workspace_manager import WindowsWorkspaceManager
from zye_windows.windows_models import (
    AppDiscoveryResult,
    AppInfo,
    AppLifecycleStatus,
    BatteryInfo,
    ClipboardMetadata,
    DisplayInfo,
    FileSearchResult,
    InstallationType,
    MediaSessionInfo,
    ProcessInfo,
    ProcessResourceUsage,
    ProcessTree,
    RecycleBinSummary,
    ScreenshotInfo,
    UIControl,
    UIInspectResult,
    VirtualDesktopInfo,
    WhatsAppCallState,
    WhatsAppContact,
    WhatsAppMessage,
    WindowInfo,
)

__all__ = [
    "AppDiscoveryResult",
    "AppInfo",
    "AppLifecycleStatus",
    "ApplicationExecutionResult",
    "ApplicationExecutionStatus",
    "ApplicationResolver",
    "BatteryInfo",
    "ClipboardMetadata",
    "DisplayInfo",
    "FileSearchResult",
    "INPUT_LOCK",
    "InstallationType",
    "MediaSessionInfo",
    "NAMED_SHORTCUTS",
    "ProcessInfo",
    "ProcessResourceUsage",
    "ProcessTree",
    "RecycleBinSummary",
    "ScreenshotInfo",
    "UIControl",
    "UIInspectResult",
    "VirtualDesktopInfo",
    "WhatsAppCallState",
    "WhatsAppContact",
    "WhatsAppController",
    "WhatsAppMessage",
    "WindowInfo",
    "WindowVerifier",
    "WindowsAppCatalog",
    "WindowsAppDiscovery",
    "WindowsAppLauncher",
    "WindowsAppLifecycle",
    "WindowsApplicationController",
    "WindowsBrightnessManager",
    "WindowsClipboardManager",
    "WindowsDisplayManager",
    "WindowsFileSearch",
    "WindowsHardwareManager",
    "WindowsInputController",
    "WindowsIntegrationHealth",
    "WindowsMediaController",
    "WindowsOSIntegration",
    "WindowsPowerManager",
    "WindowsProcessManager",
    "WindowsProcessMonitor",
    "WindowsRecycleBinManager",
    "WindowsScreenshotManager",
    "WindowsUIAutomation",
    "WindowsUIAInspector",
    "WindowsUIAInteraction",
    "WindowsVolumeManager",
    "WindowsWindowManager",
    "WindowsWorkspaceManager",
]
