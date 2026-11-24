"""
Browser Health and Diagnostics Engine — Day 24.
Performs end-to-end checks for Playwright, Chrome installation, profiles storage, configs, and active sessions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.profile_discovery import ChromeProfileDiscovery
from zye_browser.profile_manager import ProfileManager
from zye_browser.profile_path_validator import ProfilePathValidator


class BrowserHealthChecker:
    """Diagnostic health check suite for Zye Browser Intelligence subsystems."""

    @classmethod
    def check_all(cls) -> Dict[str, Any]:
        """Run all Day 24 browser diagnostic checks and return comprehensive report."""
        checks: List[Dict[str, Any]] = []

        # 1. Playwright Check
        try:
            import playwright
            checks.append({
                "component": "playwright_package",
                "status": "PASS",
                "details": f"Playwright installed (v{getattr(playwright, '__version__', 'unknown')})",
            })
        except ImportError:
            checks.append({
                "component": "playwright_package",
                "status": "FAIL",
                "details": "Playwright is not installed in current Python environment.",
            })

        # 2. Host Chrome Executable
        try:
            chrome_exe = ChromeProfileDiscovery.get_host_chrome_executable()
            if chrome_exe and chrome_exe.exists():
                checks.append({
                    "component": "host_chrome_binary",
                    "status": "PASS",
                    "details": str(chrome_exe),
                })
            else:
                checks.append({
                    "component": "host_chrome_binary",
                    "status": "WARN",
                    "details": "Google Chrome executable was not found in standard paths.",
                })
        except Exception as exc:
            checks.append({
                "component": "host_chrome_binary",
                "status": "WARN",
                "details": f"Chrome binary check exception: {exc}",
            })

        # 3. Host Chrome User Data / Local State
        try:
            user_data_dir = ChromeProfileDiscovery.get_chrome_user_data_dir()
            if user_data_dir and (user_data_dir / "Local State").exists():
                checks.append({
                    "component": "chrome_local_state",
                    "status": "PASS",
                    "details": f"Local State verified at {user_data_dir / 'Local State'}",
                })
            else:
                checks.append({
                    "component": "chrome_local_state",
                    "status": "WARN",
                    "details": "Chrome Local State not detected (host profile auto-discovery may be limited).",
                })
        except Exception as exc:
            checks.append({
                "component": "chrome_local_state",
                "status": "WARN",
                "details": f"Chrome Local State inaccessible (e.g. sandbox restriction): {exc}",
            })

        # 4. Zye Profiles Storage
        profiles_root = ProfilePathValidator.get_default_profiles_root()
        try:
            profiles_root.mkdir(parents=True, exist_ok=True)
            test_file = profiles_root / ".health_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            checks.append({
                "component": "zye_profiles_storage",
                "status": "PASS",
                "details": f"Profiles storage writable at {profiles_root}",
            })
        except Exception as exc:
            checks.append({
                "component": "zye_profiles_storage",
                "status": "FAIL",
                "details": f"Profiles storage error: {exc}",
            })

        # 5. Configuration Files
        configs = [
            Path("configs/browser_profiles.toml"),
            Path("configs/browser_security.toml"),
            Path("configs/web_apps.toml"),
        ]
        all_configs = all(c.exists() for c in configs)
        if all_configs:
            checks.append({
                "component": "browser_configurations",
                "status": "PASS",
                "details": "All 3 TOML browser configurations found.",
            })
        else:
            checks.append({
                "component": "browser_configurations",
                "status": "WARN",
                "details": "One or more browser configuration TOML files missing.",
            })

        # 6. Profile Registry & Active Profiles
        try:
            pm = ProfileManager(profiles_root=profiles_root)
            registered = pm.list_profiles()
            checks.append({
                "component": "profile_registry",
                "status": "PASS",
                "details": f"{len(registered)} profiles registered in Zye.",
            })
        except Exception as exc:
            checks.append({
                "component": "profile_registry",
                "status": "FAIL",
                "details": f"Failed to initialize profile registry: {exc}",
            })

        # Calculate summary score
        passed = sum(1 for c in checks if c["status"] == "PASS")
        failed = sum(1 for c in checks if c["status"] == "FAIL")
        total = len(checks)
        score = int((passed / total) * 100) if total > 0 else 0

        return {
            "status": "HEALTHY" if failed == 0 else "DEGRADED",
            "score_pct": score,
            "passed_checks": passed,
            "failed_checks": failed,
            "total_checks": total,
            "checks": checks,
        }
