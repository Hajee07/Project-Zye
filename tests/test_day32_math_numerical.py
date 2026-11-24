"""
Tests for Day 32 SciPy Numerical Engine.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.numerical_engine import NumericalEngine


class TestDay32MathNumerical(unittest.TestCase):
    """Verifies root finding, scalar/multivariable optimization, adaptive quadrature, and ODE solving."""

    def test_01_scalar_root_finding(self):
        """Tests bracketed root finding for non-linear equations."""
        res = NumericalEngine.find_scalar_root("x**3 - x - 2", bracket=[1.0, 2.0])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["converged"])
        # True root is ~1.5213797
        self.assertAlmostEqual(res["root"], 1.52138, places=4)
        self.assertLess(abs(res["residual"]), 1e-6)

    def test_02_scalar_optimization(self):
        """Tests scalar minimization with SciPy."""
        res = NumericalEngine.optimize_function("(x - 3)**2 + 4", initial_guess=0.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["converged"])
        # Minimum at x = 3, value = 4
        self.assertAlmostEqual(res["optimal_point"], 3.0, places=3)
        self.assertAlmostEqual(res["optimal_value"], 4.0, places=3)

    def test_03_multivariable_optimization(self):
        """Tests multivariable minimization (e.g. paraboloid (x-1)^2 + (y-2)^2)."""
        res = NumericalEngine.optimize_function(
            "(x - 1)**2 + (y - 2)**2",
            initial_guess=[0.0, 0.0],
            variable=["x", "y"],
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["converged"])
        self.assertAlmostEqual(res["optimal_point"][0], 1.0, places=3)
        self.assertAlmostEqual(res["optimal_point"][1], 2.0, places=3)

    def test_04_adaptive_quadrature_integration(self):
        """Tests definite numerical integration using quad."""
        # Integral of exp(-x) from 0 to 1 = 1 - 1/e ~ 0.63212
        res = NumericalEngine.integrate_quad("exp(-x)", 0.0, 1.0)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertAlmostEqual(res["integral"], 0.63212, places=4)
        self.assertLess(res["estimated_error"], 1e-8)

    def test_05_ordinary_differential_equation_solve(self):
        """Tests solving 1st-order ODE (symbolic dsolve with fallback)."""
        # y' = -2*y -> y(t) = C1*exp(-2*t)
        res = NumericalEngine.solve_ode("-2*y", initial_condition=1.0, variable="y", independent_var="t")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solution"])


if __name__ == "__main__":
    unittest.main()
