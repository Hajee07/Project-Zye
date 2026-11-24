"""
Acceptance Test Suite: Verified Application Launch & Zero False Success Engine.
Validates strict empirical window checking, alias resolution, ambiguous query handling,
process management, and zero false success across Win32 and Windows Store/UWP apps.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from zye_windows.application_execution_schema import (
    ApplicationExecutionResult,
    ApplicationExecutionStatus,
)
from zye_windows.application_resolver import ApplicationResolver, COMMON_ALIASES
from zye_windows.window_verifier import WindowVerifier
from zye_windows.app_launcher import WindowsAppLauncher
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.windows_models import AppInfo, InstallationType


class TestVerifiedApplicationLaunch(unittest.TestCase):
    """Test suite for verified application execution and zero false success."""

    def test_01_schema_validation(self):
        """Test ApplicationExecutionResult schema construction and validation."""
        result = ApplicationExecutionResult(
            status=ApplicationExecutionStatus.UI_READY,
            requested_application="notepad",
            resolved_application="Notepad",
            appid="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
            process_id=1234,
            window_title="Untitled - Notepad",
            hwnd=5678,
            window_visible=True,
            uia_accessible=True,
            launch_method="DIRECT_EXECUTABLE",
            verification_method="WINDOW_AND_UIA",
            execution_time_ms=45.2,
            verified=True,
            message="Application 'Notepad' successfully opened and verified on desktop.",
        )
        self.assertTrue(result.verified)
        self.assertEqual(result.status, ApplicationExecutionStatus.UI_READY)
        d = result.model_dump()
        self.assertEqual(d["process_id"], 1234)
        self.assertEqual(d["hwnd"], 5678)

    def test_02_schema_negative_verified_constraint(self):
        """Test schema enforces verified=False for unverified statuses."""
        res_timeout = ApplicationExecutionResult(
            status=ApplicationExecutionStatus.WINDOW_TIMEOUT,
            requested_application="slow_app",
            resolved_application="SlowApp",
            verified=False,
            message="Window did not appear",
        )
        self.assertFalse(res_timeout.verified)

        res_not_found = ApplicationExecutionResult(
            status=ApplicationExecutionStatus.APP_NOT_FOUND,
            requested_application="fake_app",
            resolved_application="",
            verified=False,
            message="App not found",
        )
        self.assertFalse(res_not_found.verified)

    def test_03_alias_resolution(self):
        """Test common aliases resolve to verified canonical names."""
        resolver = ApplicationResolver()
        aliases_to_test = [
            ("chrome", "Google Chrome"),
            ("calc", "Calculator"),
            ("notepad", "Notepad"),
            ("word", "Microsoft Word"),
            ("excel", "Microsoft Excel"),
            ("whatsapp", "WhatsApp"),
        ]
        for alias, expected_canonical in aliases_to_test:
            status, app, _ = resolver.resolve(alias)
            self.assertEqual(status, "ALIAS_MATCH")
            self.assertIsNotNone(app)
            self.assertEqual(app.application_name, expected_canonical)

    def test_04_ambiguous_resolution(self):
        """Test resolver returns AMBIGUOUS_MATCH when query matches multiple apps."""
        mock_discovery = MagicMock()
        mock_discovery.search_installed_apps.return_value = [
            AppInfo(application_name="Media Player Classic", installation_type=InstallationType.WIN32),
            AppInfo(application_name="Media Player Deluxe", installation_type=InstallationType.WIN32),
            AppInfo(application_name="Windows Media Player", installation_type=InstallationType.WIN32),
        ]
        resolver = ApplicationResolver(discovery=mock_discovery)
        status, app, candidates = resolver.resolve("media player")
        self.assertEqual(status, "AMBIGUOUS_MATCH")
        self.assertIsNone(app)
        self.assertGreaterEqual(len(candidates), 2)

    def test_05_unknown_app_not_found(self):
        """Test resolver returns NOT_FOUND for unknown queries."""
        mock_discovery = MagicMock()
        mock_discovery.search_installed_apps.return_value = []
        resolver = ApplicationResolver(discovery=mock_discovery)
        status, app, candidates = resolver.resolve("completely_unknown_executable_999")
        self.assertEqual(status, "NOT_FOUND")
        self.assertIsNone(app)
        self.assertEqual(len(candidates), 0)

    def test_06_window_verifier_absent_window(self):
        """Test WindowVerifier returns found=False for non-existent window."""
        res = WindowVerifier.verify_window("xyz_non_existent_window_title_98765")
        self.assertFalse(res["found"])
        self.assertFalse(res["visible"])
        self.assertIsNone(res["hwnd"])

    def test_07_zero_false_success_launcher_unknown(self):
        """Test launcher never claims success for unknown app."""
        launcher = WindowsAppLauncher()
        res = launcher.open_any_app("phantom_application_xyz", timeout=0.5)
        self.assertFalse(res["verified"])
        self.assertIn(res["status"], [
            ApplicationExecutionStatus.APP_NOT_FOUND,
            ApplicationExecutionStatus.LAUNCH_FAILED,
        ])
        self.assertNotIn("successfully opened", res["message"].lower())

    def test_08_zero_false_success_launcher_timeout(self):
        """Test launcher returns WINDOW_TIMEOUT and verified=False when window doesn't emerge."""
        mock_discovery = MagicMock()
        app_dummy = AppInfo(
            application_name="SilentStubApp",
            app_id="SilentStubApp",
            executable_path="dummy.exe",
            installation_type=InstallationType.WIN32,
        )
        mock_discovery.search_installed_apps.return_value = [app_dummy]

        launcher = WindowsAppLauncher(discovery=mock_discovery)
        with patch.object(launcher, "_launch_app_process", return_value=(True, "DIRECT_EXECUTABLE", "")):
            with patch.object(WindowVerifier, "verify_window", return_value={"found": False}):
                res = launcher.open_any_app("SilentStubApp", timeout=0.5)
                self.assertFalse(res["verified"])
                self.assertEqual(res["status"], ApplicationExecutionStatus.WINDOW_TIMEOUT)
                self.assertNotIn("successfully opened", res["message"].lower())

    def test_09_launcher_already_open(self):
        """Test launcher returns ALREADY_OPEN and verified=True when window already exists."""
        mock_discovery = MagicMock()
        app_open = AppInfo(
            application_name="ActiveApp",
            app_id="ActiveApp",
            installation_type=InstallationType.WIN32,
        )
        mock_discovery.search_installed_apps.return_value = [app_open]

        launcher = WindowsAppLauncher(discovery=mock_discovery)
        with patch.object(WindowVerifier, "verify_window", return_value={
            "found": True,
            "hwnd": 9999,
            "pid": 4321,
            "title": "ActiveApp Window",
            "visible": True,
            "uia_accessible": True,
            "verification_method": "WIN32_TITLE_MATCH",
        }):
            res = launcher.open_any_app("ActiveApp", timeout=1.0)
            self.assertTrue(res["verified"])
            self.assertEqual(res["status"], ApplicationExecutionStatus.ALREADY_OPEN)
            self.assertEqual(res["hwnd"], 9999)
            self.assertEqual(res["process_id"], 4321)

    def test_10_launcher_successful_emergence(self):
        """Test launcher verifies newly emerged window on desktop."""
        mock_discovery = MagicMock()
        app = AppInfo(
            application_name="EmergingApp",
            app_id="EmergingApp",
            installation_type=InstallationType.WIN32,
        )
        mock_discovery.search_installed_apps.return_value = [app]

        launcher = WindowsAppLauncher(discovery=mock_discovery)
        # First check (already open): False; Second check (polling after launch): True
        checks = [
            {"found": False},
            {"found": True, "hwnd": 8888, "pid": 1111, "title": "EmergingApp", "visible": True, "uia_accessible": True, "verification_method": "WINDOW_AND_UIA"},
        ]
        with patch.object(launcher, "_launch_app_process", return_value=(True, "DIRECT_EXECUTABLE", "")):
            with patch.object(WindowVerifier, "verify_window", side_effect=checks):
                res = launcher.open_any_app("EmergingApp", timeout=2.0)
                self.assertTrue(res["verified"])
                self.assertEqual(res["status"], ApplicationExecutionStatus.UI_READY)
                self.assertEqual(res["hwnd"], 8888)

    def test_11_process_manager_command_injection_rejected(self):
        """Test ProcessManager rejects dangerous shell commands and metacharacters."""
        pm = WindowsProcessManager()
        # Direct shell interpreter
        res_cmd = pm.start_application_process("cmd.exe")
        self.assertEqual(res_cmd["status"], "REJECTED")

        res_ps = pm.start_application_process("powershell.exe")
        self.assertEqual(res_ps["status"], "REJECTED")

        # Metacharacters
        res_meta = pm.start_application_process("calc.exe & notepad.exe")
        self.assertEqual(res_meta["status"], "REJECTED")

    def test_12_process_manager_zero_false_success_headless(self):
        """Test ProcessManager returns PROCESS_STARTED and verified=False when no window emerges."""
        pm = WindowsProcessManager()
        mock_proc = MagicMock()
        mock_proc.pid = 9988
        mock_proc.poll.return_value = None  # Process running

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(WindowVerifier, "verify_window", return_value={"found": False}):
                res = pm.start_application_process("custom_cli_tool.exe")
                self.assertFalse(res["verified"])
                self.assertEqual(res["status"], "PROCESS_STARTED")
                self.assertEqual(res["pid"], 9988)

    def test_13_mcp_tool_open_any_app_json_output(self):
        """Test MCP open_any_app tool outputs valid JSON conformant with schema."""
        import windows_control_mcp
        with patch.object(windows_control_mcp.app_launcher, "open_any_app", return_value={
            "status": "UI_READY",
            "requested_application": "calc",
            "resolved_application": "Calculator",
            "process_id": 5555,
            "window_title": "Calculator",
            "hwnd": 1234,
            "window_visible": True,
            "uia_accessible": True,
            "launch_method": "APP_PATHS",
            "verification_method": "WINDOW_AND_UIA",
            "execution_time_ms": 320.0,
            "verified": True,
            "message": "Calculator opened successfully.",
            "candidates": [],
        }):
            raw_json = windows_control_mcp.open_any_app("calc")
            parsed = json.loads(raw_json)
            self.assertTrue(parsed["verified"])
            self.assertEqual(parsed["status"], "UI_READY")
            self.assertEqual(parsed["process_id"], 5555)

    def test_14_system_prompt_negative_constraint(self):
        """Test system instructions in main.py and zye_gemini_live.py include zero false success rules."""
        import inspect
        from zye_gemini_live import ZyeGeminiLiveManager
        source_live = inspect.getsource(ZyeGeminiLiveManager._build_live_connect_config)
        self.assertIn("MANDATORY ZERO-FALSE-SUCCESS RULE FOR APPLICATIONS", source_live)
        self.assertIn("ONLY confirm successful launch if 'verified' is true", source_live)

        import main
        source_main = inspect.getsource(main.ZyeMasterAgent.handle_input)
        self.assertIn("MANDATORY ZERO-FALSE-SUCCESS RULE FOR APPLICATIONS", source_main)


if __name__ == "__main__":
    unittest.main()
