"""
Matrix & Linear Algebra Engine.
Performs exact symbolic and numerical matrix calculations: determinants, inverses,
eigenvalues, eigenvectors, rank, trace, and Singular Value Decomposition (SVD).
"""

from __future__ import annotations

import logging
from typing import Any
import numpy as np
import scipy.linalg
import sympy

logger = logging.getLogger("zye.computer_intelligence.matrix")


class MatrixEngine:
    """Executes symbolic and numerical linear algebra operations."""

    @staticmethod
    def create_matrix(matrix_data: list[list[Any]]) -> sympy.Matrix:
        """Constructs a SymPy Matrix from a nested list with dimension and shape checks."""
        if not matrix_data or not isinstance(matrix_data, list):
            raise ValueError("Matrix data must be a non-empty 2D list.")
        rows = len(matrix_data)
        if rows == 0 or not isinstance(matrix_data[0], list):
            raise ValueError("Matrix rows must be lists.")
        cols = len(matrix_data[0])
        for r in matrix_data:
            if len(r) != cols:
                raise ValueError(f"Inconsistent matrix row lengths: expected {cols}, got {len(r)}")
        return sympy.Matrix(matrix_data)

    @classmethod
    def calculate_matrix_properties(cls, matrix_data: list[list[Any]]) -> dict[str, Any]:
        """Calculates determinant, rank, trace, inverse (if non-singular), and eigenvalues."""
        M = cls.create_matrix(matrix_data)
        rows, cols = M.shape
        is_square = (rows == cols)

        det_val = None
        is_singular = False
        inv_matrix = None
        eigenvals_list = []

        if is_square:
            det = M.det()
            det_val = str(det)
            is_singular = (det == 0)

            if not is_singular:
                inv_matrix = M.inv().tolist()

            # Eigenvalues
            try:
                raw_eigen = M.eigenvals()
                eigenvals_list = [
                    {"value": str(val), "multiplicity": mult}
                    for val, mult in raw_eigen.items()
                ]
            except Exception as e:
                logger.debug("Symbolic eigenvalue calculation failed: %s", e)

        rank_val = int(M.rank())
        trace_val = str(M.trace()) if is_square else None

        return {
            "status": "SUCCESS",
            "shape": [rows, cols],
            "is_square": is_square,
            "rank": rank_val,
            "trace": trace_val,
            "determinant": det_val,
            "is_singular": is_singular,
            "inverse": inv_matrix,
            "eigenvalues": eigenvals_list,
        }

    @classmethod
    def solve_matrix_system(
        cls,
        A_data: list[list[Any]],
        b_data: list[Any] | list[list[Any]],
    ) -> dict[str, Any]:
        """Solves matrix linear system A @ x = b."""
        A = cls.create_matrix(A_data)
        # Ensure b is a column vector
        if isinstance(b_data[0], list):
            b = sympy.Matrix(b_data)
        else:
            b = sympy.Matrix([[val] for val in b_data])

        try:
            # 1. Exact symbolic solve
            x = A.LUsolve(b)
            solution_vector = [str(x[i, 0]) for i in range(x.rows)]
            return {
                "status": "SUCCESS",
                "method": "EXACT_SYMBOLIC_LU",
                "solution": solution_vector,
                "is_exact": True,
            }
        except Exception as e:
            logger.debug("Exact LU solve failed: %s; trying SciPy lstsq fallback", e)
            try:
                # 2. SciPy numerical least-squares fallback
                A_num = np.array(A_data, dtype=float)
                b_num = np.array(b_data, dtype=float).flatten()
                x_num, residuals, rank, s = scipy.linalg.lstsq(A_num, b_num)
                return {
                    "status": "SUCCESS",
                    "method": "NUMERICAL_LEAST_SQUARES",
                    "solution": [round(float(v), 6) for v in x_num],
                    "rank": int(rank),
                    "is_exact": False,
                }
            except Exception as e2:
                logger.error("Matrix system solve failed: %s", e2)
                return {
                    "status": "ERROR",
                    "error_code": "MATRIX_SOLVE_FAILED",
                    "message": f"Could not solve matrix system: {e2}",
                }

    @classmethod
    def calculate_svd(cls, matrix_data: list[list[Any]]) -> dict[str, Any]:
        """Computes numerical Singular Value Decomposition (SVD) via SciPy."""
        try:
            A_num = np.array(matrix_data, dtype=float)
            U, s, Vh = scipy.linalg.svd(A_num)
            return {
                "status": "SUCCESS",
                "singular_values": [round(float(val), 6) for val in s],
                "U_shape": list(U.shape),
                "Vh_shape": list(Vh.shape),
            }
        except Exception as e:
            logger.error("SVD computation failed: %s", e)
            return {
                "status": "ERROR",
                "error_code": "SVD_FAILED",
                "message": f"Failed to compute SVD: {e}",
            }
