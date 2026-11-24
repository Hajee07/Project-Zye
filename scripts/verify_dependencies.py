#!/usr/bin/env python3
"""
ZYE AI — Dependency Verification Engine
========================================

Independent dependency and runtime verification utility for Zye AI.
Validates Python runtime environment, virtual environment isolation,
package distribution versions, module importability, Windows-specific
bindings, and CPU-only PyTorch execution mode.

This script does not perform network operations or install packages.
It is safe to execute repeatedly in both CI and local developer shells.

Usage:
    python scripts/verify_dependencies.py
    python scripts/verify_dependencies.py --json
    python scripts/verify_dependencies.py --output logs/day02_package_inventory.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Constants & Package Mapping
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY_PATH = PROJECT_ROOT / "logs" / "day02_package_inventory.json"

# Mapping of Distribution Name (PyPI / requirements.txt) -> list of top-level import names
DISTRIBUTION_TO_IMPORTS: dict[str, list[str]] = {
    # Core AI & MCP
    "google-genai": ["google.genai"],
    "mcp": ["mcp"],
    "python-dotenv": ["dotenv"],
    "httpx": ["httpx"],
    "pydantic": ["pydantic"],
    # Voice & Audio
    "silero-vad": ["silero_vad"],
    "sounddevice": ["sounddevice"],
    "numpy": ["numpy"],
    "scipy": ["scipy"],
    "edge-tts": ["edge_tts"],
    "pygame": ["pygame"],
    "keyboard": ["keyboard"],
    # Windows & Office
    "pywinauto": ["pywinauto"],
    "pywin32": ["pythoncom", "win32com.client"],
    "pyautogui": ["pyautogui"],
    "pygetwindow": ["pygetwindow"],
    "pyperclip": ["pyperclip"],
    "python-docx": ["docx"],
    "python-pptx": ["pptx"],
    "openpyxl": ["openpyxl"],
    "pypdf": ["pypdf"],
    # Browser & Vision
    "playwright": ["playwright"],
    "opencv-contrib-python": ["cv2"],
    "mss": ["mss"],
    "pillow": ["PIL"],
    # Data & Intelligence
    "duckdb": ["duckdb"],
    "pandas": ["pandas"],
    "sympy": ["sympy"],
    "duckduckgo-search": ["duckduckgo_search"],
    # System & Cybersecurity
    "psutil": ["psutil"],
    "scapy": ["scapy"],
    # Engineering & CAD
    "trimesh": ["trimesh"],
    "ezdxf": ["ezdxf"],
}

WINDOWS_SPECIFIC_DISTRIBUTIONS = ["pywin32", "pywinauto", "keyboard"]


# ---------------------------------------------------------------------------
# Core Verification Functions
# ---------------------------------------------------------------------------

def get_python_runtime() -> dict[str, Any]:
    """Retrieve details of the active Python runtime environment."""
    return {
        "version": platform.python_version(),
        "version_info": list(sys.version_info[:3]),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "is_isolated": sys.prefix != sys.base_prefix,
        "platform": platform.platform(),
        "system": platform.system(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
    }


def get_distribution_version(distribution_name: str) -> str | None:
    """
    Retrieve installed version for a distribution name using importlib.metadata.
    Returns None if distribution is not installed.
    """
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def verify_python_isolation() -> tuple[bool, str]:
    """Verify that Python is running inside an isolated virtual environment."""
    runtime = get_python_runtime()
    if runtime["is_isolated"]:
        return True, f"Virtual environment verified at: {runtime['prefix']}"
    return False, f"Not running in virtual environment (global prefix: {runtime['prefix']})"


def verify_required_imports(
    mapping: dict[str, list[str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Verify each distribution and its corresponding Python module imports.
    Returns a dictionary keyed by distribution name with verification status and details.
    """
    if mapping is None:
        mapping = DISTRIBUTION_TO_IMPORTS

    results: dict[str, dict[str, Any]] = {}

    for dist_name, import_names in mapping.items():
        dist_version = get_distribution_version(dist_name)
        dist_installed = dist_version is not None

        imports_status: list[dict[str, Any]] = []
        all_imports_passed = True

        for imp in import_names:
            try:
                importlib.import_module(imp)
                imports_status.append({
                    "import_name": imp,
                    "status": "PASS",
                    "error": None,
                })
            except Exception as exc:
                all_imports_passed = False
                # Format sanitized error message without leaking sensitive variables
                exc_type = type(exc).__name__
                exc_msg = str(exc).strip()
                imports_status.append({
                    "import_name": imp,
                    "status": "FAIL",
                    "error": f"{exc_type}: {exc_msg}" if exc_msg else exc_type,
                })

        if dist_installed and all_imports_passed:
            overall = "PASS"
            remediation = None
        elif not dist_installed and not all_imports_passed:
            overall = "NOT_INSTALLED"
            remediation = f"Install distribution via: pip install {dist_name}"
        else:
            overall = "FAIL"
            remediation = f"Reinstall or fix configuration for: {dist_name}"

        results[dist_name] = {
            "distribution": dist_name,
            "installed": dist_installed,
            "version": dist_version,
            "imports": imports_status,
            "status": overall,
            "remediation": remediation,
        }

    return results


