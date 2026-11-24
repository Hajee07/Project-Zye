"""
Tests for Day 32 Mathematical Expression Security & AST Sandbox.
"""

from __future__ import annotations

import unittest
from zye_computer_intelligence.mathematics.expression_security import (
    ExpressionSecurityValidator,
    MathSecurityError,
)
from zye_computer_intelligence.mathematics.math_expression_parser import MathExpressionParser


class TestDay32MathSecurity(unittest.TestCase):
    """Verifies strict security validation, AST whitelisting, depth/length/exponent limits."""

    def test_01_valid_mathematical_expressions(self):
        """Verifies valid algebraic, trigonometric, and scientific expressions pass cleanly."""
        valid_expressions = [
            "2*x + 5",
            "sin(x)**2 + cos(x)**2",
            "exp(-x**2)",
            "sqrt(x**2 + y**2)",
            "(x + 1)/(x - 1)",
            "log(x + 1) + 3*x",
            "tan(x) + sec(x)",
            "x^2 + 2x + 1",  # Preprocessing handles ^ and 2x
        ]
        for expr in valid_expressions:
            tree = ExpressionSecurityValidator.validate(expr)
            self.assertIsNotNone(tree, f"Valid expression failed: {expr}")

    def test_02_rejection_of_system_calls_and_imports(self):
        """Verifies malicious attempts to import, execute, or access system internals are blocked."""
        malicious = [
            "__import__('os').system('dir')",
            "open('passwords.txt', 'r')",
            "exec('import os')",
            "eval('2 + 2')",
            "subprocess.run(['cmd'])",
            "globals()",
            "locals()",
            "exit()",
            "quit()",
            "breakpoint()",
        ]
        for code in malicious:
            with self.assertRaises(MathSecurityError, msg=f"Should reject: {code}"):
                ExpressionSecurityValidator.validate(code)

    def test_03_rejection_of_attribute_access_and_introspection(self):
        """Verifies attribute access like x.__class__ or x.mro() is strictly rejected."""
        introspections = [
            "x.__class__",
            "x.__dict__",
            "x.__subclasses__()",
            "(1).__class__.__bases__[0]",
            "math.__dict__",
        ]
        for code in introspections:
            with self.assertRaises(MathSecurityError, msg=f"Should reject introspection: {code}"):
                ExpressionSecurityValidator.validate(code)

    def test_04_expression_length_limit(self):
        """Verifies expressions exceeding 1000 characters are rejected."""
        long_expr = "x + " * 350 + "1"
        self.assertGreater(len(long_expr), 1000)
        with self.assertRaises(MathSecurityError):
            ExpressionSecurityValidator.validate(long_expr)

    def test_05_ast_nesting_depth_limit(self):
        """Verifies expressions exceeding AST nesting depth limit of 25 are rejected."""
        deep_expr = "sin(" * 30 + "x" + ")" * 30
        with self.assertRaises(MathSecurityError):
            ExpressionSecurityValidator.validate(deep_expr)

    def test_06_exponent_magnitude_limit(self):
        """Verifies large exponents (e.g. x**1000) are rejected to prevent computational bombs."""
        large_exp = "x**500"
        with self.assertRaises(MathSecurityError):
            ExpressionSecurityValidator.validate(large_exp)

    def test_07_disallowed_function_calls(self):
        """Verifies non-whitelisted functions are rejected."""
        disallowed = [
            "format(x)",
            "compile('x', 'file', 'eval')",
            "getattr(x, 'val')",
            "custom_unsafe_func(x)",
        ]
        for code in disallowed:
            with self.assertRaises(MathSecurityError):
                ExpressionSecurityValidator.validate(code)


if __name__ == "__main__":
    unittest.main()
