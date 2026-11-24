"""
Precision & Mathematical Representation Manager.
Controls exact symbolic representations, rational preservation, and arbitrary-precision decimal formatting.
"""

from __future__ import annotations

from typing import Any
import sympy


class PrecisionManager:
    """Manages numerical precision and exact rational formatting."""

    @staticmethod
    def format_result(
        expr_obj: Any,
        precision_digits: int = 6,
        force_numeric: bool = False,
    ) -> dict[str, Any]:
        """Formats mathematical output preserving exact and numerical representations."""
        if isinstance(expr_obj, str):
            try:
                sym_obj = sympy.sympify(expr_obj)
            except Exception:
                return {"exact": expr_obj, "numeric": None}
        else:
            sym_obj = expr_obj

        # Exact symbolic string
        exact_str = str(sym_obj)
        latex_str = sympy.latex(sym_obj) if hasattr(sympy, "latex") else exact_str

        # Numerical float approximation
        numeric_str = None
        try:
            evaluated = sym_obj.evalf(precision_digits)
            numeric_str = str(evaluated)
        except Exception:
            pass

        return {
            "exact": exact_str,
            "numeric": numeric_str if (force_numeric or numeric_str is not None) else exact_str,
            "latex": latex_str,
            "is_exact": not force_numeric,
            "precision_digits": precision_digits,
        }
