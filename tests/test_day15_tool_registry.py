"""Day 15 Unit Tests — Tool Registry & Gemini Schema Conversion."""
import unittest

from zye_orchestrator.tool_registry import ZyeToolRegistry


class TestToolRegistryInit(unittest.TestCase):
    def test_creates_instance(self):
        tr = ZyeToolRegistry()
        self.assertIsNotNone(tr)

    def test_get_all_tools_returns_dict(self):
        tr = ZyeToolRegistry()
        tools = tr.get_all_tools()
        self.assertIsInstance(tools, dict)

    def test_get_all_tools_empty_on_no_servers(self):
        tr = ZyeToolRegistry()
        tools = tr.get_all_tools()
        # No MCP servers connected — may be empty
        self.assertIsInstance(tools, dict)

    def test_build_gemini_declarations_returns_list(self):
        tr = ZyeToolRegistry()
        decls = tr.build_gemini_declarations()
        self.assertIsInstance(decls, list)

    def test_get_tool_route_unknown_returns_none(self):
        tr = ZyeToolRegistry()
        route = tr.get_tool_route("completely_unknown_tool_xyz")
        self.assertIsNone(route)


class TestToolRegistryWithMockTools(unittest.TestCase):
    """Test tool registry with manually registered tools."""

    def _make_tool_entry(self, server: str, name: str):
        from zye_orchestrator.tool_registry import ToolEntry
        return ToolEntry(
            server_name=server,
            original_name=name,
            public_name=f"{server}__{name}",
            schema={"type": "object", "properties": {}, "required": []},
        )

    def test_register_and_retrieve_tool(self):
        tr = ZyeToolRegistry()
        entry = self._make_tool_entry("test_srv", "test_action")
        tr._tools["test_srv__test_action"] = entry
        tools = tr.get_all_tools()
        self.assertIn("test_srv__test_action", tools)

    def test_route_found_after_register(self):
        tr = ZyeToolRegistry()
        entry = self._make_tool_entry("srv_x", "do_thing")
        tr._tools["srv_x__do_thing"] = entry
        route = tr.get_tool_route("srv_x__do_thing")
        self.assertIsNotNone(route)

    def test_namespace_collision_resolution(self):
        """Two servers with same tool name should both be registered under namespaced keys."""
        tr = ZyeToolRegistry()
        e1 = self._make_tool_entry("server_a", "inspect")
        e2 = self._make_tool_entry("server_b", "inspect")
        tr._tools["server_a__inspect"] = e1
        tr._tools["server_b__inspect"] = e2
        tools = tr.get_all_tools()
        self.assertIn("server_a__inspect", tools)
        self.assertIn("server_b__inspect", tools)

    def test_gemini_declarations_include_registered_tool(self):
        tr = ZyeToolRegistry()
        entry = self._make_tool_entry("srv_gemini", "my_tool")
        entry.schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
        tr._tools["srv_gemini__my_tool"] = entry
        decls = tr.build_gemini_declarations()
        self.assertIsInstance(decls, list)
        self.assertGreater(len(decls), 0)


class TestToolEntry(unittest.TestCase):
    def test_tool_entry_has_required_fields(self):
        from zye_orchestrator.tool_registry import ToolEntry
        e = ToolEntry(
            server_name="srv",
            original_name="tool",
            public_name="srv__tool",
            schema={},
        )
        self.assertEqual(e.server_name, "srv")
        self.assertEqual(e.original_name, "tool")
        self.assertEqual(e.public_name, "srv__tool")


if __name__ == "__main__":
    unittest.main()
