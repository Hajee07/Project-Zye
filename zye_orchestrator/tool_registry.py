"""
ZYE AI — Dynamic Tool Registry (Day 12)
========================================
Discovers MCP tools, validates schemas, generates Gemini FunctionDeclarations,
handles duplicate tool names across servers, and maintains atomic registry snapshots.
"""

from __future__ import annotations

import copy
import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("zye_orchestrator.tool_registry")


@dataclass
class ToolEntry:
    """Registry entry for a single MCP tool."""
    public_name: str         # Name as exposed to Gemini
    original_name: str       # Name as known to the MCP server
    server_name: str         # Owning server
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    generation: int = 0      # Registry generation when registered
    schema_valid: bool = True
    schema: Any = None

    def __post_init__(self) -> None:
        if self.schema is not None and not self.input_schema:
            self.input_schema = self.schema
        elif self.input_schema and self.schema is None:
            self.schema = self.input_schema


class ZyeToolRegistry:
    """
    Centralized tool registry managing MCP tool discovery, Gemini declaration
    generation, duplicate name resolution, and atomic snapshots.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}            # public_name -> ToolEntry
        self._server_tools: dict[str, list[str]] = {}     # server -> [public_names]
        self._generation: int = 0
        self._lock = threading.Lock()

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def get_tool(self, public_name: str) -> ToolEntry | None:
        """Look up a tool by its public name."""
        return self._tools.get(public_name)

    def get_tool_route(self, public_name: str) -> tuple[str, str] | None:
        """Return (server_name, original_tool_name) for routing, or None."""
        entry = self._tools.get(public_name)
        if entry:
            return (entry.server_name, entry.original_name)
        return None

    def get_server_tools(self, server_name: str) -> list[str]:
        """Return list of public tool names belonging to a server."""
        return list(self._server_tools.get(server_name, []))

    def get_all_tools(self) -> dict[str, ToolEntry]:
        """Return copy of all tool entries."""
        return dict(self._tools)

    async def discover_tools(self, server_name: str, session: Any) -> list[dict[str, Any]]:
        """
        Discover tools from an MCP server session using list_tools().
        Returns list of raw tool dicts: [{name, description, inputSchema, input_schema}]
        Supports both MCP v2 (input_schema) and legacy wire format (inputSchema).
        """
        try:
            result = await session.list_tools()
            tools = []
            for tool in result.tools:
                schema = (
                    getattr(tool, "input_schema", None)
                    or getattr(tool, "inputSchema", None)
                    or (tool.get("input_schema") if isinstance(tool, dict) else None)
                    or (tool.get("inputSchema") if isinstance(tool, dict) else None)
                    or {}
                )
                tool_dict = {
                    "name": getattr(tool, "name", "") if not isinstance(tool, dict) else tool.get("name", ""),
                    "description": getattr(tool, "description", "") if not isinstance(tool, dict) else tool.get("description", ""),
                    "inputSchema": schema,
                    "input_schema": schema,
                }
                tools.append(tool_dict)
            return tools
        except Exception as exc:
            logger.error("Tool discovery failed for '%s': %s", server_name, exc)
            return []

    def validate_tool_schema(self, tool_dict: dict[str, Any]) -> bool:
        """Validate a tool schema is well-formed."""
        name = tool_dict.get("name", "")
        if not name or not isinstance(name, str):
            return False
        desc = tool_dict.get("description", "")
        if not isinstance(desc, str):
            return False
        schema = tool_dict.get("input_schema", tool_dict.get("inputSchema"))
        if schema is not None and not isinstance(schema, dict):
            return False
        return True

    def register_server_tools(
        self,
        server_name: str,
        raw_tools: list[dict[str, Any]],
        generation: int | None = None,
    ) -> list[str]:
        """
        Register discovered tools for a server, handling duplicates.
        Returns list of public names registered.
        """
        with self._lock:
            gen = generation if generation is not None else self._generation + 1
            registered: list[str] = []

            for tool_dict in raw_tools:
                if not self.validate_tool_schema(tool_dict):
                    logger.warning(
                        "Skipping invalid tool from '%s': %s",
                        server_name,
                        tool_dict.get("name", "<unnamed>"),
                    )
                    continue

                original_name = tool_dict["name"]
                description = tool_dict.get("description", "")
                input_schema = tool_dict.get("inputSchema", {})

                # Resolve public name (handle duplicates across servers)
                public_name = self._resolve_public_name(original_name, server_name)

                entry = ToolEntry(
                    public_name=public_name,
                    original_name=original_name,
                    server_name=server_name,
                    description=description,
                    input_schema=input_schema,
                    generation=gen,
                    schema_valid=True,
                )
                self._tools[public_name] = entry
                registered.append(public_name)

            self._server_tools[server_name] = registered
            self._generation = gen
            return registered

    def remove_server_tools(self, server_name: str) -> list[str]:
        """Remove all tools belonging to a server. Returns removed public names."""
        with self._lock:
            removed: list[str] = []
            tool_names = self._server_tools.pop(server_name, [])
            for pname in tool_names:
                if pname in self._tools and self._tools[pname].server_name == server_name:
                    del self._tools[pname]
                    removed.append(pname)
            return removed

    def atomic_refresh_server(
        self,
        server_name: str,
        new_tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Atomically replace a server's tools: remove old, register new.
        Returns summary of {added, removed, retained} tool names.
        """
        with self._lock:
            old_names = set(self._server_tools.get(server_name, []))

            # Build new tool entries
            new_gen = self._generation + 1
            new_entries: dict[str, ToolEntry] = {}
            new_public_names: list[str] = []

            for tool_dict in new_tools:
                if not self.validate_tool_schema(tool_dict):
                    continue
                original_name = tool_dict["name"]
                public_name = self._resolve_public_name(original_name, server_name)
                entry = ToolEntry(
                    public_name=public_name,
                    original_name=original_name,
                    server_name=server_name,
                    description=tool_dict.get("description", ""),
                    input_schema=tool_dict.get("inputSchema", {}),
                    generation=new_gen,
                    schema_valid=True,
                )
                new_entries[public_name] = entry
                new_public_names.append(public_name)

            new_names = set(new_public_names)
            removed = old_names - new_names
            added = new_names - old_names
            retained = old_names & new_names

            # Remove old tools
            for pname in removed:
                self._tools.pop(pname, None)

            # Add/update new tools
            for pname, entry in new_entries.items():
                self._tools[pname] = entry

            self._server_tools[server_name] = new_public_names
            self._generation = new_gen

            return {
                "added": list(added),
                "removed": list(removed),
                "retained": list(retained),
                "generation": new_gen,
            }

    def _resolve_public_name(self, original_name: str, server_name: str) -> str:
        """
        Resolve a tool's public name. If collision exists with another server,
        use server_name__tool_name format.
        """
        existing = self._tools.get(original_name)
        if existing is None or existing.server_name == server_name:
            return original_name

        # Collision detected: namespace both the existing and new one
        old_entry = self._tools.pop(original_name)
        old_public = f"{old_entry.server_name}__{original_name}"
        old_entry.public_name = old_public
        self._tools[old_public] = old_entry

        # Update server tools list for the old server
        if old_entry.server_name in self._server_tools:
            tools_list = self._server_tools[old_entry.server_name]
            if original_name in tools_list:
                idx = tools_list.index(original_name)
                tools_list[idx] = old_public

        return f"{server_name}__{original_name}"

    def build_gemini_declarations(self) -> list[Any]:
        """
        Build Gemini FunctionDeclaration list from all registered tools.
        Uses google.genai types if available, otherwise returns dicts.
        """
        declarations: list[Any] = []
        try:
            from google.genai import types
            _genai = True
        except ImportError:
            _genai = False

        for entry in self._tools.values():
            if not entry.schema_valid:
                continue

            if _genai:
                try:
                    # Build Schema from inputSchema dict
                    schema = entry.input_schema or getattr(entry, "schema", None) or {}
                    fd = types.FunctionDeclaration(
                        name=entry.public_name,
                        description=entry.description or f"MCP tool: {entry.original_name}",
                        parameters=schema if schema else None,
                    )
                    declarations.append(fd)
                except Exception as exc:
                    logger.warning(
                        "Failed to create FunctionDeclaration for '%s': %s",
                        entry.public_name,
                        exc,
                    )
            else:
                declarations.append({
                    "name": entry.public_name,
                    "description": entry.description,
                    "parameters": entry.input_schema,
                })

        return declarations

    def is_generation_current(self, gen: int) -> bool:
        """Check if a generation ID matches the current registry."""
        return gen == self._generation

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic information about the tool registry."""
        return {
            "generation": self._generation,
            "total_tools": len(self._tools),
            "servers_with_tools": list(self._server_tools.keys()),
            "tools": {
                name: {
                    "original_name": entry.original_name,
                    "server": entry.server_name,
                    "schema_valid": entry.schema_valid,
                    "generation": entry.generation,
                }
                for name, entry in self._tools.items()
            },
        }
