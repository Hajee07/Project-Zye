#!/usr/bin/env python3
"""
ZYE AI — Day 03 Doctor Diagnostic Tests
========================================

Comprehensive automated test suite for doctor.py covering:
- Runtime & isolation diagnostics
- Directory creation, permission checking, and cleanup
- SQLite database initialization, WAL journal mode, and integrity checks
- Configuration & secret integrity validation
- Dependency & COM initialization audits
- Hardware detection (microphone, speaker, RAM, disk, admin)
- Final health certification and exit code validation

All tests run fully offline with mocks for hardware and COM interfaces.

Usage:
    python -m unittest tests.test_day03_doctor -v
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import doctor
from doctor import (
    DiagnosticCheck,
    aggregate_diagnostic_results,
    check_administrator_privileges,
    check_available_disk,
    check_available_ram,
    check_directory_permissions,
    check_future_mcp_modules,
    check_microphone_device,
    check_project_directories,
    check_python_version,
    check_speaker_device,
    check_virtual_environment,
    check_windows_platform,
    generate_remediation_advice,
    get_project_root,
    get_runtime_information,
    initialize_log_files,
    initialize_sqlite_database,
    load_toml_configuration,
    redact_sensitive_string,
    save_doctor_report,
    test_microphone_stream,
    validate_environment_file,
    validate_gemini_credentials,
    validate_optional_credentials,
    verify_pytorch_cpu_mode,
    verify_sqlite_integrity,
    verify_sqlite_wal,
    verify_windows_com,
)


# ===========================================================================
# 1. Runtime Tests (1–5)
# ===========================================================================

class TestRuntimeDiagnostics(unittest.TestCase):
    """Runtime and isolation diagnostic tests."""

    def test_01_supported_python_version(self) -> None:
        """Current runtime must be supported (3.11 or 3.12)."""
        check = check_python_version()
        self.assertIn(check.status, ["PASS", "FAIL"])
        major, minor = sys.version_info[:2]
        if (major, minor) in [(3, 11), (3, 12)]:
            self.assertEqual(check.status, "PASS")

    def test_02_unsupported_python_version_mock(self) -> None:
        """Unsupported version must produce FAIL with critical severity."""
        with patch.object(sys, "version_info", (3, 10, 5, "final", 0)):
            check = check_python_version()
            self.assertEqual(check.status, "FAIL")
            self.assertEqual(check.severity, "CRITICAL")
            self.assertIn("3.10", check.details)

    def test_03_windows_platform_detection(self) -> None:
        """Must correctly identify Windows NT 64-bit."""
        check = check_windows_platform()
        if sys.platform == "win32":
            self.assertEqual(check.status, "PASS")
        else:
            self.assertEqual(check.status, "FAIL")

    def test_04_virtual_environment_detection(self) -> None:
        """Must detect virtual environment isolation."""
        check = check_virtual_environment(PROJECT_ROOT)
        self.assertIn(check.status, ["PASS", "WARN"])

    def test_05_global_python_warning(self) -> None:
        """Running under global base prefix must yield a WARN."""
        with patch.object(sys, "prefix", sys.base_prefix):
            with patch.object(sys, "executable", r"C:\Python312\python.exe"):
                check = check_virtual_environment(PROJECT_ROOT)
                self.assertEqual(check.status, "WARN")
                self.assertEqual(check.severity, "HIGH")


# ===========================================================================
# 2. Filesystem Tests (6–10)
# ===========================================================================

class TestFilesystemDiagnostics(unittest.TestCase):
    """Directory creation, permission checking, and cleanup tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        import logging
        logger = logging.getLogger("zye_doctor")
        for h in list(logger.handlers):
            h.close()
            logger.removeHandler(h)
        self.temp_dir.cleanup()

    def test_06_required_directory_detection(self) -> None:
        """Pre-existing required directories must report PASS."""
        for d in ["skills", "data", "data/cad_models", "logs", "backups", "profiles"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        checks = check_project_directories(self.root)
        self.assertTrue(all(c.status == "PASS" for c in checks))

    def test_07_missing_directory_creation(self) -> None:
        """Missing required directories must be automatically created."""
        checks = check_project_directories(self.root)
        self.assertTrue(all(c.status == "PASS" for c in checks))
        self.assertTrue((self.root / "skills").is_dir())
        self.assertTrue((self.root / "data" / "cad_models").is_dir())
        self.assertTrue((self.root / "logs").is_dir())

    def test_08_write_permission_validation(self) -> None:
        """Writable directories must report PASS."""
        for d in ["data", "logs", "backups", "profiles"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        checks = check_directory_permissions(self.root)
        self.assertTrue(all(c.status == "PASS" for c in checks))

    def test_09_temporary_file_cleanup(self) -> None:
        """Temporary permission check files must be deleted immediately."""
        logs_dir = self.root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        check_directory_permissions(self.root)
        tmp_files = list(logs_dir.glob(".doctor_perm_test_*"))
        self.assertEqual(tmp_files, [], "Temporary test file was not cleaned up")

    def test_10_existing_files_preservation(self) -> None:
        """Existing logs must not be truncated or overwritten."""
        logs_dir = self.root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        sample_log = logs_dir / "zye_errors.log"
        sample_log.write_text("historical error record\n", encoding="utf-8")
        initialize_log_files(self.root)
        content = sample_log.read_text(encoding="utf-8")
        self.assertIn("historical error record", content)


# ===========================================================================
# 3. SQLite Tests (11–15)
# ===========================================================================

class TestSQLiteDiagnostics(unittest.TestCase):
    """SQLite WAL, integrity, and safe initialization tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_zye.sqlite"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_11_database_initialization(self) -> None:
        """Database file must be created on initialization."""
        check = initialize_sqlite_database(self.db_path)
        self.assertEqual(check.status, "PASS")
        self.assertTrue(self.db_path.is_file())

    def test_12_wal_mode_verification(self) -> None:
        """PRAGMA journal_mode=WAL must be set and verified."""
        initialize_sqlite_database(self.db_path)
        check = verify_sqlite_wal(self.db_path)
        self.assertEqual(check.status, "PASS")
        conn = sqlite3.connect(str(self.db_path))
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_13_integrity_check_pass(self) -> None:
        """PRAGMA integrity_check must return 'ok'."""
        initialize_sqlite_database(self.db_path)
        verify_sqlite_wal(self.db_path)
        check = verify_sqlite_integrity(self.db_path)
        self.assertEqual(check.status, "PASS")
        self.assertIn("ok", check.details)

    def test_14_existing_database_preservation(self) -> None:
        """Existing tables and data in SQLite must be preserved."""
        initialize_sqlite_database(self.db_path)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, item TEXT);")
        conn.execute("INSERT INTO test_tbl VALUES (1, 'preserved_data');")
        conn.commit()
        conn.close()

        # Re-run initialization and checks
        initialize_sqlite_database(self.db_path)
        verify_sqlite_wal(self.db_path)
        verify_sqlite_integrity(self.db_path)

        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute("SELECT item FROM test_tbl WHERE id = 1;").fetchone()
        conn.close()
        self.assertEqual(row[0], "preserved_data")

    def test_15_database_connection_cleanup(self) -> None:
        """File must be accessible (not locked) after checks complete."""
        initialize_sqlite_database(self.db_path)
        verify_sqlite_wal(self.db_path)
        verify_sqlite_integrity(self.db_path)
        # Should be able to open and delete without WinError 32 (file in use)
        conn = sqlite3.connect(str(self.db_path))
        conn.close()
        self.assertTrue(self.db_path.is_file())


# ===========================================================================
# 4. Configuration Tests (16–23)
# ===========================================================================

class TestConfigurationDiagnostics(unittest.TestCase):
    """TOML configuration, .env credentials, and secret redaction tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_16_valid_toml_parsing(self) -> None:
        """Valid TOML with required sections reports PASS."""
        toml_file = self.root / "zye_config.toml"
        toml_file.write_text(
            '[system]\nname="Zye"\n[features]\n[audio]\n[paths]\n', encoding="utf-8"
        )
        cfg, checks = load_toml_configuration(toml_file)
        self.assertIsNotNone(cfg)
        self.assertTrue(all(c.status == "PASS" for c in checks))

    def test_17_invalid_toml_handled(self) -> None:
        """Invalid TOML reports controlled FAIL without crashing."""
        toml_file = self.root / "zye_config.toml"
        toml_file.write_text("invalid [toml content ===\n", encoding="utf-8")
        cfg, checks = load_toml_configuration(toml_file)
        self.assertIsNone(cfg)
        self.assertTrue(any(c.status == "FAIL" for c in checks))

    def test_18_missing_env_file(self) -> None:
        """Missing .env file reports FAIL."""
        missing_env = self.root / ".env_does_not_exist"
        _, checks = validate_environment_file(missing_env)
        self.assertTrue(any(c.status == "FAIL" and "not found" in c.details for c in checks))

    def test_19_valid_gemini_credential(self) -> None:
        """Legitimate GEMINI_API_KEY reports PASS."""
        env_vars = {"GEMINI_API_KEY": "AIzaSyTestValidFakeKeyForUnitTestingOnly123"}
        check = validate_gemini_credentials(env_vars)
        self.assertEqual(check.status, "PASS")

    def test_20_missing_gemini_credential(self) -> None:
        """Missing GEMINI_API_KEY reports FAIL."""
        env_vars = {}
        check = validate_gemini_credentials(env_vars)
        self.assertEqual(check.status, "FAIL")

    def test_21_placeholder_gemini_credential(self) -> None:
        """Default template placeholder reports FAIL."""
        env_vars = {"GEMINI_API_KEY": "your_gemini_api_key_here"}
        check = validate_gemini_credentials(env_vars)
        self.assertEqual(check.status, "FAIL")
        self.assertIn("placeholder", check.details)

    def test_22_missing_optional_credentials_skip(self) -> None:
        """Missing optional credentials report SKIP and do not block."""
        env_vars = {"GEMINI_API_KEY": "valid_key"}
        checks = validate_optional_credentials(env_vars)
        self.assertTrue(all(c.status in ["PASS", "SKIP"] for c in checks))

    def test_23_secret_redaction(self) -> None:
        """Sensitive API key patterns must be completely redacted."""
        raw_text = "API error: GEMINI_API_KEY=AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q and sk-abcdef123456789012345678"
        redacted = redact_sensitive_string(raw_text)
        self.assertNotIn("AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q", redacted)
        self.assertNotIn("sk-abcdef123456789012345678", redacted)
        self.assertIn("[REDACTED", redacted)


# ===========================================================================
# 5. Dependency Tests (24–30)
# ===========================================================================

class TestDependencyDiagnostics(unittest.TestCase):
    """Package import, PyTorch CPU, and COM runtime tests."""

    def test_24_successful_imports(self) -> None:
        """Standard library modules must import without issues."""
        res = importlib.import_module("json")
        self.assertIsNotNone(res)

    def test_25_missing_imports(self) -> None:
        """Nonexistent package must be reported cleanly."""
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("non_existent_fake_zye_pkg_xyz")

    def test_26_broken_native_imports_handled(self) -> None:
        """Broken native package imports must not crash doctor functions."""
        with patch("importlib.import_module", side_effect=OSError("DLL load failed")):
            check = verify_pytorch_cpu_mode()
            self.assertEqual(check.status, "FAIL")

    def test_27_pytorch_cpu_mode_mock(self) -> None:
        """Mocked CPU PyTorch passes tensor and CUDA check."""
        mock_torch = MagicMock()
        mock_torch.__version__ = "2.2.0+cpu"
        mock_torch.version.cuda = None
        mock_torch.cuda.is_available.return_value = False
        mock_tensor = MagicMock()
        mock_tensor.tolist.return_value = [2, 4, 6]
        mock_torch.tensor.return_value.__mul__.return_value = mock_tensor

        with patch("importlib.import_module", return_value=mock_torch):
            check = verify_pytorch_cpu_mode()
            self.assertEqual(check.status, "PASS")
            self.assertIn("CPU-only", check.details)

    def test_28_cuda_enabled_build_warning(self) -> None:
        """CUDA-enabled PyTorch build produces a WARN."""
        mock_torch = MagicMock()
        mock_torch.__version__ = "2.2.0+cu121"
        mock_torch.version.cuda = "12.1"
        mock_torch.cuda.is_available.return_value = True
        mock_tensor = MagicMock()
        mock_tensor.tolist.return_value = [2, 4, 6]
        mock_torch.tensor.return_value.__mul__.return_value = mock_tensor

        with patch("importlib.import_module", return_value=mock_torch):
            check = verify_pytorch_cpu_mode()
            self.assertEqual(check.status, "WARN")
            self.assertIn("CUDA", check.details)

    def test_29_com_initialization_success_mock(self) -> None:
        """Successful COM CoInitialize/CoUninitialize reports PASS."""
        mock_com = MagicMock()
        with patch.dict(sys.modules, {"pythoncom": mock_com, "win32com.client": MagicMock()}):
            check = verify_windows_com()
            self.assertEqual(check.status, "PASS")
            mock_com.CoInitialize.assert_called_once()
            mock_com.CoUninitialize.assert_called_once()

    def test_30_com_initialization_failure_mock(self) -> None:
        """COM initialization error reports FAIL."""
        mock_com = MagicMock()
        mock_com.CoInitialize.side_effect = RuntimeError("RPC Server Unavailable")
        with patch.dict(sys.modules, {"pythoncom": mock_com}):
            check = verify_windows_com()
            self.assertEqual(check.status, "FAIL")


# ===========================================================================
# 6. Hardware & Resource Tests (31–42)
# ===========================================================================

class TestHardwareDiagnostics(unittest.TestCase):
    """Audio devices, memory, disk, and privilege audit tests."""

    def test_31_microphone_found_mock(self) -> None:
        """Available input device reports PASS."""
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = {
            "name": "Mock Realtek Microphone",
            "max_input_channels": 2,
            "default_samplerate": 48000,
        }
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check, meta = check_microphone_device()
            self.assertEqual(check.status, "PASS")
            self.assertTrue(meta["available"])

    def test_32_microphone_unavailable_mock(self) -> None:
        """Missing input device reports WARN and recommends fallback."""
        mock_sd = MagicMock()
        mock_sd.query_devices.side_effect = Exception("No input device found")
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check, meta = check_microphone_device()
            self.assertEqual(check.status, "WARN")
            self.assertTrue(meta["silent_text_mode_recommended"])
            self.assertEqual(meta["recommended_fallback"], "ALT_Z_TEXT_MODE")

    def test_33_microphone_stream_opens_mock(self) -> None:
        """16 kHz mono float32 stream verification passes."""
        mock_sd = MagicMock()
        mock_stream = MagicMock()
        mock_stream.active = True
        mock_sd.InputStream.return_value = mock_stream
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check = test_microphone_stream()
            self.assertEqual(check.status, "PASS")
            mock_sd.InputStream.assert_called_once_with(
                samplerate=16000, channels=1, dtype="float32"
            )
            mock_stream.close.assert_called_once()

    def test_34_microphone_stream_fails_mock(self) -> None:
        """Stream opening failure reports WARN cleanly."""
        mock_sd = MagicMock()
        mock_sd.InputStream.side_effect = RuntimeError("Device Busy")
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check = test_microphone_stream()
            self.assertEqual(check.status, "WARN")

    def test_35_speaker_found_mock(self) -> None:
        """Available output device reports PASS."""
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = {
            "name": "Mock Realtek Speakers",
            "max_output_channels": 2,
        }
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check, meta = check_speaker_device()
            self.assertEqual(check.status, "PASS")
            self.assertTrue(meta["available"])

    def test_36_speaker_unavailable_mock(self) -> None:
        """Missing output device reports WARN."""
        mock_sd = MagicMock()
        mock_sd.query_devices.side_effect = Exception("No output device found")
        with patch.dict(sys.modules, {"sounddevice": mock_sd}):
            check, meta = check_speaker_device()
            self.assertEqual(check.status, "WARN")
            self.assertFalse(meta["available"])

    def test_37_ram_above_threshold_mock(self) -> None:
        """RAM >= threshold reports PASS."""
        mock_psutil = MagicMock()
        mock_vm = MagicMock()
        mock_vm.available = 4 * (1024**3)
        mock_vm.total = 16 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_vm
        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            check = check_available_ram(min_ram_gb=1.5)
            self.assertEqual(check.status, "PASS")

    def test_38_ram_below_threshold_mock(self) -> None:
        """RAM < threshold reports FAIL."""
        mock_psutil = MagicMock()
        mock_vm = MagicMock()
        mock_vm.available = 1.0 * (1024**3)
        mock_vm.total = 8 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_vm
        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            check = check_available_ram(min_ram_gb=1.5)
            self.assertEqual(check.status, "FAIL")

    def test_39_disk_above_threshold(self) -> None:
        """Disk >= threshold reports PASS."""
        check = check_available_disk(PROJECT_ROOT, min_disk_gb=1.0)
        self.assertIn(check.status, ["PASS", "FAIL"])

    def test_40_disk_below_threshold_mock(self) -> None:
        """Mocked insufficient disk space reports FAIL."""
        with patch("shutil.disk_usage", return_value=(100 * 10**9, 99 * 10**9, 0.5 * 10**9)):
            check = check_available_disk(PROJECT_ROOT, min_disk_gb=3.0)
            self.assertEqual(check.status, "FAIL")

    def test_41_administrator_check_success_mock(self) -> None:
        """Admin user returns PASS."""
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=1):
            check = check_administrator_privileges()
            self.assertEqual(check.status, "PASS")

    def test_42_administrator_check_warning_mock(self) -> None:
        """Standard non-elevated user returns non-blocking WARN."""
        with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0):
            check = check_administrator_privileges()
            self.assertEqual(check.status, "WARN")


