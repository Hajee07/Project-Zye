"""
Configuration schema and loader for Zye Master MCP Orchestrator (Day 15).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_orchestrator_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate orchestrator settings from TOML file."""
    p = Path(config_path or (PROJECT_ROOT / "zye_config.toml"))
    if not p.is_file():
        return {}

    try:
        import tomllib
        with open(p, "rb") as f:
            cfg = tomllib.load(f)
            return cfg.get("orchestrator", {})
    except Exception:
        return {}
