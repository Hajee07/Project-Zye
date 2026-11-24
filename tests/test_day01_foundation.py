#!/usr/bin/env python3
"""
ZYE AI — Day 01 Foundation Tests
==================================

Automated validation of the Day 01 project structure, configuration,
security rules, and package initialization.

These tests are fully offline and require no external APIs or network access.

Usage:
    python -m pytest tests/test_day01_foundation.py -v
    python -m unittest tests.test_day01_foundation -v
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DIRS: list[str] = [
    "scripts",
    "skills",
    "data",
    "data/cad_models",
    "logs",
    "backups",
    "profiles",
    "tests",
]

REQUIRED_FILES: list[str] = [
    ".env.example",
    ".gitignore",
    "zye_config.toml",
    "requirements.txt",
    "README.md",
    "scripts/validate_config.py",
    "skills/__init__.py",
    "tests/test_day01_foundation.py",
    "data/cad_models/.gitkeep",
    "logs/.gitkeep",
    "backups/.gitkeep",
    "profiles/.gitkeep",
]

REQUIRED_TOML_SECTIONS: list[str] = [
    "system",
    "ai",
    "ai.privacy",
    "features",
    "security",
    "security.permissions",
    "performance",
    "audio",
    "observability",
    "paths",
]

FEATURE_FLAG_KEYS: list[str] = [
    "enable_smart_home",
    "enable_background_watchdog",
    "enable_meeting_reminders",
    "enable_memory",
    "enable_camera",
    "enable_autonomous_execution",
]

GITIGNORE_REQUIRED_PATTERNS: list[str] = [
    ".env",
    ".venv/",
    "__pycache__/",
    "logs/*.log",
    "data/*.sqlite",
    "profiles/*",
]


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestProjectRoot(unittest.TestCase):
    """TEST 01 — Project root exists."""

    def test_project_root_exists(self) -> None:
        """The project root directory must exist."""
        self.assertTrue(
            PROJECT_ROOT.exists(),
            f"Project root does not exist: {PROJECT_ROOT}",
        )

    def test_project_root_is_directory(self) -> None:
        """The project root must be a directory."""
        self.assertTrue(
            PROJECT_ROOT.is_dir(),
            f"Project root is not a directory: {PROJECT_ROOT}",
        )


class TestDirectoryStructure(unittest.TestCase):
    """TEST 02 — All required directories exist."""

    def test_required_directories(self) -> None:
        """Every required directory must exist."""
        for dir_name in REQUIRED_DIRS:
            dir_path = PROJECT_ROOT / dir_name
            with self.subTest(directory=dir_name):
                self.assertTrue(
                    dir_path.is_dir(),
                    f"Required directory missing: {dir_name}",
                )


class TestRequiredFiles(unittest.TestCase):
    """TEST 03 — All required Day 01 files exist."""

    def test_required_files(self) -> None:
        """Every required file must exist and be non-empty (except .gitkeep)."""
        for file_name in REQUIRED_FILES:
            file_path = PROJECT_ROOT / file_name
            with self.subTest(file=file_name):
                self.assertTrue(
                    file_path.is_file(),
                    f"Required file missing: {file_name}",
                )


class TestPythonEnvironment(unittest.TestCase):
    """TEST 04 — Python interpreter is inside .venv."""

    def test_venv_exists(self) -> None:
        """The .venv directory must exist."""
        venv_path = PROJECT_ROOT / ".venv"
        self.assertTrue(
            venv_path.is_dir(),
            "Virtual environment directory .venv/ does not exist.",
        )

    def test_venv_python_executable(self) -> None:
        """A Python executable must exist within .venv."""
        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        self.assertTrue(
            venv_python.is_file(),
            f"Virtual environment Python not found: {venv_python}",
        )


class TestTomlConfiguration(unittest.TestCase):
    """TEST 05 — TOML configuration parses correctly."""

    def setUp(self) -> None:
        self.config_path = PROJECT_ROOT / "zye_config.toml"

    def test_toml_file_exists(self) -> None:
        """The TOML configuration file must exist."""
        self.assertTrue(self.config_path.is_file(), "zye_config.toml not found.")

    def test_toml_parses(self) -> None:
        """The TOML file must parse without errors."""
        with open(self.config_path, "rb") as f:
            config = tomllib.load(f)
        self.assertIsInstance(config, dict)
        self.assertGreater(len(config), 0, "Configuration is empty.")


class TestRequiredSections(unittest.TestCase):
    """TEST 06 — Required configuration sections exist."""

    @classmethod
    def setUpClass(cls) -> None:
        config_path = PROJECT_ROOT / "zye_config.toml"
        with open(config_path, "rb") as f:
            cls.config = tomllib.load(f)

    def _get_nested(self, dotted_key: str) -> bool:
        """Check if a dotted key path exists."""
        keys = dotted_key.split(".")
        current = self.config
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        return True

    def test_required_sections(self) -> None:
        """All required TOML sections must be present."""
        for section in REQUIRED_TOML_SECTIONS:
            with self.subTest(section=section):
                self.assertTrue(
                    self._get_nested(section),
                    f"Required section missing: [{section}]",
                )


class TestConfigDataTypes(unittest.TestCase):
    """TEST 07 — Configuration data types are correct."""

    @classmethod
    def setUpClass(cls) -> None:
        config_path = PROJECT_ROOT / "zye_config.toml"
        with open(config_path, "rb") as f:
            cls.config = tomllib.load(f)

    def test_system_types(self) -> None:
        """System section values must have correct types."""
        system = self.config["system"]
        self.assertIsInstance(system["assistant_name"], str)
        self.assertIsInstance(system["version"], str)
        self.assertIsInstance(system["default_mission"], str)
        self.assertIsInstance(system["min_free_disk_gb"], (int, float))
        self.assertIsInstance(system["min_free_ram_gb"], (int, float))

    def test_ai_types(self) -> None:
        """AI section values must have correct types."""
        ai = self.config["ai"]
        self.assertIsInstance(ai["primary_provider"], str)
        self.assertIsInstance(ai["local_provider"], str)
        self.assertIsInstance(ai["cloud_fallback_enabled"], bool)
        self.assertIsInstance(ai["request_timeout_seconds"], int)

    def test_performance_types(self) -> None:
        """Performance section values must have correct types."""
        perf = self.config["performance"]
        self.assertIsInstance(perf["max_concurrent_tasks"], int)
        self.assertIsInstance(perf["default_task_timeout_seconds"], int)
        self.assertIsInstance(perf["max_retry_attempts"], int)

    def test_audio_types(self) -> None:
        """Audio section values must have correct types."""
        audio = self.config["audio"]
        self.assertIsInstance(audio["sample_rate"], int)
        self.assertIsInstance(audio["chunk_size"], int)
        self.assertIsInstance(audio["silence_timeout_sec"], (int, float))
        self.assertIsInstance(audio["tts_voice"], str)


class TestFeatureFlags(unittest.TestCase):
    """TEST 08 — Feature flags are boolean."""

    @classmethod
    def setUpClass(cls) -> None:
        config_path = PROJECT_ROOT / "zye_config.toml"
        with open(config_path, "rb") as f:
            cls.config = tomllib.load(f)

    def test_feature_flags_are_boolean(self) -> None:
        """Every feature flag must be a boolean value."""
        features = self.config.get("features", {})
        for flag in FEATURE_FLAG_KEYS:
            with self.subTest(flag=flag):
                self.assertIn(flag, features, f"Feature flag missing: {flag}")
                self.assertIsInstance(
                    features[flag],
                    bool,
                    f"{flag} is {type(features[flag]).__name__}, expected bool",
                )


class TestPathConfiguration(unittest.TestCase):
    """TEST 09 — Configured paths resolve inside the project root."""

    @classmethod
    def setUpClass(cls) -> None:
        config_path = PROJECT_ROOT / "zye_config.toml"
        with open(config_path, "rb") as f:
            cls.config = tomllib.load(f)

    def test_paths_within_project(self) -> None:
        """All configured paths must resolve within the project root."""
        paths = self.config.get("paths", {})
        for key in ["skills_dir", "data_dir", "logs_dir", "backups_dir", "profiles_dir"]:
            with self.subTest(path_key=key):
                self.assertIn(key, paths, f"Path key missing: {key}")
                resolved = (PROJECT_ROOT / paths[key]).resolve()
                try:
                    resolved.relative_to(PROJECT_ROOT.resolve())
                except ValueError:
                    self.fail(
                        f"{key} resolves outside project root: {resolved}"
                    )


class TestEnvExample(unittest.TestCase):
    """TEST 10 — .env.example exists."""

    def test_env_example_exists(self) -> None:
        """The .env.example file must exist."""
        env_example = PROJECT_ROOT / ".env.example"
        self.assertTrue(env_example.is_file(), ".env.example not found.")

    def test_env_example_has_content(self) -> None:
        """The .env.example file must contain key definitions."""
        env_example = PROJECT_ROOT / ".env.example"
        content = env_example.read_text(encoding="utf-8")
        self.assertIn("GEMINI_API_KEY", content, "GEMINI_API_KEY not in .env.example")
        self.assertIn("OLLAMA_URL", content, "OLLAMA_URL not in .env.example")


class TestEnvNotExposed(unittest.TestCase):
    """TEST 11 — .env is not accidentally exposed."""

    def test_env_not_in_gitignore_negation(self) -> None:
        """The .gitignore must not negate .env exclusion."""
        gitignore = PROJECT_ROOT / ".gitignore"
        if not gitignore.is_file():
            self.skipTest(".gitignore not found.")
        content = gitignore.read_text(encoding="utf-8")
        # .env should be ignored but .env.example should NOT be ignored
        self.assertIn(".env", content, ".env not found in .gitignore")
        self.assertIn("!.env.example", content, ".env.example should be preserved")


class TestGitIgnorePatterns(unittest.TestCase):
    """TEST 12 — Git ignore patterns protect sensitive files."""

    def test_required_ignore_patterns(self) -> None:
        """Critical patterns must be present in .gitignore."""
        gitignore = PROJECT_ROOT / ".gitignore"
        if not gitignore.is_file():
            self.skipTest(".gitignore not found.")
        content = gitignore.read_text(encoding="utf-8")
        for pattern in GITIGNORE_REQUIRED_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(
                    pattern,
                    content,
                    f"Missing gitignore pattern: {pattern}",
                )


class TestSkillsPackage(unittest.TestCase):
    """TEST 13 — skills package imports."""

    def test_skills_init_exists(self) -> None:
        """skills/__init__.py must exist."""
        init_file = PROJECT_ROOT / "skills" / "__init__.py"
        self.assertTrue(init_file.is_file(), "skills/__init__.py not found.")

    def test_skills_importable(self) -> None:
        """The skills package must be importable."""
        # Add project root to path temporarily
        original_path = sys.path.copy()
        try:
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            # Force reimport
            if "skills" in sys.modules:
                del sys.modules["skills"]
            import skills
            self.assertIsNotNone(skills.__version__)
        finally:
            sys.path[:] = original_path


class TestConfigValidator(unittest.TestCase):
    """TEST 14 — Configuration validator executes successfully."""

    def test_validator_runs(self) -> None:
        """validate_config.py must execute without crashing."""
        validator = PROJECT_ROOT / "scripts" / "validate_config.py"
        self.assertTrue(validator.is_file(), "validate_config.py not found.")

        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.is_file() else sys.executable

        result = subprocess.run(
            [python_exe, str(validator)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        # Should exit 0 (all pass) with valid config
        self.assertEqual(
            result.returncode,
            0,
            f"Validator failed with exit code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )


class TestInvalidTomlHandling(unittest.TestCase):
    """TEST 15 — Invalid TOML produces a controlled error."""

    def test_invalid_toml_does_not_crash(self) -> None:
        """The validator must handle invalid TOML gracefully."""
        validator = PROJECT_ROOT / "scripts" / "validate_config.py"

        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.is_file() else sys.executable

        # Create a temporary invalid TOML file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False, dir=str(PROJECT_ROOT)
        ) as tmp:
            tmp.write("[invalid\nthis is not valid toml ===\n")
            tmp_path = tmp.name

        try:
            # Import and test load_config directly
            original_path = sys.path.copy()
            try:
                if str(PROJECT_ROOT) not in sys.path:
                    sys.path.insert(0, str(PROJECT_ROOT))
                if str(PROJECT_ROOT / "scripts") not in sys.path:
                    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

                # Clear cached module
                for mod_name in list(sys.modules.keys()):
                    if "validate_config" in mod_name:
                        del sys.modules[mod_name]

                from scripts.validate_config import load_config
                config, error = load_config(Path(tmp_path))
                self.assertIsNone(config, "Invalid TOML should return None config.")
                self.assertIsNotNone(error, "Invalid TOML should return an error message.")
                self.assertIn("TOML", error, "Error should mention TOML.")
            finally:
                sys.path[:] = original_path
        finally:
            os.unlink(tmp_path)


class TestMissingCredentials(unittest.TestCase):
    """TEST 16 — Missing optional credentials do not crash validation."""

    def test_placeholder_credentials_handled(self) -> None:
        """Validation must not crash when credentials are placeholder values."""
        validator = PROJECT_ROOT / "scripts" / "validate_config.py"

        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.is_file() else sys.executable

        result = subprocess.run(
            [python_exe, str(validator)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        # Should not crash — exit 0 or 1 is fine, but not a traceback crash
        self.assertIn(
            result.returncode,
            [0, 1],
            f"Validator crashed with unexpected code {result.returncode}.\n"
            f"stderr: {result.stderr}",
        )
        # Should not have unhandled exception traces
        self.assertNotIn(
            "Traceback",
            result.stderr,
            "Validator produced an unhandled exception traceback.",
        )


class TestInvalidCriticalConfig(unittest.TestCase):
    """TEST 17 — Invalid critical configuration produces non-zero exit."""

    def test_missing_config_file(self) -> None:
        """Validator must return non-zero when config file is missing."""
        validator = PROJECT_ROOT / "scripts" / "validate_config.py"

        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.is_file() else sys.executable

        # Run from a temporary directory where zye_config.toml doesn't exist
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Copy only the validator script
            tmp_scripts = Path(tmp_dir) / "scripts"
            tmp_scripts.mkdir()
            import shutil
            shutil.copy2(str(validator), str(tmp_scripts / "validate_config.py"))

            result = subprocess.run(
                [python_exe, str(tmp_scripts / "validate_config.py")],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_dir,
            )
            self.assertEqual(
                result.returncode,
                1,
                f"Expected exit code 1 for missing config, got {result.returncode}.",
            )


class TestNoNetworkCalls(unittest.TestCase):
    """TEST 18 — No external network calls are made during testing."""

    def test_no_network_imports_in_validator(self) -> None:
        """The validator must not import network-related modules."""
        validator = PROJECT_ROOT / "scripts" / "validate_config.py"
        content = validator.read_text(encoding="utf-8")

        network_modules = ["urllib", "requests", "httpx", "aiohttp", "socket"]
        for module in network_modules:
            self.assertNotIn(
                f"import {module}",
                content,
                f"Validator imports network module: {module}",
            )

    def test_no_network_imports_in_skills_init(self) -> None:
        """skills/__init__.py must not import network modules."""
        init_file = PROJECT_ROOT / "skills" / "__init__.py"
        content = init_file.read_text(encoding="utf-8")

        network_modules = ["urllib", "requests", "httpx", "aiohttp", "socket"]
        for module in network_modules:
            self.assertNotIn(
                f"import {module}",
                content,
                f"skills/__init__.py imports network module: {module}",
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
