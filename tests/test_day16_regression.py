"""Day 16 Unit Tests — System Regression & Multi-Day Preservation."""
import importlib
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:
    import toml as tomllib


class TestDay16Regression(unittest.TestCase):
    def test_import_core_modules(self):
        modules = [
            "main",
            "zye_guard",
            "doctor",
            "autonomous_decision_mcp",
            "personal_assistant_mcp",
            "windows_control_mcp",
            "system_os_mcp",
            "zye_windows",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            self.assertIsNotNone(mod, f"Failed to import {mod_name}")

    def test_mcp_servers_registry_in_main(self):
        main_mod = importlib.import_module("main")
        mcp_servers = main_mod.MCP_SERVERS
        self.assertIn("windows_control", mcp_servers)
        self.assertIn("system_os", mcp_servers)
        # Ensure older MCP servers are also preserved
        self.assertIn("autonomous_brain", mcp_servers)
        self.assertIn("personal_assistant", mcp_servers)

    def test_zye_config_has_day16_sections(self):
        cfg_path = Path("zye_config.toml")
        self.assertTrue(cfg_path.exists())
        with open(cfg_path, "rb") as f:
            cfg = tomllib.load(f)
        self.assertIn("windows_control", cfg)
        self.assertIn("system_os", cfg)
        self.assertTrue(cfg["windows_control"].get("enabled", False))
        self.assertTrue(cfg["system_os"].get("enabled", False))

    def test_zye_windows_package_exports(self):
        import zye_windows
        expected_symbols = [
            "WindowsAppDiscovery",
            "WindowsAppLauncher",
            "WindowsWindowManager",
            "WindowsUIAInspector",
            "WindowsUIAInteraction",
            "WindowsInputController",
            "WindowsClipboardManager",
            "WindowsPowerManager",
            "WindowsBrightnessManager",
            "WindowsVolumeManager",
            "WindowsMediaController",
            "WindowsFileSearch",
            "WindowsScreenshotManager",
            "WhatsAppController",
            "WindowsProcessManager",
            "AppInfo",
            "UIControl",
            "UIInspectResult",
            "WindowInfo",
            "WhatsAppContact",
            "WhatsAppMessage",
            "WhatsAppCallState",
            "BatteryInfo",
            "FileSearchResult",
        ]
        for sym in expected_symbols:
            self.assertTrue(hasattr(zye_windows, sym), f"Missing symbol {sym} in zye_windows")

    def test_doctor_has_stage12(self):
        doctor_mod = importlib.import_module("doctor")
        self.assertTrue(hasattr(doctor_mod, "check_day16_windows_automation"))


if __name__ == "__main__":
    unittest.main()
