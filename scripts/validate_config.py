#!/usr/bin/env python3
"""
ZYE AI — Configuration Validator
=================================

Deterministic validation utility for zye_config.toml and environment
configuration files. Validates structure, types, value ranges, feature
flags, paths, and credential templates.

This script is safe to execute repeatedly. It makes no external API calls,
does not modify any files, and does not execute shell commands.

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --json

Exit Codes:
    0 — All validations passed.
    1 — One or more critical validations failed.
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "zye_config.toml"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
ENV_FILE = PROJECT_ROOT / ".env"

REQUIRED_SECTIONS: list[str] = [
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

FEATURE_FLAGS: list[str] = [
    "enable_smart_home",
    "enable_background_watchdog",
    "enable_meeting_reminders",
    "enable_memory",
    "enable_camera",
    "enable_autonomous_execution",
]

SECURITY_BOOLEANS: list[str] = [
    "allow_arbitrary_shell_execution",
    "allow_arbitrary_python_execution",
    "require_tool_validation",
    "require_action_audit",
    "fail_closed_on_permission_error",
]

PERMISSION_BOOLEANS: list[str] = [
    "read_operations",
    "reversible_file_operations",
    "external_message_sending_requires_confirmation",
    "file_deletion_requires_confirmation",
    "system_configuration_changes_require_confirmation",
]

NUMERIC_LIMITS: dict[str, dict[str, Any]] = {
    "system.min_free_disk_gb": {"min": 0.5, "max": 100.0},
    "system.min_free_ram_gb": {"min": 0.5, "max": 64.0},
    "ai.request_timeout_seconds": {"min": 5, "max": 300},
    "performance.max_concurrent_tasks": {"min": 1, "max": 20},
    "performance.default_task_timeout_seconds": {"min": 5, "max": 600},
    "performance.max_retry_attempts": {"min": 0, "max": 10},
    "audio.sample_rate": {"min": 8000, "max": 48000},
    "audio.chunk_size": {"min": 64, "max": 4096},
    "audio.silence_timeout_sec": {"min": 0.1, "max": 10.0},
    "audio.pre_roll_chunks": {"min": 1, "max": 100},
}

PATH_KEYS: list[str] = [
    "skills_dir",
    "data_dir",
    "logs_dir",
    "backups_dir",
    "profiles_dir",
]

PLACEHOLDER_PATTERNS: list[str] = [
    "your_",
    "placeholder",
    "insert_",
    "change_me",
    "xxx",
    "TODO",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Single validation check result."""

    name: str
    status: str  # "PASS", "WARN", "FAIL", "SKIP"
    message: str


@dataclass
class ValidationReport:
    """Aggregated validation report."""

    results: list[ValidationResult] = field(default_factory=list)

    def add(self, name: str, status: str, message: str) -> None:
        """Add a validation result to the report."""
        self.results.append(ValidationResult(name=name, status=status, message=message))

    @property
    def has_failures(self) -> bool:
        """Return True if any critical failures exist."""
        return any(r.status == "FAIL" for r in self.results)

    @property
    def summary(self) -> dict[str, int]:
        """Count results by status."""
        counts: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Helper: nested dict access
# ---------------------------------------------------------------------------

def _get_nested(data: dict[str, Any], dotted_key: str) -> Any:
    """Retrieve a value from a nested dict using a dotted key path."""
    keys = dotted_key.split(".")
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise KeyError(dotted_key)
        current = current[key]
    return current


