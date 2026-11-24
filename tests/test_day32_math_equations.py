"""
Tests for Day 32 Domain-Aware Equation Solving Engine.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.equation_solver import EquationSolver


class TestDay32MathEquations(unittest.TestCase):
    """Verifies single-variable equation solving, systems of equations, domain filtering, and inequalities."""

    def test_01_single_variable_linear(self):
        """Tests solving single-variable linear equations."""
        res = EquationSolver.solve_single_variable("2*x + 5 = 15")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solutions"])
        self.assertEqual(res["solutions"], ["5"])

    def test_02_single_variable_quadratic(self):
        """Tests solving quadratic equations yielding multiple roots."""
        res = EquationSolver.solve_single_variable("x**2 - 5*x + 6 = 0")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solutions"])
        solutions = sorted([int(s) for s in res["solutions"]])
        self.assertEqual(solutions, [2, 3])

    def test_03_domain_filtering_real_vs_complex(self):
        """Tests domain awareness (REAL vs COMPLEX) for equations with imaginary roots."""
        # In REAL domain: x**2 + 1 = 0 has no real solutions
        res_real = EquationSolver.solve_single_variable("x**2 + 1 = 0", domain="REAL")
        self.assertEqual(res_real["status"], "SUCCESS")
        self.assertFalse(res_real["has_solutions"])
        self.assertEqual(len(res_real["solutions"]), 0)

        # In COMPLEX domain: x**2 + 1 = 0 has roots {-I, I}
        res_cplx = EquationSolver.solve_single_variable("x**2 + 1 = 0", domain="COMPLEX")
        self.assertEqual(res_cplx["status"], "SUCCESS")
        self.assertTrue(res_cplx["has_solutions"])
        self.assertTrue(any("I" in s for s in res_cplx["solutions"]))

    def test_04_linear_system_solving(self):
        """Tests simultaneous linear system solving."""
        res = EquationSolver.solve_system(["x + y = 10", "x - y = 2"], ["x", "y"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solutions"])
        # x = 6, y = 4
        self.assertIn("6", str(res["solutions"]))
        self.assertIn("4", str(res["solutions"]))

    def test_05_nonlinear_system_solving(self):
        """Tests simultaneous nonlinear system solving (e.g. circle and line)."""
        res = EquationSolver.solve_system(["x**2 + y**2 = 25", "y = 0"], ["x", "y"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["has_solutions"])
        self.assertIn("5", str(res["solutions"]))
        self.assertIn("-5", str(res["solutions"]))

    def test_06_univariate_inequality_solving(self):
        """Tests algebraic inequality solving."""
        res = EquationSolver.solve_inequality("2*x - 4 > 0", "x")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("2", res["solution_set"])


if __name__ == "__main__":
    unittest.main()
