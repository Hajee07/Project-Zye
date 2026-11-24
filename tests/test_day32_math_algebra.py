"""
Tests for Day 32 Symbolic Algebra Engine.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.algebra_engine import AlgebraEngine


class TestDay32MathAlgebra(unittest.TestCase):
    """Verifies simplification, expansion, factoring, term collection, and substitution."""

    def test_01_simplify_expression(self):
        """Tests simplification of polynomial, rational, and trigonometric expressions."""
        res1 = AlgebraEngine.simplify_expression("2*x + 3*x")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["result"], "5*x")

        # Trig identity: sin(x)**2 + cos(x)**2 -> 1
        res2 = AlgebraEngine.simplify_expression("sin(x)**2 + cos(x)**2")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["result"], "1")

        # Rational simplification: (x**2 - 1)/(x - 1) -> x + 1
        res3 = AlgebraEngine.simplify_expression("(x**2 - 1)/(x - 1)")
        self.assertEqual(res3["status"], "SUCCESS")
        self.assertEqual(res3["result"], "x + 1")

    def test_02_expand_expression(self):
        """Tests expansion of polynomial powers and factored products."""
        res1 = AlgebraEngine.expand_expression("(x + 2)**2")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertIn("x**2", res1["result"])
        self.assertIn("4*x", res1["result"])
        self.assertIn("4", res1["result"])

        res2 = AlgebraEngine.expand_expression("(x + y)*(x - y)")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertIn("x**2", res2["result"])
        self.assertIn("y**2", res2["result"])

    def test_03_factor_expression(self):
        """Tests polynomial factoring and difference of squares."""
        res1 = AlgebraEngine.factor_expression("x**2 - 9")
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertIn("(x - 3)", res1["result"])
        self.assertIn("(x + 3)", res1["result"])

        res2 = AlgebraEngine.factor_expression("x**2 - 5*x + 6")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertIn("(x - 2)", res2["result"])
        self.assertIn("(x - 3)", res2["result"])

    def test_04_collect_terms(self):
        """Tests grouping of polynomial terms by variable."""
        res = AlgebraEngine.collect_terms("a*x**2 + b*x**2 + c*x + d", "x")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("x**2", res["result"])

    def test_05_substitute_expression(self):
        """Tests numerical and symbolic value substitution into expressions."""
        # Numerical substitution: x**2 + 2*x + 1 with x=3 -> 16
        res1 = AlgebraEngine.substitute_expression("x**2 + 2*x + 1", {"x": "3"})
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["result"], "16")

        # Symbolic substitution: x**2 with x = y + 1 -> (y + 1)**2
        res2 = AlgebraEngine.substitute_expression("x**2", {"x": "y + 1"})
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertIn("y", res2["result"])


if __name__ == "__main__":
    unittest.main()
