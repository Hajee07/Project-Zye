"""
Mathematical Result Verification Engine.
Substitutes proposed solutions back into original equations, calculates residuals,
and certifies exact or numerical correctness.
"""

from __future__ import annotations

import logging
from typing import Any
import sympy

from .math_expression_parser import MathExpressionParser

logger = logging.getLogger("zye.computer_intelligence.validator")


class MathematicalResultValidator:
    """Certifies mathematical outputs by evaluating substitution residuals."""

    @staticmethod
    def verify_equation_solution(
        equation_str: str,
        solution_str: str,
        variable: str = "x",
        numerical_tolerance: float = 1e-6,
    ) -> dict[str, Any]:
        """Substitutes proposed solution into equation and checks whether residual is zero."""
        try:
            eq = MathExpressionParser.parse_to_sympy(equation_str)
            sol = MathExpressionParser.parse_to_sympy(solution_str)
            sym = sympy.Symbol(variable)

            # Form residual expr: lhs - rhs = 0
            if isinstance(eq, sympy.Equality):
                residual_expr = eq.lhs - eq.rhs
            elif hasattr(eq, "lhs") and hasattr(eq, "rhs"):
                residual_expr = eq.lhs - eq.rhs
            else:
                residual_expr = eq

            # 1. Exact symbolic substitution
            subbed = residual_expr.subs(sym, sol)
            simplified_residual = sympy.simplify(subbed)

            if simplified_residual == 0 or simplified_residual is sympy.S.Zero:
                return {
                    "verification_status": "VERIFIED_EXACT",
                    "residual": 0.0,
                    "is_valid": True,
                    "is_verified": True,
                    "method": "SYMBOLIC_SUBSTITUTION",
                }

            # 2. Numerical residual check
            try:
                num_val = abs(float(simplified_residual.evalf()))
                if num_val <= numerical_tolerance:
                    return {
                        "verification_status": "VERIFIED_NUMERICALLY",
                        "residual": round(num_val, 10),
                        "is_valid": True,
                        "is_verified": True,
                        "method": "NUMERICAL_TOLERANCE",
                    }
                else:
                    return {
                        "verification_status": "FAILED_VERIFICATION",
                        "residual": round(num_val, 10),
                        "is_valid": False,
                        "method": "NUMERICAL_TOLERANCE",
                        "tolerance": numerical_tolerance,
                    }
            except Exception:
                return {
                    "verification_status": "UNVERIFIED",
                    "residual": str(simplified_residual),
                    "is_valid": False,
                    "method": "UNKNOWN",
                }
        except Exception as e:
            logger.error("Verification failed for '%s' with '%s': %s", equation_str, solution_str, e)
            return {
                "verification_status": "UNVERIFIED",
                "is_valid": False,
                "error": str(e),
            }
