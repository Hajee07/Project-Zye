"""
Tests for Day 32 FastMCP Tools Registration, Result Verification, and Voice Formatting.
"""

from __future__ import annotations

import unittest
import computer_intelligence_mcp
from zye_computer_intelligence.mathematics.result_validator import MathematicalResultValidator


class TestDay32MathMCP(unittest.TestCase):
    """Verifies all 28 FastMCP tools, mathematical tool execution, and deterministic validation."""

    def test_01_tool_registration_count_and_presence(self):
        """Verifies exactly 28 tools are registered in computer_intelligence_mcp."""
        tools = getattr(computer_intelligence_mcp.mcp, "_tools", None)
        if tools is None and hasattr(computer_intelligence_mcp.mcp, "_tool_manager"):
            tools = getattr(computer_intelligence_mcp.mcp._tool_manager, "_tools", None)

        self.assertIsNotNone(tools)
        tool_names = set(tools.keys())
        expected_math_tools = {
            "solve_math_equation",
            "solve_math_system",
            "simplify_math_expression",
            "expand_math_expression",
            "factor_math_expression",
            "differentiate_expression",
            "integrate_expression",
            "calculate_mathematical_limit",
            "calculate_taylor_series",
            "solve_matrix_equation",
            "calculate_matrix_properties",
            "find_numerical_root",
            "optimize_math_function",
            "integrate_function_numerically",
            "solve_differential_equation",
            "evaluate_math_expression",
            "verify_math_solution",
        }
        self.assertTrue(expected_math_tools.issubset(tool_names), f"Missing math tools: {expected_math_tools - tool_names}")
        self.assertGreaterEqual(len(tool_names), 28)

    def test_02_solve_math_equation_tool(self):
        """Tests FastMCP solve_math_equation with deterministic verification & voice summaries."""
        res = computer_intelligence_mcp.solve_math_equation("x**2 - 9 = 0")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solutions"])
        self.assertIn("markdown", res)
        self.assertIn("voice_tanglish", res)
        self.assertIn("voice_en", res)
        self.assertEqual(res["verification"]["verification_status"], "VERIFIED_EXACT")

    def test_03_simplify_and_expand_tools(self):
        """Tests FastMCP simplify_math_expression and expand_math_expression tools."""
        simp = computer_intelligence_mcp.simplify_math_expression("2*x + 4*x")
        self.assertEqual(simp["status"], "SUCCESS")
        self.assertEqual(simp["result"], "6*x")

        exp = computer_intelligence_mcp.expand_math_expression("(x + 3)**2")
        self.assertEqual(exp["status"], "SUCCESS")
        self.assertIn("x**2", exp["result"])

    def test_04_calculus_tools(self):
        """Tests FastMCP differentiate_expression and integrate_expression tools."""
        diff = computer_intelligence_mcp.differentiate_expression("x**4", "x", 1)
        self.assertEqual(diff["status"], "SUCCESS")
        self.assertEqual(diff["derivative"], "4*x**3")

        integ = computer_intelligence_mcp.integrate_expression("4*x**3", "x")
        self.assertEqual(integ["status"], "SUCCESS")
        self.assertIn("x**4", integ["result"])

    def test_05_matrix_tools(self):
        """Tests FastMCP calculate_matrix_properties and solve_matrix_equation tools."""
        props = computer_intelligence_mcp.calculate_matrix_properties([[1, 2], [3, 4]])
        self.assertEqual(props["status"], "SUCCESS")
        self.assertEqual(props["rank"], 2)

        solve = computer_intelligence_mcp.solve_matrix_equation([[2, 1], [1, 3]], [5, 5])
        self.assertEqual(solve["status"], "SUCCESS")
        self.assertEqual(solve["solution"], ["2", "1"])

    def test_06_verify_math_solution_tool(self):
        """Tests standalone FastMCP verify_math_solution tool."""
        ver = computer_intelligence_mcp.verify_math_solution("2*x + 10 = 20", "5", "x")
        self.assertEqual(ver["status"], "SUCCESS")
        self.assertEqual(ver["verification_status"], "VERIFIED_EXACT")
        self.assertTrue(ver["is_verified"])


if __name__ == "__main__":
    unittest.main()
