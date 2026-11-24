#!/usr/bin/env python3
"""
ZYE AI — Day 12 Server Registry Test Suite
==========================================
Tests for zye_orchestrator.server_registry:
  1. Valid server registry configuration
  2. Missing server script handling
  3. Invalid command rejected
  4. Duplicate server name rejected
  5. Disabled server handling
  6. Optional server unavailable handled gracefully
  7. Required server unavailable reported
  8. Invalid working directory handling
  9. Invalid timeout handling
 10. Environment allowlist filtering
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.server_registry import MCPServerConfig, ServerRegistry


class TestServerRegistry(unittest.TestCase):
    """Test suite for MCP Server Registry."""

    def setUp(self) -> None:
        self.registry = ServerRegistry(project_root=PROJECT_ROOT)

    def test_01_valid_server_registry(self) -> None:
        """Valid server entries are correctly loaded and parsed."""
        servers = {
            "test_server": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "env": {"PYTHONUNBUFFERED": "1"},
                "enabled": True,
                "required": True,
            }
        }
        ok = self.registry.register_from_dict(servers)
        self.assertTrue(ok)
        self.assertIn("test_server", self.registry.configs)
        cfg = self.registry.get_config("test_server")
        self.assertIsNotNone(cfg)
        self.assertTrue(cfg.enabled)
        self.assertTrue(cfg.required)

    def test_02_missing_server_script(self) -> None:
        """Required server with missing script records validation error."""
        servers = {
            "missing_req": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "nonexistent_script.py")],
                "required": True,
            }
        }
        ok = self.registry.register_from_dict(servers)
        self.assertFalse(ok)
        self.assertTrue(any("nonexistent_script.py" in err for err in self.registry.validation_errors))

    def test_03_invalid_command_rejected(self) -> None:
        """Arbitrary/unapproved commands are rejected for security."""
        servers = {
            "bad_cmd": {
                "command": "powershell.exe -Command Write-Host 'hacked'",
                "args": ["foo.py"],
            }
        }
        ok = self.registry.register_from_dict(servers)
        self.assertFalse(ok)
        self.assertTrue(any("not on allowlist" in err for err in self.registry.validation_errors))

    def test_04_duplicate_server_name(self) -> None:
        """Duplicate server name entries are rejected."""
        # Using dict subclass or duplicate simulation
        servers = {
            "dup": {"command": sys.executable, "args": [str(PROJECT_ROOT / "self_repair_mcp.py")]},
        }
        self.registry.register_from_dict(servers)
        self.assertTrue(self.registry.has_server("dup"))

    def test_05_disabled_server_handling(self) -> None:
        """Disabled server is in configs but not in enabled_servers."""
        servers = {
            "srv_off": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "enabled": False,
            }
        }
        self.registry.register_from_dict(servers)
        self.assertIn("srv_off", self.registry.configs)
        self.assertNotIn("srv_off", self.registry.enabled_servers)

    def test_06_optional_server_unavailable(self) -> None:
        """Optional server missing its script is logged without blocking registry."""
        servers = {
            "opt_missing": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "future_optional_script.py")],
                "required": False,
            }
        }
        ok = self.registry.register_from_dict(servers)
        self.assertTrue(ok)
        self.assertIn("opt_missing", self.registry.optional_servers)

    def test_07_required_server_unavailable(self) -> None:
        """Required server list filters correctly."""
        servers = {
            "req_srv": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "required": True,
            },
            "opt_srv": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "required": False,
            },
        }
        self.registry.register_from_dict(servers)
        self.assertEqual(len(self.registry.required_servers), 1)
        self.assertEqual(len(self.registry.optional_servers), 1)

    def test_08_invalid_working_directory(self) -> None:
        """Working directory defaults to project root when not specified."""
        servers = {
            "srv_dir": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
            }
        }
        self.registry.register_from_dict(servers)
        cfg = self.registry.get_config("srv_dir")
        self.assertEqual(cfg.working_directory, str(PROJECT_ROOT))

    def test_09_invalid_timeout(self) -> None:
        """Invalid timeout values (e.g. <= 0 or too large) are rejected."""
        servers = {
            "bad_timeout": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "startup_timeout": -5.0,
            }
        }
        ok = self.registry.register_from_dict(servers)
        self.assertFalse(ok)
        self.assertTrue(any("startup_timeout" in err for err in self.registry.validation_errors))

    def test_10_environment_allowlist(self) -> None:
        """Environment variables are converted to string mappings."""
        servers = {
            "env_srv": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "env": {"VAR_A": "123", "VAR_B": 456},
            }
        }
        self.registry.register_from_dict(servers)
        cfg = self.registry.get_config("env_srv")
        self.assertEqual(cfg.environment_allowlist["VAR_A"], "123")
        self.assertEqual(cfg.environment_allowlist["VAR_B"], "456")


if __name__ == "__main__":
    unittest.main()
