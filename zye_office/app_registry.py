"""
Office Application Registry & Environment Detection — Zye Day 20.
Inspects Windows Registry for COM ProgIDs, detects installed Microsoft Office applications,
resolves versions, and determines running process counts.
"""

from __future__ import annotations

import logging
import winreg
from typing import Any, Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from zye_office.models import OfficeAppInfo, OfficeAppType

logger = logging.getLogger("zye.office.app_registry")

# Canonical ProgIDs and Executable names for supported Microsoft Office suite
OFFICE_APP_REGISTRY: dict[str, dict[str, Any]] = {
    "word": {
        "prog_id": "Word.Application",
        "display_name": "Microsoft Word",
        "executable": "winword.exe",
        "type": OfficeAppType.WORD,
        "default_capabilities": [
            "inspect_document", "get_word_count", "get_page_count",
            "insert_text", "insert_heading", "apply_style",
            "inspect_track_changes", "set_track_changes", "export_pdf",
        ],
    },
    "excel": {
        "prog_id": "Excel.Application",
        "display_name": "Microsoft Excel",
        "executable": "excel.exe",
        "type": OfficeAppType.EXCEL,
        "default_capabilities": [
            "inspect_workbook", "inspect_worksheet", "inspect_range",
            "get_cell_value", "get_cell_formula", "set_cell_value",
            "set_cell_formula", "format_range", "export_pdf",
        ],
    },
    "powerpoint": {
        "prog_id": "PowerPoint.Application",
        "display_name": "Microsoft PowerPoint",
        "executable": "powerpnt.exe",
        "type": OfficeAppType.POWERPOINT,
        "default_capabilities": [
            "inspect_presentation", "inspect_slides", "get_slide_count",
            "get_slide_titles", "get_active_slide", "get_slide_details",
            "export_pdf",
        ],
    },
    "outlook": {
        "prog_id": "Outlook.Application",
        "display_name": "Microsoft Outlook",
        "executable": "outlook.exe",
        "type": OfficeAppType.OUTLOOK,
        "default_capabilities": [
            "inspect_outlook", "get_application_status", "get_session_details",
            "get_current_explorer", "get_current_folder_metadata",
        ],
    },
}


class OfficeAppRegistry:
    """
    Discovers installed and COM-registered Microsoft Office applications on the Windows host.
    """

    def __init__(self) -> None:
        self._cache: dict[str, OfficeAppInfo] = {}

    def get_supported_office_apps(self) -> list[str]:
        """Return canonical list of supported Office application keys."""
        return list(OFFICE_APP_REGISTRY.keys())

    def get_office_prog_id(self, app_name: str) -> str:
        """Resolve canonical ProgID for application name (case-insensitive)."""
        key = (app_name or "").strip().lower()
        if key in OFFICE_APP_REGISTRY:
            return OFFICE_APP_REGISTRY[key]["prog_id"]
        # Allow passing ProgID directly (e.g. Word.Application)
        for meta in OFFICE_APP_REGISTRY.values():
            if meta["prog_id"].lower() == key:
                return meta["prog_id"]
        return ""

    def check_office_installation(self, app_name: str) -> OfficeAppInfo:
        """
        Check if an Office application's ProgID is registered in the Windows Registry (HKEY_CLASSES_ROOT).
        Also checks whether its associated executable process is currently running.
        """
        key = (app_name or "").strip().lower()
        # Normalize key
        for k, meta in OFFICE_APP_REGISTRY.items():
            if k == key or meta["prog_id"].lower() == key:
                key = k
                break

        if key not in OFFICE_APP_REGISTRY:
            return OfficeAppInfo(
                app_name=app_name,
                prog_id="",
                is_installed=False,
                is_registered=False,
                error=f"Application '{app_name}' is not recognized as a supported Office application.",
            )

        meta = OFFICE_APP_REGISTRY[key]
        prog_id = meta["prog_id"]
        exe_name = meta["executable"]

        # 1. Registry Inspection for ProgID
        is_registered = False
        version_str: Optional[str] = None
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id) as reg_key:
                is_registered = True
                # Try to read CurVer (e.g. Word.Application.16)
                try:
                    with winreg.OpenKey(reg_key, "CurVer") as cur_ver_key:
                        cur_ver, _ = winreg.QueryValueEx(cur_ver_key, "")
                        parts = cur_ver.split(".")
                        if len(parts) >= 3 and parts[-1].isdigit():
                            version_str = f"Office Build {parts[-1]}"
                except Exception:
                    pass
        except OSError:
            is_registered = False

        # 2. Process check
        running_count = 0
        if _PSUTIL_AVAILABLE:
            try:
                for p in psutil.process_iter(["name"]):
                    try:
                        p_name = (p.info.get("name") or "").lower()
                        if p_name == exe_name.lower():
                            running_count += 1
                    except Exception:
                        continue
            except Exception:
                pass

        info = OfficeAppInfo(
            app_name=key,
            prog_id=prog_id,
            is_installed=is_registered,
            is_registered=is_registered,
            version=version_str,
            running_instances=running_count,
            capabilities=list(meta["default_capabilities"]),
        )
        self._cache[key] = info
        return info

    def get_registered_office_apps(self) -> list[OfficeAppInfo]:
        """Scan all supported Office applications and return inventory."""
        return [self.check_office_installation(app) for app in self.get_supported_office_apps()]

    def discover_all(self) -> dict[OfficeAppType, OfficeAppInfo]:
        """Scan all supported Office applications and return dictionary keyed by OfficeAppType."""
        results = {}
        for app_key in self.get_supported_office_apps():
            info = self.check_office_installation(app_key)
            app_type = OFFICE_APP_REGISTRY[app_key]["type"]
            results[app_type] = info
        return results

    def get_office_capabilities(self, app_name: str) -> list[str]:
        """Retrieve allowlisted capability names for an application."""
        info = self.check_office_installation(app_name)
        return list(info.capabilities)

    def get_office_connection_status(self, app_name: str) -> dict[str, Any]:
        """Summary of installation, process state, and ProgID."""
        info = self.check_office_installation(app_name)
        return {
            "status": "SUCCESS" if info.is_registered else "NOT_INSTALLED",
            "app_name": info.app_name,
            "prog_id": info.prog_id,
            "is_installed": info.is_installed,
            "running_instances": info.running_instances,
            "is_running": info.running_instances > 0,
            "version": info.version,
        }