def _has_nested(data: dict[str, Any], dotted_key: str) -> bool:
    """Check if a dotted key path exists in a nested dict."""
    try:
        _get_nested(data, dotted_key)
        return True
    except KeyError:
        return False


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load and parse the TOML configuration file.

    Returns:
        A tuple of (parsed_config, error_message).
        On success, error_message is None.
        On failure, parsed_config is None.
    """
    if not config_path.exists():
        return None, f"Configuration file not found: {config_path.name}"

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config, None
    except tomllib.TOMLDecodeError as exc:
        return None, f"TOML parse error: {exc}"
    except OSError as exc:
        return None, f"File read error: {exc}"


def validate_config_structure(config: dict[str, Any], report: ValidationReport) -> None:
    """Validate that the configuration is a non-empty dictionary."""
    if not config:
        report.add("config_structure", "FAIL", "Configuration is empty.")
    elif not isinstance(config, dict):
        report.add("config_structure", "FAIL", "Configuration root is not a mapping.")
    else:
        top_keys = list(config.keys())
        report.add(
            "config_structure",
            "PASS",
            f"Configuration loaded with {len(top_keys)} top-level sections: {', '.join(top_keys)}.",
        )


def validate_required_sections(config: dict[str, Any], report: ValidationReport) -> None:
    """Verify all required configuration sections exist."""
    missing: list[str] = []
    for section in REQUIRED_SECTIONS:
        if not _has_nested(config, section):
            missing.append(section)

    if missing:
        report.add(
            "required_sections",
            "FAIL",
            f"Missing required sections: {', '.join(missing)}.",
        )
    else:
        report.add(
            "required_sections",
            "PASS",
            f"All {len(REQUIRED_SECTIONS)} required sections present.",
        )


def validate_value_types(config: dict[str, Any], report: ValidationReport) -> None:
    """Validate critical configuration value types."""
    type_checks: list[tuple[str, type, str]] = [
        ("system.assistant_name", str, "string"),
        ("system.version", str, "string"),
        ("system.default_mission", str, "string"),
        ("system.min_free_disk_gb", (int, float), "number"),
        ("system.min_free_ram_gb", (int, float), "number"),
        ("ai.primary_provider", str, "string"),
        ("ai.local_provider", str, "string"),
        ("ai.model_routing_mode", str, "string"),
        ("ai.cloud_fallback_enabled", bool, "boolean"),
        ("ai.request_timeout_seconds", int, "integer"),
        ("performance.max_concurrent_tasks", int, "integer"),
        ("audio.sample_rate", int, "integer"),
        ("audio.chunk_size", int, "integer"),
        ("audio.silence_timeout_sec", (int, float), "number"),
        ("audio.tts_voice", str, "string"),
        ("observability.structured_logging", bool, "boolean"),
        ("observability.redact_secrets", bool, "boolean"),
    ]

    errors: list[str] = []
    for dotted_key, expected_type, type_name in type_checks:
        try:
            value = _get_nested(config, dotted_key)
            if not isinstance(value, expected_type):
                errors.append(
                    f"{dotted_key}: expected {type_name}, got {type(value).__name__}"
                )
        except KeyError:
            errors.append(f"{dotted_key}: key not found")

    if errors:
        report.add("value_types", "FAIL", f"Type errors: {'; '.join(errors)}.")
    else:
        report.add(
            "value_types",
            "PASS",
            f"All {len(type_checks)} type checks passed.",
        )


def validate_numeric_limits(config: dict[str, Any], report: ValidationReport) -> None:
    """Validate numeric configuration values are within acceptable ranges."""
    out_of_range: list[str] = []

    for dotted_key, limits in NUMERIC_LIMITS.items():
        try:
            value = _get_nested(config, dotted_key)
            if not isinstance(value, (int, float)):
                out_of_range.append(f"{dotted_key}: not a number")
                continue
            if value < limits["min"] or value > limits["max"]:
                out_of_range.append(
                    f"{dotted_key}={value} (allowed: {limits['min']}–{limits['max']})"
                )
        except KeyError:
            out_of_range.append(f"{dotted_key}: key not found")

    if out_of_range:
        report.add(
            "numeric_limits",
            "FAIL",
            f"Out-of-range values: {'; '.join(out_of_range)}.",
        )
    else:
        report.add(
            "numeric_limits",
            "PASS",
            f"All {len(NUMERIC_LIMITS)} numeric values within limits.",
        )


def validate_feature_flags(config: dict[str, Any], report: ValidationReport) -> None:
    """Verify all feature flags are boolean values."""
    non_boolean: list[str] = []
    features = config.get("features", {})

    for flag in FEATURE_FLAGS:
        if flag not in features:
            non_boolean.append(f"{flag}: missing")
        elif not isinstance(features[flag], bool):
            non_boolean.append(f"{flag}: {type(features[flag]).__name__} (expected bool)")

    # Also validate security booleans
    security = config.get("security", {})
    for flag in SECURITY_BOOLEANS:
        if flag not in security:
            non_boolean.append(f"security.{flag}: missing")
        elif not isinstance(security[flag], bool):
            non_boolean.append(
                f"security.{flag}: {type(security[flag]).__name__} (expected bool)"
            )

    # Validate permission booleans
    permissions = security.get("permissions", {})
    for flag in PERMISSION_BOOLEANS:
        if flag not in permissions:
            non_boolean.append(f"security.permissions.{flag}: missing")
        elif not isinstance(permissions[flag], bool):
            non_boolean.append(
                f"security.permissions.{flag}: {type(permissions[flag]).__name__} (expected bool)"
            )

    total_flags = len(FEATURE_FLAGS) + len(SECURITY_BOOLEANS) + len(PERMISSION_BOOLEANS)
    if non_boolean:
        report.add(
            "feature_flags",
            "FAIL",
            f"Boolean flag errors: {'; '.join(non_boolean)}.",
        )
    else:
        report.add(
            "feature_flags",
            "PASS",
            f"All {total_flags} boolean flags validated.",
        )


def validate_project_paths(config: dict[str, Any], report: ValidationReport) -> None:
    """Verify configured paths resolve within the project root."""
    paths_section = config.get("paths", {})
    issues: list[str] = []

    for key in PATH_KEYS:
        if key not in paths_section:
            issues.append(f"{key}: not configured")
            continue

        raw_path = paths_section[key]
        if not isinstance(raw_path, str):
            issues.append(f"{key}: not a string")
            continue

        resolved = (PROJECT_ROOT / raw_path).resolve()
        try:
            resolved.relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            issues.append(f"{key}: resolves outside project root ({resolved})")
            continue

        if not resolved.exists():
            issues.append(f"{key}: directory does not exist ({raw_path})")

    if issues:
        # Path issues are warnings if directories just don't exist yet
        has_outside = any("outside project root" in i for i in issues)
        status = "FAIL" if has_outside else "WARN"
        report.add("project_paths", status, f"Path issues: {'; '.join(issues)}.")
    else:
        report.add(
            "project_paths",
            "PASS",
            f"All {len(PATH_KEYS)} configured paths resolve within project root.",
        )


def validate_env_template(report: ValidationReport) -> None:
    """Check .env.example and .env existence and placeholder detection."""
    # Check .env.example
    if not ENV_EXAMPLE_FILE.exists():
        report.add("env_template", "FAIL", ".env.example not found.")
        return

    report.add("env_template", "PASS", ".env.example exists.")

    # Check .env
    if not ENV_FILE.exists():
        report.add("env_file", "WARN", ".env not found. Copy from .env.example.")
        return

    report.add("env_file", "PASS", ".env exists.")

    # Detect placeholder credentials (without printing values)
    try:
        env_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        placeholder_keys: list[str] = []
        for line in env_lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if any(pattern in value.lower() for pattern in PLACEHOLDER_PATTERNS):
                placeholder_keys.append(key)

        if placeholder_keys:
            report.add(
                "env_placeholders",
                "WARN",
                f"Placeholder values detected in {len(placeholder_keys)} key(s): "
                f"{', '.join(placeholder_keys)}. Update with real values when ready.",
            )
        else:
            report.add("env_placeholders", "PASS", "No placeholder patterns detected in .env.")
    except OSError as exc:
        report.add("env_placeholders", "WARN", f"Could not read .env: {exc}")


def generate_validation_report(report: ValidationReport, as_json: bool = False) -> str:
    """
    Generate a formatted validation report.

    Args:
        report: The validation report to format.
        as_json: If True, output JSON format.

    Returns:
        Formatted report string.
    """
    if as_json:
        data = {
            "results": [
                {"name": r.name, "status": r.status, "message": r.message}
                for r in report.results
            ],
            "summary": report.summary,
            "overall": "FAIL" if report.has_failures else "PASS",
        }
        return json.dumps(data, indent=2)

    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("ZYE AI — Configuration Validation Report")
    lines.append("=" * 72)
    lines.append("")

    for result in report.results:
        lines.append(f"  [{result.status}] {result.name}")
        lines.append(f"         {result.message}")
        lines.append("")

    lines.append("-" * 72)
    summary = report.summary
    lines.append(
        f"  Summary: {summary['PASS']} passed, {summary['WARN']} warnings, "
        f"{summary['FAIL']} failed, {summary['SKIP']} skipped"
    )

    if report.has_failures:
        lines.append("  Overall: FAIL — Critical issues must be resolved.")
    else:
        lines.append("  Overall: PASS — Configuration is valid.")

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    """
    Run all configuration validations and print the report.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    as_json = "--json" in sys.argv

    report = ValidationReport()

    # Step 1: Load configuration
    config, error = load_config(CONFIG_FILE)
    if error is not None:
        report.add("config_load", "FAIL", error)
        print(generate_validation_report(report, as_json=as_json))
        return 1

    report.add("config_load", "PASS", f"Configuration loaded from {CONFIG_FILE.name}.")

    # Step 2: Validate structure
    validate_config_structure(config, report)

    # Step 3: Required sections
    validate_required_sections(config, report)

    # Step 4: Value types
    validate_value_types(config, report)

    # Step 5: Numeric limits
    validate_numeric_limits(config, report)

    # Step 6: Feature flags
    validate_feature_flags(config, report)

    # Step 7: Project paths
    validate_project_paths(config, report)

    # Step 8: Environment template
    validate_env_template(report)

    # Generate and print report
    output = generate_validation_report(report, as_json=as_json)
    print(output)

    return 1 if report.has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
