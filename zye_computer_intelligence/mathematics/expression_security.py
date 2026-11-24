"""
Mathematical Expression Security Validator.
Enforces strict AST inspection, prohibits arbitrary Python code, eval(), exec(),
and bounds expression depth, token counts, and exponent magnitudes.
"""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.math_security")

MAX_EXPRESSION_LENGTH = 1000
MAX_AST_DEPTH = 25
MAX_EXPONENT_VALUE = 100.0

ALLOWED_FUNCTION_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sec", "csc", "cot", "asec", "acsc", "acot",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "sech", "csch", "coth",
    "exp", "log", "ln", "sqrt", "cbrt", "Abs", "abs",
    "factorial", "floor", "ceiling", "ceil", "gamma",
    "sign", "min", "max",
}

ALLOWED_CONSTANTS = {
    "pi", "PI", "E", "e", "I", "i", "oo", "inf", "zoo", "nan",
}

ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Compare,
    ast.Tuple,
    ast.List,
    ast.Load,
    # Binary operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    # Unary operators
    ast.UAdd, ast.USub,
    # Comparisons
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


class MathSecurityError(Exception):
    """Raised when an expression violates mathematical security constraints."""
    pass


class ExpressionSecurityValidator:
    """Validates mathematical expression strings and AST trees for safe symbolic parsing."""

    @classmethod
    def validate_expression_string(cls, expr_str: str) -> str:
        """Validates raw expression string length and checks for forbidden patterns."""
        if not expr_str or not expr_str.strip():
            raise MathSecurityError("Mathematical expression cannot be empty.")

        cleaned = expr_str.strip()
        if len(cleaned) > MAX_EXPRESSION_LENGTH:
            raise MathSecurityError(
                f"Expression exceeds maximum length of {MAX_EXPRESSION_LENGTH} characters."
            )

        # Check for obvious forbidden keywords before AST
        forbidden_patterns = [
            r"__\w+__",          # Dunder methods
            r"import\s+",        # import statements
            r"lambda\s+",        # lambda functions
            r"open\s*\(",        # file access
            r"exec\s*\(",        # exec call
            r"eval\s*\(",        # eval call
            r"system\s*\(",      # os.system
            r"subprocess",       # subprocess calls
            r"globals\s*\(",     # globals()
            r"locals\s*\(",      # locals()
            r"exit\s*\(",        # exit()
            r"quit\s*\(",        # quit()
            r"breakpoint\s*\(",  # breakpoint()
        ]
        for pat in forbidden_patterns:
            if re.search(pat, cleaned, re.IGNORECASE):
                raise MathSecurityError(f"Prohibited pattern detected in expression: '{pat}'")

        return cleaned

    @classmethod
    def validate(cls, expr_str: str) -> ast.AST:
        """Validates raw expression string, parses AST and validates all nodes recursively."""
        cleaned = cls.validate_expression_string(expr_str)
        normalized = re.sub(r"\^", "**", cleaned)
        normalized = re.sub(r"(\d+(?:\.\d+)?)\s*([a-zA-Z_]\w*)", r"\1*\2", normalized)
        normalized = re.sub(r"(\d+)\s*\(", r"\1*(", normalized)
        normalized = re.sub(r"\)\s*\(", r")*(", normalized)
        normalized = re.sub(r"\)\s*([a-zA-Z_]\w*)", r")*\1", normalized)
        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError as e:
            raise MathSecurityError(f"Syntax error in mathematical expression: {e}")
        cls.validate_ast_tree(tree)
        return tree

    @classmethod
    def validate_ast_tree(cls, tree: ast.AST) -> None:
        """Recursively validates that the AST contains only allowed mathematical nodes."""
        cls._check_node_recursive(tree, depth=0)

    @classmethod
    def _check_node_recursive(cls, node: ast.AST, depth: int) -> None:
        if depth > MAX_AST_DEPTH:
            raise MathSecurityError(f"Expression AST exceeds maximum nesting depth of {MAX_AST_DEPTH}.")

        if not isinstance(node, ALLOWED_AST_NODES):
            raise MathSecurityError(
                f"Security restriction: AST node '{type(node).__name__}' is prohibited in mathematical expressions."
            )

        # Check Calls: function name must be in allowlist
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
                if fn_name not in ALLOWED_FUNCTION_NAMES:
                    raise MathSecurityError(
                        f"Function '{fn_name}' is not in the allowed mathematical function list."
                    )
            else:
                raise MathSecurityError("Complex or dynamic function calls are prohibited.")

        # Check Names: identifier or allowed constant
        elif isinstance(node, ast.Name):
            name = node.id
            # Variable or constant identifier must be alphabetic/alphanumeric
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                raise MathSecurityError(f"Invalid variable identifier '{name}'.")

        # Check Exponent bounds to prevent CPU denial of service (e.g. 2**1000000000)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                if abs(node.right.value) > MAX_EXPONENT_VALUE:
                    raise MathSecurityError(
                        f"Exponent value {node.right.value} exceeds maximum allowed power magnitude ({MAX_EXPONENT_VALUE})."
                    )

        # Recurse children
        for child in ast.iter_child_nodes(node):
            cls._check_node_recursive(child, depth + 1)
