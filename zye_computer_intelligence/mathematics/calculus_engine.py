"""
Symbolic Calculus Engine.
Computes symbolic derivatives (partial, higher-order, gradient), definite and indefinite integrals,
limits (two-sided, directional, infinite), and Taylor/Maclaurin series expansions.
"""

from __future__ import annotations

import logging
from typing import Any
import sympy

from .math_expression_parser import MathExpressionParser
from .symbolic_engine import SymbolicEngine

logger = logging.getLogger("zye.computer_intelligence.calculus")


class CalculusEngine:
    """Performs exact symbolic calculus operations."""

    @staticmethod
    def differentiate(
        expression_str: str,
        variable: str | None = None,
        order: int = 1,
    ) -> dict[str, Any]:
        """Calculates first or higher-order derivatives with respect to a variable."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        free_vars = SymbolicEngine.extract_free_symbols(expr)
        var_name = variable or (free_vars[0] if free_vars else "x")
        sym = sympy.Symbol(var_name)

        order_val = max(1, min(int(order), 20))
        derived = sympy.diff(expr, sym, order_val)

        return {
            "status": "SUCCESS",
            "operation": "differentiate",
            "original_expression": str(expr),
            "variable": var_name,
            "order": order_val,
            "derivative": str(derived),
            "latex": sympy.latex(derived),
            "is_exact": True,
        }

    @staticmethod
    def calculate_gradient(
        expression_str: str,
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calculates multivariable gradient vector."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        free_vars = variables or SymbolicEngine.extract_free_symbols(expr)
        if not free_vars:
            free_vars = ["x"]

        grad_dict: dict[str, str] = {}
        for v in free_vars:
            sym = sympy.Symbol(v)
            grad_dict[v] = str(sympy.diff(expr, sym))

        return {
            "status": "SUCCESS",
            "operation": "gradient",
            "original_expression": str(expr),
            "variables": free_vars,
            "gradient": grad_dict,
        }

    @staticmethod
    def integrate(
        expression_str: str,
        variable: str | None = None,
        lower_bound: float | str | None = None,
        upper_bound: float | str | None = None,
    ) -> dict[str, Any]:
        """Calculates definite or indefinite symbolic integrals."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        free_vars = SymbolicEngine.extract_free_symbols(expr)
        var_name = variable or (free_vars[0] if free_vars else "x")
        sym = sympy.Symbol(var_name)

        # Definite integration
        if lower_bound is not None and upper_bound is not None:
            low = MathExpressionParser.parse_to_sympy(str(lower_bound))
            high = MathExpressionParser.parse_to_sympy(str(upper_bound))
            integrated = sympy.integrate(expr, (sym, low, high))

            try:
                numeric_val = float(integrated.evalf())
            except Exception:
                numeric_val = None

            return {
                "status": "SUCCESS",
                "operation": "definite_integral",
                "original_expression": str(expr),
                "variable": var_name,
                "lower_bound": str(low),
                "upper_bound": str(high),
                "result": str(integrated),
                "numeric_result": numeric_val,
                "latex": sympy.latex(integrated),
                "is_exact": True,
            }

        # Indefinite integration
        integrated = sympy.integrate(expr, sym)
        return {
            "status": "SUCCESS",
            "operation": "indefinite_integral",
            "original_expression": str(expr),
            "variable": var_name,
            "result": f"{integrated} + C",
            "antiderivative": str(integrated),
            "latex": f"{sympy.latex(integrated)} + C",
            "is_exact": True,
        }

    @staticmethod
    def calculate_limit(
        expression_str: str,
        variable: str | None = None,
        target_point: float | str = 0,
        direction: str = "+-",
    ) -> dict[str, Any]:
        """Calculates two-sided, left, right, or infinite limits."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        free_vars = SymbolicEngine.extract_free_symbols(expr)
        var_name = variable or (free_vars[0] if free_vars else "x")
        sym = sympy.Symbol(var_name)
        target = MathExpressionParser.parse_to_sympy(str(target_point))

        # Direction: "+-" (two-sided), "+" (right), "-" (left)
        dir_val = direction if direction in ("+-", "+", "-") else "+-"
        lim_val = sympy.limit(expr, sym, target, dir=dir_val)

        return {
            "status": "SUCCESS",
            "operation": "limit",
            "original_expression": str(expr),
            "variable": var_name,
            "target_point": str(target),
            "direction": dir_val,
            "limit": str(lim_val),
            "latex": sympy.latex(lim_val),
            "is_exact": True,
        }

    @staticmethod
    def calculate_taylor_series(
        expression_str: str,
        variable: str | None = None,
        expansion_point: float | str = 0,
        order: int = 6,
        point: float | str | None = None,
    ) -> dict[str, Any]:
        """Calculates Taylor or Maclaurin series expansion to specified order."""
        if point is not None:
            expansion_point = point
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        free_vars = SymbolicEngine.extract_free_symbols(expr)
        var_name = variable or (free_vars[0] if free_vars else "x")
        sym = sympy.Symbol(var_name)
        pt = MathExpressionParser.parse_to_sympy(str(expansion_point))
        order_val = max(1, min(int(order), 20))

        series_with_order = expr.series(sym, x0=pt, n=order_val)
        series_poly = series_with_order.removeO()

        return {
            "status": "SUCCESS",
            "operation": "taylor_series",
            "original_expression": str(expr),
            "variable": var_name,
            "expansion_point": str(pt),
            "order": order_val,
            "series": str(series_with_order),
            "truncated_polynomial": str(series_poly),
            "latex": sympy.latex(series_with_order),
            "is_exact": True,
        }
