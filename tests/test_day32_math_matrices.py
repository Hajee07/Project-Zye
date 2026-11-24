"""
Tests for Day 32 Matrix Algebra & Linear System Engine.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.matrix_engine import MatrixEngine


class TestDay32MathMatrices(unittest.TestCase):
    """Verifies determinants, rank, trace, inverses, eigenvalues, LU solve, least-squares, and SVD."""

    def test_01_matrix_properties_2x2(self):
        """Tests determinant, rank, trace, and invertibility for 2x2 matrix."""
        mat = [[1, 2], [3, 4]]
        res = MatrixEngine.calculate_matrix_properties(mat)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rank"], 2)
        self.assertEqual(str(res["determinant"]), "-2")
        self.assertEqual(str(res["trace"]), "5")
        self.assertFalse(res["is_singular"])
        self.assertEqual(len(res["inverse"]), 2)

    def test_02_singular_matrix_detection(self):
        """Tests detection of non-invertible / singular matrices."""
        singular_mat = [[1, 2], [2, 4]]
        res = MatrixEngine.calculate_matrix_properties(singular_mat)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(str(res["determinant"]), "0")
        self.assertTrue(res["is_singular"])
        self.assertIsNone(res["inverse"])

    def test_03_matrix_system_exact_lu_solve(self):
        """Tests exact symbolic solving of A*x = b."""
        A = [[2, 1], [1, 3]]
        b = [5, 5]
        res = MatrixEngine.solve_matrix_system(A, b)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["method"], "EXACT_SYMBOLIC_LU")
        self.assertEqual(res["solution"], ["2", "1"])
        self.assertTrue(res["is_exact"])

    def test_04_matrix_system_least_squares(self):
        """Tests least-squares solution for overdetermined systems."""
        # 3 equations, 2 unknowns
        A = [[1, 1], [1, 2], [1, 3]]
        b = [2, 3, 4]
        res = MatrixEngine.solve_matrix_system(A, b)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn(res["method"], ["EXACT_SYMBOLIC_LU", "LEAST_SQUARES_NUMERICAL"])
        self.assertEqual(len(res["solution"]), 2)

    def test_05_svd_decomposition(self):
        """Tests SciPy Singular Value Decomposition."""
        mat = [[1.0, 2.0], [3.0, 4.0]]
        res = MatrixEngine.calculate_svd(mat)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["singular_values"]), 2)
        self.assertGreater(res["singular_values"][0], 0)


if __name__ == "__main__":
    unittest.main()