def verify_torch_cpu_mode() -> dict[str, Any]:
    """
    Verify PyTorch installation, ensuring it is CPU-only and functional.
    CUDA must be disabled/unavailable for CPU-only builds.
    """
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "cuda_version": None,
        "cuda_available": False,
        "cpu_tensor_verified": False,
        "status": "NOT_INSTALLED",
        "message": "PyTorch is not installed.",
    }

    try:
        torch = importlib.import_module("torch")
        result["installed"] = True
        result["version"] = getattr(torch, "__version__", "unknown")
        result["cuda_version"] = getattr(getattr(torch, "version", None), "cuda", None)
        result["cuda_available"] = bool(torch.cuda.is_available())

        # Test basic CPU tensor calculation
        x = torch.tensor([1, 2, 3])
        y = x * 2
        tensor_correct = y.tolist() == [2, 4, 6]
        result["cpu_tensor_verified"] = tensor_correct

        if result["cuda_available"]:
            result["status"] = "WARN"
            result["message"] = (
                f"PyTorch version {result['version']} installed with CUDA enabled. "
                "Day 02 target is CPU-only."
            )
        elif not tensor_correct:
            result["status"] = "FAIL"
            result["message"] = "PyTorch CPU tensor multiplication test failed."
        else:
            result["status"] = "PASS"
            result["message"] = (
                f"CPU-only PyTorch v{result['version']} verified. "
                f"CUDA available: {result['cuda_available']}."
            )
    except ModuleNotFoundError:
        result["status"] = "NOT_INSTALLED"
        result["message"] = "torch module not installed in current environment."
    except Exception as exc:
        result["status"] = "FAIL"
        result["message"] = f"PyTorch verification error: {type(exc).__name__}: {exc}"

    return result


def verify_windows_packages() -> dict[str, Any]:
    """Verify Windows-specific subsystems (pywin32, pywinauto, keyboard)."""
    sub_results: dict[str, Any] = {}
    is_windows = platform.system() == "Windows"

    for dist in WINDOWS_SPECIFIC_DISTRIBUTIONS:
        ver = get_distribution_version(dist)
        sub_results[dist] = {
            "installed": ver is not None,
            "version": ver,
            "applicable": is_windows,
        }

    return {
        "platform_is_windows": is_windows,
        "packages": sub_results,
    }