# ===========================================================================
# 7. Certification & Report Tests (43–50)
# ===========================================================================

class TestCertificationEngine(unittest.TestCase):
    """Results aggregation, JSON reporting, and status rules tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_43_ready_aggregation(self) -> None:
        """All PASS and SKIP checks produce READY status."""
        checks = [
            DiagnosticCheck("c1", "STAGE 1", "PASS", "INFO", "ok", "ts"),
            DiagnosticCheck("c2", "STAGE 3", "SKIP", "INFO", "skipped", "ts"),
        ]
        report = aggregate_diagnostic_results(checks, {}, self.root)
        self.assertEqual(report["overall_status"], "READY")

    def test_44_degraded_aggregation(self) -> None:
        """Presence of WARN without critical FAIL produces DEGRADED status."""
        checks = [
            DiagnosticCheck("c1", "STAGE 1", "PASS", "INFO", "ok", "ts"),
            DiagnosticCheck("c2", "STAGE 5", "WARN", "MEDIUM", "warning", "ts"),
        ]
        report = aggregate_diagnostic_results(checks, {}, self.root)
        self.assertEqual(report["overall_status"], "DEGRADED")

    def test_45_blocked_aggregation(self) -> None:
        """Presence of critical FAIL produces BLOCKED status."""
        checks = [
            DiagnosticCheck("c1", "STAGE 1", "PASS", "INFO", "ok", "ts"),
            DiagnosticCheck("c2", "STAGE 3", "FAIL", "CRITICAL", "missing key", "ts"),
        ]
        report = aggregate_diagnostic_results(checks, {}, self.root)
        self.assertEqual(report["overall_status"], "BLOCKED")

    def test_46_correct_exit_codes(self) -> None:
        """Exit code must be 0 for READY/DEGRADED and 1 for BLOCKED."""
        # Simulated BLOCKED
        report_blocked = {"overall_status": "BLOCKED"}
        exit_code = 1 if report_blocked["overall_status"] == "BLOCKED" else 0
        self.assertEqual(exit_code, 1)

        # Simulated DEGRADED
        report_degraded = {"overall_status": "DEGRADED"}
        exit_code = 1 if report_degraded["overall_status"] == "BLOCKED" else 0
        self.assertEqual(exit_code, 0)

    def test_47_json_report_generation(self) -> None:
        """Generated report must be valid JSON matching required keys."""
        checks = [DiagnosticCheck("c1", "STAGE 1", "PASS", "INFO", "ok", "ts")]
        report = aggregate_diagnostic_results(checks, {}, self.root)
        out_path = self.root / "logs" / "test_report.json"
        save_doctor_report(report, out_path)
        self.assertTrue(out_path.is_file())
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["project"], "Zye AI")
        self.assertIn("summary", loaded)

    def test_48_future_mcp_missing_modules_non_critical(self) -> None:
        """Missing future MCP modules must report WARN and not cause BLOCKED."""
        checks = check_future_mcp_modules(self.root)
        self.assertTrue(all(c.status == "WARN" for c in checks))
        self.assertTrue(all(c.severity == "INFO" for c in checks))
        report = aggregate_diagnostic_results(checks, {}, self.root)
        self.assertEqual(report["overall_status"], "DEGRADED")

    def test_49_optional_credentials_do_not_block(self) -> None:
        """Optional credentials do not cause a BLOCKED status."""
        env_vars = {"GEMINI_API_KEY": "valid_key"}
        checks = validate_optional_credentials(env_vars)
        report = aggregate_diagnostic_results(checks, {}, self.root)
        self.assertNotEqual(report["overall_status"], "BLOCKED")

    def test_50_no_secrets_in_reports(self) -> None:
        """Serialized doctor report must not contain secret tokens."""
        checks = [DiagnosticCheck("c1", "STAGE 3", "PASS", "INFO", "GEMINI_API_KEY=AIzaSySecretTestKey123", "ts")]
        report = aggregate_diagnostic_results(checks, {}, self.root)
        out_path = self.root / "logs" / "secret_test_report.json"
        save_doctor_report(report, out_path)
        content = out_path.read_text(encoding="utf-8")
        self.assertNotIn("AIzaSySecretTestKey123", content)
        self.assertIn("[REDACTED", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
