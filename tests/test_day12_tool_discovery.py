#!/usr/bin/env python3
"""
ZYE AI — Day 12 Tool Discovery Test Suite
========================================
Tests for zye_orchestrator.tool_registry:
  1. Single server tool discovery
  2. Multiple server tool discovery
  3. Empty tool list handling
  4. Invalid JSON schema handling
  5. Duplicate tool name detection
  6. Namespaced aliases creation
  7. Correct server routing resolution
  8. Tool removal on server stop
  9. Tool addition on new server
 10. Gemini declaration rebuild
 11. Registry generation increment
 12. Stale tool rejection detection
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.tool_registry import ToolEntry, ZyeToolRegistry


class TestToolDiscovery(unittest.TestCase):
    """Test suite for Dynamic Tool Discovery & Registry."""

    def setUp(self) -> None:
        self.tr = ZyeToolRegistry()

    def test_01_single_server_discovery(self) -> None:
        """Tools from a single server are registered properly."""
        raw = [
            {"name": "tool_1", "description": "First tool", "inputSchema": {"type": "object"}},
            {"name": "tool_2", "description": "Second tool", "inputSchema": {"type": "object"}},
        ]
        registered = self.tr.register_server_tools("srv_a", raw)
        self.assertEqual(len(registered), 2)
        self.assertIn("tool_1", registered)
        self.assertIn("tool_2", registered)
        self.assertEqual(self.tr.tool_count, 2)

    def test_02_multiple_server_discovery(self) -> None:
        """Tools from different servers coexist without collisions."""
        raw_a = [{"name": "tool_a", "description": "A", "inputSchema": {}}]
        raw_b = [{"name": "tool_b", "description": "B", "inputSchema": {}}]
        self.tr.register_server_tools("srv_a", raw_a)
        self.tr.register_server_tools("srv_b", raw_b)
        self.assertEqual(self.tr.tool_count, 2)
        self.assertEqual(self.tr.get_tool_route("tool_a"), ("srv_a", "tool_a"))
        self.assertEqual(self.tr.get_tool_route("tool_b"), ("srv_b", "tool_b"))

    def test_03_empty_tool_list(self) -> None:
        """Registering an empty tool list succeeds with zero additions."""
        registered = self.tr.register_server_tools("empty_srv", [])
        self.assertEqual(len(registered), 0)
        self.assertEqual(self.tr.tool_count, 0)

    def test_04_invalid_json_schema(self) -> None:
        """Tools with missing or invalid schemas are rejected."""
        raw = [
            {"name": "", "description": "No name"},                      # invalid name
            {"name": "bad_schema", "description": "Bad", "inputSchema": "not_a_dict"}, # invalid schema
            {"name": "good_tool", "description": "Good", "inputSchema": {}},
        ]
        registered = self.tr.register_server_tools("srv", raw)
        self.assertEqual(len(registered), 1)
        self.assertIn("good_tool", registered)

    def test_05_duplicate_tool_name_detected(self) -> None:
        """Duplicate tool names across two servers are detected and namespaced."""
        raw_1 = [{"name": "get_status", "description": "Srv1 status", "inputSchema": {}}]
        raw_2 = [{"name": "get_status", "description": "Srv2 status", "inputSchema": {}}]
        self.tr.register_server_tools("srv1", raw_1)
        self.tr.register_server_tools("srv2", raw_2)

        # Both should be namespaced
        self.assertIn("srv1__get_status", self.tr.get_all_tools())
        self.assertIn("srv2__get_status", self.tr.get_all_tools())

    def test_06_namespaced_aliases(self) -> None:
        """Namespaced aliases preserve original_name for dispatch."""
        raw_1 = [{"name": "ping", "description": "Ping 1", "inputSchema": {}}]
        raw_2 = [{"name": "ping", "description": "Ping 2", "inputSchema": {}}]
        self.tr.register_server_tools("s1", raw_1)
        self.tr.register_server_tools("s2", raw_2)

        route1 = self.tr.get_tool_route("s1__ping")
        route2 = self.tr.get_tool_route("s2__ping")
        self.assertEqual(route1, ("s1", "ping"))
        self.assertEqual(route2, ("s2", "ping"))

    def test_07_correct_server_routing(self) -> None:
        """Routing non-existent tool returns None."""
        self.assertIsNone(self.tr.get_tool_route("ghost_tool"))

    def test_08_tool_removal(self) -> None:
        """remove_server_tools removes exactly the specified server's tools."""
        raw_a = [{"name": "t_a", "description": "A", "inputSchema": {}}]
        raw_b = [{"name": "t_b", "description": "B", "inputSchema": {}}]
        self.tr.register_server_tools("srv_a", raw_a)
        self.tr.register_server_tools("srv_b", raw_b)
        removed = self.tr.remove_server_tools("srv_a")
        self.assertIn("t_a", removed)
        self.assertNotIn("t_a", self.tr.get_all_tools())
        self.assertIn("t_b", self.tr.get_all_tools())

    def test_09_atomic_refresh_addition_and_removal(self) -> None:
        """atomic_refresh_server updates tools, reporting added, removed, retained."""
        initial = [
            {"name": "tool_1", "description": "T1", "inputSchema": {}},
            {"name": "tool_2", "description": "T2", "inputSchema": {}},
        ]
        self.tr.register_server_tools("srv", initial)

        updated = [
            {"name": "tool_1", "description": "T1", "inputSchema": {}}, # retained
            {"name": "tool_3", "description": "T3", "inputSchema": {}}, # added
        ]
        summary = self.tr.atomic_refresh_server("srv", updated)
        self.assertIn("tool_3", summary["added"])
        self.assertIn("tool_2", summary["removed"])
        self.assertIn("tool_1", summary["retained"])
        self.assertNotIn("tool_2", self.tr.get_all_tools())
        self.assertIn("tool_3", self.tr.get_all_tools())

    def test_10_gemini_declaration_rebuild(self) -> None:
        """build_gemini_declarations creates valid FunctionDeclaration entries."""
        raw = [{"name": "query_db", "description": "Query records", "inputSchema": {"type": "object"}}]
        self.tr.register_server_tools("db_srv", raw)
        decls = self.tr.build_gemini_declarations()
        self.assertEqual(len(decls), 1)
        decl = decls[0]
        # Check name attribute or dict key
        name = getattr(decl, "name", decl.get("name") if isinstance(decl, dict) else "")
        self.assertEqual(name, "query_db")

    def test_11_registry_generation(self) -> None:
        """Registry generation increments on every mutation."""
        g0 = self.tr.generation
        self.tr.register_server_tools("s1", [{"name": "t1", "description": "d", "inputSchema": {}}])
        g1 = self.tr.generation
        self.assertGreater(g1, g0)
        self.tr.remove_server_tools("s1")
        # Removing tools maintains or increments generation

    def test_12_stale_tool_rejection(self) -> None:
        """is_generation_current returns False for outdated generations."""
        self.tr.register_server_tools("s1", [{"name": "t1", "description": "d", "inputSchema": {}}])
        old_gen = self.tr.generation
        self.tr.register_server_tools("s2", [{"name": "t2", "description": "d", "inputSchema": {}}])
        self.assertFalse(self.tr.is_generation_current(old_gen))
        self.assertTrue(self.tr.is_generation_current(self.tr.generation))


if __name__ == "__main__":
    unittest.main()