def verify_dependency_integrity() -> dict[str, Any]:
    """Aggregate environment checks into a single integrity dictionary."""
    runtime = get_python_runtime()
    iso_ok, iso_msg = verify_python_isolation()
    torch_res = verify_torch_cpu_mode()
    imports_res = verify_required_imports()
    win_res = verify_windows_packages()

    total_packages = len(imports_res)
    passed_count = sum(1 for v in imports_res.values() if v["status"] == "PASS")
    not_installed_count = sum(1 for v in imports_res.values() if v["status"] == "NOT_INSTALLED")
    failed_count = sum(1 for v in imports_res.values() if v["status"] == "FAIL")

    if passed_count == total_packages and torch_res["status"] == "PASS":
        overall_status = "PASS"
    elif not_installed_count == total_packages and torch_res["status"] == "NOT_INSTALLED":
        overall_status = "PENDING_INSTALL"
    elif failed_count > 0 or torch_res["status"] == "FAIL":
        overall_status = "FAIL"
    else:
        overall_status = "PARTIAL"

    return {
        "overall_status": overall_status,
        "runtime": runtime,
        "isolation": {"valid": iso_ok, "message": iso_msg},
        "torch_cpu": torch_res,
        "windows_packages": win_res,
        "summary": {
            "total_declared": total_packages,
            "passed": passed_count,
            "not_installed": not_installed_count,
            "failed": failed_count,
        },
        "packages": imports_res,
    }


def build_dependency_report() -> dict[str, Any]:
    """Build a complete serializable JSON inventory report."""
    integrity = verify_dependency_integrity()
    return {
        "project": "Zye AI",
        "stage": "Day 02",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "integrity": integrity,
    }


def save_json_report(report: dict[str, Any], output_path: Path) -> None:
    """Save the dependency verification report to JSON file securely."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# CLI Formatting and Entry Point
# ---------------------------------------------------------------------------

def format_console_report(report: dict[str, Any]) -> str:
    """Format the report into clean GitHub-flavored console output."""
    integrity = report["integrity"]
    runtime = integrity["runtime"]
    summary = integrity["summary"]
    torch_res = integrity["torch_cpu"]

    lines = [
        "=" * 72,
        "ZYE AI — Dependency Verification Engine (Day 02)",
        "=" * 72,
        f"  Timestamp:         {report['generated_at']}",
        f"  Python Runtime:    v{runtime['version']} ({runtime['architecture']})",
        f"  Executable:        {runtime['executable']}",
        f"  Isolated Venv:     {integrity['isolation']['valid']} ({integrity['isolation']['message']})",
        f"  PyTorch CPU:       [{torch_res['status']}] {torch_res['message']}",
        "-" * 72,
        f"  Manifest Summary:  {summary['passed']} PASS | {summary['not_installed']} NOT INSTALLED | {summary['failed']} FAIL",
        f"  Overall Status:    {integrity['overall_status']}",
        "=" * 72,
    ]

    # Package breakdown
    lines.append("\nPackage Verification Status:")
    lines.append(f"  {'Distribution':<24} {'Status':<15} {'Version':<12} {'Imports'}")
    lines.append("  " + "-" * 68)

    for dist_name, item in integrity["packages"].items():
        ver = item["version"] or "none"
        status = item["status"]
        imports_summary = ", ".join(
            f"{imp['import_name']} ({imp['status']})" for imp in item["imports"]
        )
        lines.append(f"  {dist_name:<24} {status:<15} {ver:<12} {imports_summary}")

    return "\n".join(lines)


def main() -> int:
    """Main CLI execution handler."""
    parser = argparse.ArgumentParser(description="Zye AI Dependency Verification Utility")
    parser.add_argument("--json", action="store_true", help="Output pure JSON format")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_INVENTORY_PATH,
        help="Path to export the package inventory JSON file",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress console text output")

    args = parser.parse_args()

    report = build_dependency_report()

    # Save to requested JSON path
    try:
        save_json_report(report, args.output)
    except Exception as exc:
        print(f"Warning: Failed to save JSON report to {args.output}: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2))
    elif not args.quiet:
        print(format_console_report(report))

    overall = report["integrity"]["overall_status"]
    if overall in ("PASS", "PENDING_INSTALL"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
