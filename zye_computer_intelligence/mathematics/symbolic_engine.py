"""
Core Symbolic Mathematics Engine.
Provides domain-aware variable management, symbol extraction, and SymPy object conversions.
"""

from __future__ import annotations

import logging
from typing import Any
import sympy

logger = logging.getLogger("zye.computer_intelligence.symbolic")


class SymbolicEngine:
    """Manages symbolic variables, domains, and core conversions."""

    @staticmethod
    def get_symbols(variables: list[str] | None, domain: str = "REAL") -> list[sympy.Symbol]:
        """Creates SymPy symbols with specified domain assumptions."""
        if not variables:
            return [sympy.Symbol("x", real=True)]

        domain_upper = domain.strip().upper()
        syms: list[sympy.Symbol] = []
        for v in variables:
            v_name = str(v).strip()
            if domain_upper == "REAL":
                syms.append(sympy.Symbol(v_name, real=True))
            elif domain_upper == "POSITIVE":
                syms.append(sympy.Symbol(v_name, positive=True))
            elif domain_upper == "INTEGER":
                syms.append(sympy.Symbol(v_name, integer=True))
            elif domain_upper == "COMPLEX":
                syms.append(sympy.Symbol(v_name, complex=True))
            else:
                syms.append(sympy.Symbol(v_name))
        return syms

    @staticmethod
    def extract_free_symbols(expr: sympy.Expr | sympy.Relational) -> list[str]:
        """Extracts sorted free variable symbol names from an expression."""
        if hasattr(expr, "free_symbols"):
            return sorted([s.name for s in expr.free_symbols])
        return []
