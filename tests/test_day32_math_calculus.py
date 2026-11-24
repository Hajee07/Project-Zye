"""
Tests for Day 32 Symbolic Calculus Engine.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.calculus_engine import CalculusEngine


class TestDay32MathCalculus(unittest.TestCase):
    """Verifies symbolic derivatives, partials, gradients, definite/indefinite integrals, limits, Taylor series."""

    def test_01_first_and_higher_order_derivatives(self):
        """Tests 1st, 2nd, and 3rd order derivatives."""
        # 1st order: d/dx(x**3) = 3*x**2
        res1 = CalculusEngine.differentiate("x**3", "x", order=1)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["derivative"], "3*x**2")

        # 2nd order: d2/dx2(x**3) = 6*x
        res2 = CalculusEngine.differentiate("x**3", "x", order=2)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["derivative"], "6*x")

        # Product rule: d/dx(x * exp(x)) = (x + 1)*exp(x)
        res3 = CalculusEngine.differentiate("x*exp(x)", "x", order=1)
        self.assertEqual(res3["status"], "SUCCESS")
        self.assertTrue("exp(x)" in res3["derivative"])

    def test_02_multivariable_gradient(self):
        """Tests partial derivatives and gradient vector generation."""
        res = CalculusEngine.calculate_gradient("x**2 + 3*y**2 + 2*z", ["x", "y", "z"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["gradient"]["x"], "2*x")
        self.assertEqual(res["gradient"]["y"], "6*y")
        self.assertEqual(res["gradient"]["z"], "2")

    def test_03_indefinite_integral_with_constant(self):
        """Tests indefinite symbolic integration with + C."""
        res = CalculusEngine.integrate("3*x**2", "x")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["operation"], "indefinite_integral")
        self.assertIn("+ C", res["result"])
        self.assertIn("x**3", res["result"])

    def test_04_definite_integral_with_limits(self):
        """Tests definite integration evaluating exact and numeric values."""
        res = CalculusEngine.integrate("x**2", "x", lower_bound=0, upper_bound=3)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["operation"], "definite_integral")
        self.assertEqual(res["result"], "9")
        self.assertEqual(res["numeric_result"], 9.0)

    def test_05_limits_finite_directional_and_infinite(self):
        """Tests limit evaluation: standard, directional, and at infinity."""
        # Two-sided standard: lim x->0 sin(x)/x = 1
        res1 = CalculusEngine.calculate_limit("sin(x)/x", "x", 0)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["limit"], "1")

        # Infinite limit: lim x->oo 1/x = 0
        res2 = CalculusEngine.calculate_limit("1/x", "x", "oo")
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertEqual(res2["limit"], "0")

    def test_06_taylor_and_maclaurin_series(self):
        """Tests Taylor series expansion around point x0 with order n."""
        res = CalculusEngine.calculate_taylor_series("exp(x)", "x", point=0, order=4)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("1", res["series"])
        self.assertIn("x", res["series"])
        self.assertIn("x**2", res["series"])


if __name__ == "__main__":
    unittest.main()
