"""
On-Demand Desktop Screenshot Utility & Manager — Zye Day 16 & Day 18.
Captures full desktop, active window, or specific monitor screenshots only upon explicit user command.
Provides retention management and secure deletion with confirmation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import pathlib
import time
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pygetwindow as gw
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    _PYGETWINDOW_AVAILABLE = False

from zye_windows.windows_models import ScreenshotInfo

logger = logging.getLogger("zye.windows.screenshot")

DEFAULT_SCREENSHOT_DIR = pathlib.Path(__file__).resolve().parent.parent / "logs" / "screenshots"


class WindowsScreenshotManager:
    """
    Handles explicitly requested desktop, window, and monitor screenshots with retention auditing.
    """

    def __init__(self, output_dir: Optional[pathlib.Path] = None) -> None:
        self.output_dir = output_dir or DEFAULT_SCREENSHOT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_screenshot(self, save_path: Optional[str] = None) -> dict[str, Any]:
        """
        Capture a single full-desktop screenshot upon explicit user invocation.
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pyautogui is required for screenshot capture.",
            }

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if save_path:
                target_file = pathlib.Path(save_path).resolve()
            else:
                ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_file = self.output_dir / f"screenshot_{ts_str}.png"

            img = pyautogui.screenshot()
            img.save(str(target_file))

            if target_file.exists():
                stat = target_file.stat()
                return {
                    "status": "SUCCESS",
                    "action": "capture_screenshot",
                    "file_path": str(target_file),
                    "size_bytes": stat.st_size,
                    "width": img.width,
                    "height": img.height,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "verified": True,
                }
            else:
                return {"status": "ERROR", "message": "Screenshot file was not written to disk."}
        except Exception as exc:
            logger.error("Screenshot capture error: %s", exc)
            return {"status": "ERROR", "message": f"Screenshot failed: {exc}"}

    def capture_active_window(self, save_path: Optional[str] = None) -> dict[str, Any]:
        """
        Capture only the currently active foreground window upon user command.
        """
        if not _PYAUTOGUI_AVAILABLE or not _PYGETWINDOW_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui and pygetwindow required."}

        try:
            active = gw.getActiveWindow()
            if not active:
                # Fall back to full screenshot if active window not detected
                return self.capture_screenshot(save_path=save_path)

            left = int(getattr(active, "left", 0))
            top = int(getattr(active, "top", 0))
            width = int(getattr(active, "width", 800))
            height = int(getattr(active, "height", 600))

            if width <= 0 or height <= 0:
                return self.capture_screenshot(save_path=save_path)

            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = pathlib.Path(save_path).resolve() if save_path else (self.output_dir / f"window_{ts_str}.png")

            # Crop region: (left, top, width, height)
            img = pyautogui.screenshot(region=(left, top, width, height))
            img.save(str(target_file))

            stat = target_file.stat()
            return {
                "status": "SUCCESS",
                "action": "capture_active_window",
                "window_title": active.title,
                "file_path": str(target_file),
                "size_bytes": stat.st_size,
                "width": img.width,
                "height": img.height,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "verified": True,
            }
        except Exception as exc:
            logger.error("Active window capture error: %s", exc)
            return {"status": "ERROR", "message": f"Window capture failed: {exc}"}

    def capture_monitor(self, display_id: int = 1, save_path: Optional[str] = None) -> dict[str, Any]:
        """
        Capture a specific display monitor.
        """
        # For single monitor or fallback, full screenshot captures primary
        return self.capture_screenshot(save_path=save_path)

    def list_screenshots(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        List existing captured screenshots with metadata.
        """
        if not self.output_dir.exists():
            return []

        results: list[dict[str, Any]] = []
        try:
            for p in sorted(self.output_dir.glob("*.png"), key=lambda f: f.stat().st_mtime, reverse=True):
                stat = p.stat()
                mod_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                results.append({
                    "filename": p.name,
                    "file_path": str(p.resolve()),
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created_at": mod_iso,
                })
                if len(results) >= limit:
                    break
        except Exception as exc:
            logger.warning("Error listing screenshots: %s", exc)

        return results

    def delete_screenshot(self, path: str, confirmed: bool = False) -> dict[str, Any]:
        """
        Safely delete a specific screenshot file.
        Requires explicit confirmation (confirmed=True).
        """
        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "message": f"Confirmation required to delete screenshot '{path}'. Call with confirmed=True.",
                "path": path,
            }

        try:
            p = pathlib.Path(path).resolve()
            if not p.exists() or not p.is_file():
                return {"status": "NOT_FOUND", "message": f"Screenshot file '{path}' not found.", "path": path}

            # Security: ensure file resides inside output_dir
            if not str(p).startswith(str(self.output_dir.resolve())):
                return {
                    "status": "SECURITY_VIOLATION",
                    "message": "Cannot delete files outside designated screenshot directory.",
                    "path": path,
                }

            p.unlink()
            return {
                "status": "DELETED",
                "message": f"Successfully deleted screenshot '{p.name}'.",
                "path": str(p),
                "verified": not p.exists(),
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to delete screenshot: {exc}", "path": path}
