"""
Safe Mathematical Expression Parser.
Transforms validated natural/mathematical strings into SymPy AST representations
without arbitrary Python code execution.
"""

from __future__ import annotations

import ast
import logging
import re
from typing import Any
import sympy

from .expression_security import (
    ExpressionSecurityValidator,
    MathSecurityError,
    ALLOWED_FUNCTION_NAMES,
    ALLOWED_CONSTANTS,
)

logger = logging.getLogger("zye.computer_intelligence.math_parser")

SYMPY_FUNCTION_MAP = {
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "asin": sympy.asin,
    "acos": sympy.acos,
    "atan": sympy.atan,
    "sec": sympy.sec,
    "csc": sympy.csc,
    "cot": sympy.cot,
    "asec": sympy.asec,
    "acsc": sympy.acsc,
    "acot": sympy.acot,
    "sinh": sympy.sinh,
    "cosh": sympy.cosh,
    "tanh": sympy.tanh,
    "asinh": sympy.asinh,
    "acosh": sympy.acosh,
    "atanh": sympy.atanh,
    "sech": sympy.sech,
    "csch": sympy.csch,
    "coth": sympy.coth,
    "exp": sympy.exp,
    "log": sympy.log,
    "ln": sympy.log,
    "sqrt": sympy.sqrt,
    "cbrt": sympy.cbrt,
    "Abs": sympy.Abs,
    "abs": sympy.Abs,
    "factorial": sympy.factorial,
    "floor": sympy.floor,
    "ceiling": sympy.ceiling,
    "ceil": sympy.ceiling,
    "gamma": sympy.gamma,
    "sign": sympy.sign,
    "min": sympy.Min,
    "max": sympy.Max,
}

SYMPY_CONSTANT_MAP = {
    "pi": sympy.pi,
    "PI": sympy.pi,
    "E": sympy.E,
    "e": sympy.E,
    "I": sympy.I,
    "i": sympy.I,
    "oo": sympy.oo,
    "inf": sympy.oo,
    "zoo": sympy.zoo,
    "nan": sympy.nan,
}


class MathExpressionParser:
    """Parses mathematical strings into SymPy objects deterministically and securely."""

    @classmethod
    def normalize_math_string(cls, expr_str: str) -> str:
        """Preprocesses mathematical expressions to normalize syntax."""
        cleaned = ExpressionSecurityValidator.validate_expression_string(expr_str)

        # 1. Replace caret ^ with ** for exponentiation
        cleaned = re.sub(r"\^", "**", cleaned)

        # 2. Insert multiplication between number and variable (e.g. 2x -> 2*x, 3.5y -> 3.5*y)
        cleaned = re.sub(r"(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)", r"\1*\2", cleaned)

        # 3. Insert multiplication between parenthesis and variable/parenthesis (e.g. 2(x+1) -> 2*(x+1), (x+1)(x-1) -> (x+1)*(x-1))
        cleaned = re.sub(r"(\d+)\s*\(", r"\1*(", cleaned)
        cleaned = re.sub(r"\)\s*\(", r")*(", cleaned)
        cleaned = re.sub(r"\)\s*([a-zA-Z_]\w*)", r")*\1", cleaned)

        return cleaned

    @classmethod
    def parse_to_sympy(cls, expr_str: str, default_variables: list[str] | None = None) -> Any:
        """Parses a mathematical expression or equation string into a SymPy expression or Eq."""
        normalized = cls.normalize_math_string(expr_str)

        # Detect equation '=' (replace single '=' with '==' for AST parser if not already relational)
        if "=" in normalized and not re.search(r"[<>]|==", normalized):
            parts = normalized.split("=")
            if len(parts) == 2:
                lhs_str = parts[0].strip()
                rhs_str = parts[1].strip()
                lhs_expr = cls._parse_single_expr(lhs_str)
                rhs_expr = cls._parse_single_expr(rhs_str)
                return sympy.Eq(lhs_expr, rhs_expr)
            else:
                raise MathSecurityError("Multiple equality '=' symbols in equation are not supported.")

        # Detect inequalities: <=, >=, <, >
        for op in ("<=", ">=", "<", ">"):
            if op in normalized:
                parts = normalized.split(op)
                if len(parts) == 2:
                    lhs = cls._parse_single_expr(parts[0].strip())
                    rhs = cls._parse_single_expr(parts[1].strip())
                    if op == "<=":
                        return sympy.LessThan(lhs, rhs)
                    elif op == ">=":
                        return sympy.GreaterThan(lhs, rhs)
                    elif op == "<":
                        return sympy.StrictLessThan(lhs, rhs)
                    elif op == ">":
                        return sympy.StrictGreaterThan(lhs, rhs)

        # Single expression
        return cls._parse_single_expr(normalized)

    @classmethod
    def _parse_single_expr(cls, expr_str: str) -> sympy.Expr:
        """Parses a non-relational expression string into SymPy via secure AST traversal."""
        try:
            tree = ast.parse(expr_str, mode="eval")
        except SyntaxError as e:
            raise MathSecurityError(f"Mathematical syntax error: {e}") from e

        # Validate AST security
        ExpressionSecurityValidator.validate_ast_tree(tree)

        # Convert AST node to SymPy
        return cls._eval_ast_node(tree.body)

    @classmethod
    def _eval_ast_node(cls, node: ast.AST) -> Any:
        """Deterministically evaluates approved AST nodes into SymPy objects."""
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, (int, float)):
                return sympy.Number(val)
            elif isinstance(val, complex):
                return sympy.Number(val.real) + sympy.I * sympy.Number(val.imag)
            elif isinstance(val, str):
                return sympy.Symbol(val)
            else:
                raise MathSecurityError(f"Unsupported constant type: {type(val)}")

        elif isinstance(node, ast.Name):
            name = node.id
            if name in SYMPY_CONSTANT_MAP:
                return SYMPY_CONSTANT_MAP[name]
            return sympy.Symbol(name)

        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_ast_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            else:
                raise MathSecurityError(f"Unsupported unary operator: {type(node.op)}")

        elif isinstance(node, ast.BinOp):
            left = cls._eval_ast_node(node.left)
            right = cls._eval_ast_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
            elif isinstance(node.op, ast.FloorDiv):
                return sympy.floor(left / right)
            elif isinstance(node.op, ast.Mod):
                return left % right
            elif isinstance(node.op, ast.Pow):
                return left ** right
            else:
                raise MathSecurityError(f"Unsupported binary operator: {type(node.op)}")

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise MathSecurityError("Complex function calls are prohibited.")
            fn_name = node.func.id
            if fn_name not in SYMPY_FUNCTION_MAP:
                raise MathSecurityError(f"Unsupported function '{fn_name}'.")

            sympy_fn = SYMPY_FUNCTION_MAP[fn_name]
            args = [cls._eval_ast_node(arg) for arg in node.args]
            return sympy_fn(*args)

        else:
            raise MathSecurityError(f"AST node '{type(node).__name__}' cannot be evaluated.")
