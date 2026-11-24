"""
ZYE AI — MCP Server Registry (Day 12)
======================================
Centralized registry for MCP server configurations.
Validates server entries, resolves paths, checks script existence,
and enforces security constraints (no shell=True, no arbitrary commands).
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("zye_orchestrator.registry")


@dataclass
class MCPServerConfig:
    """Validated configuration for a single MCP server."""

    server_name: str
    command: str
    args: list[str] = field(default_factory=list)
    working_directory: str = ""
    environment_allowlist: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    required: bool = False
    startup_timeout: float = 20.0
    tool_timeout: float = 30.0
    restart_policy: str = "on_failure"       # "on_failure" | "never" | "always"
    max_restart_attempts: int = 2
    reload_strategy: str = "staged"          # "staged" | "stop_start"
    health_check_policy: str = "mcp_ping"    # "mcp_ping" | "process_alive" | "none"


class ServerRegistry:
    """Centralized MCP server configuration registry with validation."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = project_root or Path(__file__).resolve().parent.parent
        self._configs: dict[str, MCPServerConfig] = {}
        self._validation_errors: list[str] = []

    @property
    def project_root(self) -> Path:
        return self._root

    @property
    def configs(self) -> dict[str, MCPServerConfig]:
        return dict(self._configs)

    @property
    def enabled_servers(self) -> dict[str, MCPServerConfig]:
        return {n: c for n, c in self._configs.items() if c.enabled}

    @property
    def required_servers(self) -> dict[str, MCPServerConfig]:
        return {n: c for n, c in self._configs.items() if c.required and c.enabled}

    @property
    def optional_servers(self) -> dict[str, MCPServerConfig]:
        return {n: c for n, c in self._configs.items() if not c.required and c.enabled}

    @property
    def validation_errors(self) -> list[str]:
        return list(self._validation_errors)

    def register_from_dict(
        self,
        servers_dict: dict[str, dict[str, Any]],
        toml_overrides: dict[str, Any] | None = None,
    ) -> bool:
        """
        Load server configurations from a dictionary (preserving existing MCP_SERVERS format).
        Apply optional TOML configuration overrides.
        Returns True if all registrations valid, False if any errors.
        """
        self._validation_errors.clear()
        self._configs.clear()

        seen_names: set[str] = set()

        for name, entry in servers_dict.items():
            # --- Duplicate name check ---
            if name in seen_names:
                self._validation_errors.append(f"Duplicate server name: '{name}'")
                continue
            seen_names.add(name)

            # --- Validate server name ---
            if not name or not isinstance(name, str):
                self._validation_errors.append(f"Invalid server name: {name!r}")
                continue

            # --- Validate command ---
            command = entry.get("command", "")
            if not command:
                self._validation_errors.append(f"[{name}] Missing 'command'")
                continue

            # Security: command must be allowlisted executable path
            command_str = str(command)
            if not self._is_safe_command(command_str):
                self._validation_errors.append(
                    f"[{name}] Command not on allowlist: {command_str!r}"
                )
                continue

            # --- Validate args ---
            args = entry.get("args", [])
            if not isinstance(args, (list, tuple)):
                self._validation_errors.append(f"[{name}] 'args' must be a list")
                continue

            # Validate script existence for Python args
            script_path = self._resolve_script_path(args)
            script_exists = script_path.exists() if script_path else False
            is_req = entry.get("required", False)
            if script_path and not script_exists:
                if is_req:
                    self._validation_errors.append(
                        f"[{name}] Required script not found: {script_path}"
                    )
                    continue
                else:
                    logger.debug("[%s] Optional server script not found: %s", name, script_path)

            # --- Build config ---
            env_raw = entry.get("env", {})
            env_allow = {k: str(v) for k, v in env_raw.items()} if isinstance(env_raw, dict) else {}

            # Apply TOML per-server overrides
            overrides = {}
            if toml_overrides and name in toml_overrides:
                overrides = toml_overrides[name]

            # Section 5.2: Do not start a server whose entry-point script does not exist
            if script_path and not script_exists:
                enabled = False
            else:
                enabled = overrides.get("enabled", entry.get("enabled", True))
            required = overrides.get("required", entry.get("required", False))
            startup_timeout = float(overrides.get(
                "startup_timeout",
                entry.get("startup_timeout", 20.0),
            ))
            tool_timeout = float(overrides.get(
                "tool_timeout",
                entry.get("tool_timeout", 30.0),
            ))
            restart_policy = str(overrides.get(
                "restart_policy",
                entry.get("restart_policy", "on_failure"),
            ))
            max_restart = int(overrides.get(
                "max_restart_attempts",
                entry.get("max_restart_attempts", 2),
            ))
            reload_strategy = str(overrides.get(
                "reload_strategy",
                entry.get("reload_strategy", "staged"),
            ))
            health_check = str(overrides.get(
                "health_check_policy",
                entry.get("health_check_policy", "mcp_ping"),
            ))
            working_dir = str(overrides.get(
                "working_directory",
                entry.get("working_directory", str(self._root)),
            ))

            # Validate timeout ranges
            if startup_timeout <= 0 or startup_timeout > 120:
                self._validation_errors.append(
                    f"[{name}] Invalid startup_timeout: {startup_timeout}"
                )
                continue
            if tool_timeout <= 0 or tool_timeout > 300:
                self._validation_errors.append(
                    f"[{name}] Invalid tool_timeout: {tool_timeout}"
                )
                continue

            # Validate restart policy
            if restart_policy not in ("on_failure", "never", "always"):
                self._validation_errors.append(
                    f"[{name}] Invalid restart_policy: {restart_policy!r}"
                )
                continue

            config = MCPServerConfig(
                server_name=name,
                command=command_str,
                args=[str(a) for a in args],
                working_directory=working_dir,
                environment_allowlist=env_allow,
                enabled=bool(enabled),
                required=bool(required),
                startup_timeout=startup_timeout,
                tool_timeout=tool_timeout,
                restart_policy=restart_policy,
                max_restart_attempts=max_restart,
                reload_strategy=reload_strategy,
                health_check_policy=health_check,
            )
            self._configs[name] = config

        if self._validation_errors:
            for err in self._validation_errors:
                logger.warning("Registry validation: %s", err)
            return False
        return True

    def get_config(self, server_name: str) -> MCPServerConfig | None:
        return self._configs.get(server_name)

    def has_server(self, server_name: str) -> bool:
        return server_name in self._configs

    def get_server_names(self) -> list[str]:
        return list(self._configs.keys())

    def _is_safe_command(self, command: str) -> bool:
        """Validate command is a known-safe executable (Python interpreter)."""
        cmd_path = Path(command)
        cmd_name = cmd_path.name.lower()
        allowed_names = {"python.exe", "python3.exe", "python", "python3", "pythonw.exe"}
        # Allow the current interpreter
        if str(cmd_path) == sys.executable:
            return True
        if cmd_name in allowed_names:
            return True
        return False

    def _resolve_script_path(self, args: list[Any]) -> Path | None:
        """Extract and resolve the script path from args."""
        if not args:
            return None
        script = str(args[0])
        p = Path(script)
        if p.is_absolute():
            return p
        return self._root / p

    def get_diagnostics(self) -> dict[str, Any]:
        """Return registry diagnostic information."""
        return {
            "total_servers": len(self._configs),
            "enabled_servers": len(self.enabled_servers),
            "required_servers": len(self.required_servers),
            "optional_servers": len(self.optional_servers),
            "validation_errors": list(self._validation_errors),
            "servers": {
                name: {
                    "enabled": cfg.enabled,
                    "required": cfg.required,
                    "script_exists": self._resolve_script_path(cfg.args).exists()
                    if self._resolve_script_path(cfg.args)
                    else False,
                    "restart_policy": cfg.restart_policy,
                    "reload_strategy": cfg.reload_strategy,
                }
                for name, cfg in self._configs.items()
            },
        }
