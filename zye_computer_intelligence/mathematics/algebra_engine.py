"""
Algebraic Computation Engine.
Provides symbolic simplification, polynomial expansion, factorization, term collection, and substitution.
"""

from __future__ import annotations

import logging
from typing import Any
import sympy

from .math_expression_parser import MathExpressionParser

logger = logging.getLogger("zye.computer_intelligence.algebra")


class AlgebraEngine:
    """Performs deterministic symbolic algebraic manipulations."""

    @staticmethod
    def simplify_expression(expr_str: str) -> dict[str, Any]:
        """Simplifies an algebraic expression to its most compact canonical form."""
        expr = MathExpressionParser.parse_to_sympy(expr_str)
        simplified = sympy.simplify(expr)
        return {
            "status": "SUCCESS",
            "operation": "simplify",
            "original_expression": str(expr),
            "result": str(simplified),
            "latex": sympy.latex(simplified),
            "is_exact": True,
        }

    @staticmethod
    def expand_expression(expr_str: str) -> dict[str, Any]:
        """Expands algebraic products, powers, and polynomial factors."""
        expr = MathExpressionParser.parse_to_sympy(expr_str)
        expanded = sympy.expand(expr)
        return {
            "status": "SUCCESS",
            "operation": "expand",
            "original_expression": str(expr),
            "result": str(expanded),
            "latex": sympy.latex(expanded),
            "is_exact": True,
        }

    @staticmethod
    def factor_expression(expr_str: str) -> dict[str, Any]:
        """Factors polynomials and expressions into irreducible components."""
        expr = MathExpressionParser.parse_to_sympy(expr_str)
        factored = sympy.factor(expr)
        return {
            "status": "SUCCESS",
            "operation": "factor",
            "original_expression": str(expr),
            "result": str(factored),
            "latex": sympy.latex(factored),
            "is_exact": True,
        }

    @staticmethod
    def collect_terms(expr_str: str, variable: str) -> dict[str, Any]:
        """Collects powers of a specified variable in an expression."""
        expr = MathExpressionParser.parse_to_sympy(expr_str)
        sym = sympy.Symbol(variable)
        collected = sympy.collect(expr, sym)
        return {
            "status": "SUCCESS",
            "operation": "collect",
            "variable": variable,
            "original_expression": str(expr),
            "result": str(collected),
            "latex": sympy.latex(collected),
            "is_exact": True,
        }

    @staticmethod
    def substitute_expression(expr_str: str, substitutions: dict[str, Any]) -> dict[str, Any]:
        """Substitutes values or sub-expressions for variables in an expression."""
        expr = MathExpressionParser.parse_to_sympy(expr_str)
        subs_dict = {}
        for var_name, val in substitutions.items():
            sym = sympy.Symbol(var_name)
            if isinstance(val, (int, float)):
                subs_dict[sym] = sympy.Number(val)
            elif isinstance(val, str):
                subs_dict[sym] = MathExpressionParser.parse_to_sympy(val)
            else:
                subs_dict[sym] = val

        result_expr = expr.subs(subs_dict)
        return {
            "status": "SUCCESS",
            "operation": "substitute",
            "substitutions": substitutions,
            "original_expression": str(expr),
            "result": str(result_expr),
            "latex": sympy.latex(result_expr),
            "is_exact": True,
        }
