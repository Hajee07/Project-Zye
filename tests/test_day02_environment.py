#!/usr/bin/env python3
"""
ZYE AI — Day 02 Environment & Dependency Tests
================================================

Automated validation of the Day 02 Windows environment setup,
PowerShell installer existence, dependency verification engine,
manifest parser security, and offline execution boundaries.

Usage:
    python -m unittest tests.test_day02_environment -v
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import platform
import sys
import tempfile
from typing import Any
import unittest
from unittest.mock import MagicMock, patch

# Add project root and scripts directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scripts.verify_dependencies import (
    DISTRIBUTION_TO_IMPORTS,
    WINDOWS_SPECIFIC_DISTRIBUTIONS,
    build_dependency_report,
    get_distribution_version,
    get_python_runtime,
    verify_dependency_integrity,
    verify_python_isolation,
    verify_required_imports,
    verify_torch_cpu_mode,
)


class TestProjectRootDiscovery(unittest.TestCase):
    """TEST 01 — Project root discovery and containment."""

    def test_project_root_resolved(self) -> None:
        """Project root must exist and contain master configuration."""
        self.assertTrue(PROJECT_ROOT.is_dir(), f"Project root not found: {PROJECT_ROOT}")
        self.assertTrue((PROJECT_ROOT / "zye_config.toml").is_file(), "zye_config.toml not found")


class TestInstallerExistence(unittest.TestCase):
    """TEST 02 — PowerShell installer script existence."""

    def test_setup_env_ps1_exists(self) -> None:
        """scripts/setup_env.ps1 must exist and be non-empty."""
        installer = PROJECT_ROOT / "scripts" / "setup_env.ps1"
        self.assertTrue(installer.is_file(), f"setup_env.ps1 missing at {installer}")
        self.assertGreater(installer.stat().st_size, 100, "setup_env.ps1 is unexpectedly small")


class TestVerifierExistence(unittest.TestCase):
    """TEST 03 — Dependency verifier script existence."""

    def test_verify_dependencies_py_exists(self) -> None:
        """scripts/verify_dependencies.py must exist and be non-empty."""
        verifier = PROJECT_ROOT / "scripts" / "verify_dependencies.py"
        self.assertTrue(verifier.is_file(), f"verify_dependencies.py missing at {verifier}")
        self.assertGreater(verifier.stat().st_size, 500, "verify_dependencies.py is unexpectedly small")


class TestPythonVersionValidationLogic(unittest.TestCase):
    """TEST 04 — Python version validation logic."""

    @staticmethod
    def _is_supported_python(major: int, minor: int) -> bool:
        return major == 3 and minor in (11, 12)

    def test_current_python_version_supported(self) -> None:
        """Current test runtime Python version must be 3.11 or 3.12."""
        major, minor = sys.version_info[:2]
        self.assertTrue(
            self._is_supported_python(major, minor),
            f"Unsupported Python version detected: {major}.{minor}. Supported: 3.11, 3.12",
        )

    def test_reject_incompatible_python_versions(self) -> None:
        """Logic must reject incompatible versions like 3.8, 3.9, 3.10, 3.13, 2.7."""
        self.assertFalse(self._is_supported_python(2, 7))
        self.assertFalse(self._is_supported_python(3, 8))
        self.assertFalse(self._is_supported_python(3, 9))
        self.assertFalse(self._is_supported_python(3, 10))
        self.assertFalse(self._is_supported_python(3, 13))
        self.assertTrue(self._is_supported_python(3, 11))
        self.assertTrue(self._is_supported_python(3, 12))


class TestVirtualEnvironmentPathDetection(unittest.TestCase):
    """TEST 05 — Virtual environment detection and isolation."""

    def test_venv_directory_exists(self) -> None:
        """The .venv directory must exist."""
        venv_dir = PROJECT_ROOT / ".venv"
        self.assertTrue(venv_dir.is_dir(), ".venv directory does not exist")

    def test_isolation_function(self) -> None:
        """verify_python_isolation() returns expected status."""
        is_isolated, msg = verify_python_isolation()
        runtime = get_python_runtime()
        self.assertEqual(is_isolated, runtime["is_isolated"])
        self.assertIsInstance(msg, str)


class TestRequirementsManifestParsing(unittest.TestCase):
    """TEST 06 — Requirements manifest parsing."""

    def setUp(self) -> None:
        self.req_path = PROJECT_ROOT / "requirements.txt"
        self.assertTrue(self.req_path.is_file(), "requirements.txt does not exist")

    def _parse_manifest(self, path: Path) -> list[str]:
        packages: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            packages.append(clean)
        return packages

    def test_parse_manifest_non_empty(self) -> None:
        """requirements.txt must contain declared packages."""
        packages = self._parse_manifest(self.req_path)
        self.assertGreater(len(packages), 20, "Fewer packages found than expected in manifest")
        self.assertIn("google-genai", packages)
        self.assertIn("mcp", packages)
        self.assertIn("pydantic", packages)
        self.assertIn("playwright", packages)


class TestDuplicatePackageDetection(unittest.TestCase):
    """TEST 07 — Duplicate package detection."""

    def _detect_duplicates(self, lines: list[str]) -> list[str]:
        seen = set()
        duplicates = []
        for line in lines:
            clean = line.strip().lower()
            if not clean or clean.startswith("#"):
                continue
            pkg = clean.split("==")[0].split(">=")[0].split("<=")[0].strip()
            if pkg in seen:
                duplicates.append(pkg)
            seen.add(pkg)
        return duplicates

    def test_no_duplicates_in_project_requirements(self) -> None:
        """Official requirements.txt must not contain duplicate package entries."""
        req_lines = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        duplicates = self._detect_duplicates(req_lines)
        self.assertEqual(duplicates, [], f"Duplicate entries found in requirements.txt: {duplicates}")

    def test_duplicate_detector_catches_duplicates(self) -> None:
        """Duplicate detection algorithm correctly identifies duplicates."""
        test_lines = ["numpy", "scipy", "numpy", "pandas"]
        duplicates = self._detect_duplicates(test_lines)
        self.assertEqual(duplicates, ["numpy"])


class TestInvalidPackageDeclarationDetection(unittest.TestCase):
    """TEST 08 — Invalid and insecure package declaration detection."""

    def _validate_manifest_security(self, lines: list[str]) -> list[str]:
        violations = []
        for idx, line in enumerate(lines, 1):
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            line_issues = []
            # Check for editable local installs
            if clean.startswith("-e ") or clean.startswith("--editable"):
                line_issues.append("Editable installs prohibited")
            # Check for direct URL dependencies
            if "http://" in clean or "https://" in clean:
                line_issues.append("Direct URLs prohibited")
            # Check for git dependencies
            if "git+" in clean or "git://" in clean:
                line_issues.append("Git repositories prohibited")
            # Check for local path dependencies
            if clean.startswith(".") or clean.startswith("/"):
                line_issues.append("Local file paths prohibited")
            if line_issues:
                violations.append(f"Line {idx}: {', '.join(line_issues)}: {clean}")
        return violations

    def test_project_requirements_are_secure(self) -> None:
        """Project requirements.txt must contain no insecure declarations."""
        req_lines = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        violations = self._validate_manifest_security(req_lines)
        self.assertEqual(violations, [], f"Security violations in requirements.txt: {violations}")

    def test_detector_catches_insecure_entries(self) -> None:
        """Insecure entry detection correctly flags git, url, and editable lines."""
        insecure = [
            "-e ./local_pkg",
            "package @ https://example.com/wheel.whl",
            "git+https://github.com/org/repo.git",
            "valid-package",
        ]
        violations = self._validate_manifest_security(insecure)
        self.assertEqual(len(violations), 3)


class TestTorchCpuValidationLogic(unittest.TestCase):
    """TEST 09 — CPU-only PyTorch validation logic."""

    def test_torch_verification_handles_uninstalled_gracefully(self) -> None:
        """When torch is not installed or when mock tested, verify_torch_cpu_mode() reports cleanly."""
        res = verify_torch_cpu_mode()
        self.assertIn("status", res)
        self.assertIn("cuda_available", res)
        self.assertIn("cpu_tensor_verified", res)
        self.assertIn(res["status"], ["PASS", "NOT_INSTALLED", "FAIL", "WARN"])

    def test_torch_cpu_simulation_passes(self) -> None:
        """Simulated CPU-only PyTorch object passes validation."""
        mock_torch = MagicMock()
        mock_torch.__version__ = "2.2.0+cpu"
        mock_torch.version.cuda = None
        mock_torch.cuda.is_available.return_value = False

        # Mock tensor calculation
        mock_tensor = MagicMock()
        mock_tensor.tolist.return_value = [2, 4, 6]
        mock_torch.tensor.return_value.__mul__.return_value = mock_tensor

        with patch("importlib.import_module", return_value=mock_torch):
            res = verify_torch_cpu_mode()
            self.assertEqual(res["status"], "PASS")
            self.assertFalse(res["cuda_available"])
            self.assertTrue(res["cpu_tensor_verified"])


class TestDependencyMapping(unittest.TestCase):
    """TEST 10 — Dependency mapping integrity."""

    def test_all_distribution_mappings_present(self) -> None:
        """All distributions must map to valid non-empty module lists."""
        self.assertGreater(len(DISTRIBUTION_TO_IMPORTS), 25)
        for dist, imports in DISTRIBUTION_TO_IMPORTS.items():
            self.assertIsInstance(imports, list)
            self.assertGreater(len(imports), 0, f"No imports mapped for {dist}")
            for imp in imports:
                self.assertIsInstance(imp, str)
                self.assertGreater(len(imp), 0)

    def test_key_distributions_correctly_mapped(self) -> None:
        """Specific known distributions must map to their canonical import names."""
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["google-genai"], ["google.genai"])
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["python-dotenv"], ["dotenv"])
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["opencv-contrib-python"], ["cv2"])
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["pillow"], ["PIL"])
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["python-docx"], ["docx"])
        self.assertEqual(DISTRIBUTION_TO_IMPORTS["pywin32"], ["pythoncom", "win32com.client"])


class TestMissingDependencyDetection(unittest.TestCase):
    """TEST 11 — Missing dependency detection."""

    def test_missing_package_detection(self) -> None:
        """Uninstalled package must be reported as NOT_INSTALLED."""
        dummy_mapping = {"non-existent-zye-test-pkg-xyz": ["non_existent_zye_test_pkg_xyz"]}
        res = verify_required_imports(dummy_mapping)
        item = res["non-existent-zye-test-pkg-xyz"]
        self.assertEqual(item["status"], "NOT_INSTALLED")
        self.assertFalse(item["installed"])
        self.assertIn("pip install", item["remediation"])


class TestJsonReportGeneration(unittest.TestCase):
    """TEST 12 — JSON report generation."""

    def test_build_dependency_report_structure(self) -> None:
        """Generated report must contain required root keys and metadata."""
        report = build_dependency_report()
        self.assertEqual(report["project"], "Zye AI")
        self.assertEqual(report["stage"], "Day 02")
        self.assertIn("generated_at", report)
        self.assertIn("integrity", report)
        integrity = report["integrity"]
        self.assertIn("runtime", integrity)
        self.assertIn("summary", integrity)
        self.assertIn("packages", integrity)

    def test_save_json_report(self) -> None:
        """Report can be serialized and written to disk cleanly."""
        report = build_dependency_report()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            from scripts.verify_dependencies import save_json_report
            save_json_report(report, tmp_path)
            self.assertTrue(tmp_path.is_file())
            content = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(content["project"], "Zye AI")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestSecretRedaction(unittest.TestCase):
    """TEST 13 — Secret redaction."""

    def test_report_contains_no_secrets(self) -> None:
        """Serialized dependency report must never include API key patterns."""
        report = build_dependency_report()
        serialized = json.dumps(report)
        for secret_token in ["your_gemini_api_key", "sk-", "AIza", "password", "token="]:
            self.assertNotIn(secret_token, serialized)


class TestExistingEnvPreservation(unittest.TestCase):
    """TEST 14 — Existing .env preservation."""

    def test_env_file_preserved(self) -> None:
        """.env must exist and have content."""
        env_file = PROJECT_ROOT / ".env"
        self.assertTrue(env_file.is_file(), ".env file missing")
        self.assertGreater(env_file.stat().st_size, 0, ".env file is empty")


class TestExistingVenvPreservation(unittest.TestCase):
    """TEST 15 — Existing .venv preservation."""

    def test_venv_has_scripts(self) -> None:
        """Existing .venv must have python executable in Scripts."""
        py_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        self.assertTrue(py_exe.is_file(), f"Python not found in .venv: {py_exe}")


class TestNoExternalApiCalls(unittest.TestCase):
    """TEST 16 — No external network calls in test and verifier scripts."""

    def test_verifier_no_network_imports(self) -> None:
        """verify_dependencies.py must not import network client libraries."""
        code = (PROJECT_ROOT / "scripts" / "verify_dependencies.py").read_text(encoding="utf-8")
        for bad_import in ["import requests", "import httpx", "import urllib.request", "import socket"]:
            self.assertNotIn(bad_import, code, f"Forbidden network import in verifier: {bad_import}")


class TestNoArbitraryShellExecution(unittest.TestCase):
    """TEST 17 — No arbitrary shell execution in verifier code."""

    def test_verifier_no_exec_eval(self) -> None:
        """verify_dependencies.py must not contain eval() or exec()."""
        code = (PROJECT_ROOT / "scripts" / "verify_dependencies.py").read_text(encoding="utf-8")
        self.assertNotIn("eval(", code)
        self.assertNotIn("exec(", code)


class TestNoDestructiveFileOperations(unittest.TestCase):
    """TEST 18 — No destructive file operations."""

    def test_verifier_no_rmtree_or_unlink_project_root(self) -> None:
        """verify_dependencies.py must not perform destructive unlinks or rm operations."""
        code = (PROJECT_ROOT / "scripts" / "verify_dependencies.py").read_text(encoding="utf-8")
        self.assertNotIn("shutil.rmtree", code)
        self.assertNotIn("os.remove", code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
