"""
Numerical Scientific Computing Engine (SciPy).
Executes numerical root finding, scalar and multivariable optimization,
numerical quadrature, and differential equation integration (IVP).
"""

from __future__ import annotations

import logging
from typing import Any
import numpy as np
import scipy.integrate
import scipy.optimize
import sympy

from .math_expression_parser import MathExpressionParser
from .symbolic_engine import SymbolicEngine

logger = logging.getLogger("zye.computer_intelligence.numerical")


class NumericalEngine:
    """Executes deterministic scientific numerical computations using SciPy and NumPy."""

    @staticmethod
    def find_scalar_root(
        expression_str: str,
        initial_guess: float = 1.0,
        bracket: tuple[float, float] | None = None,
        variable: str = "x",
        tolerance: float = 1e-7,
    ) -> dict[str, Any]:
        """Finds a numerical root of f(x) = 0 near an initial guess or within a bracket."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        sym = sympy.Symbol(variable)

        # Convert SymPy expression to fast numerical lambda
        f_num = sympy.lambdify(sym, expr, modules=["numpy"])

        try:
            if bracket is not None:
                res = scipy.optimize.root_scalar(
                    f_num, bracket=bracket, method="brentq", xtol=tolerance
                )
            else:
                res = scipy.optimize.root_scalar(
                    f_num, x0=initial_guess, method="secant", xtol=tolerance
                )

            root_val = float(res.root)
            residual = abs(float(f_num(root_val)))

            return {
                "status": "SUCCESS",
                "converged": bool(res.converged),
                "root": round(root_val, 8),
                "residual": round(residual, 10),
                "iterations": int(res.iterations) if hasattr(res, "iterations") else None,
                "tolerance": tolerance,
                "is_verified": residual <= (tolerance * 10),
            }
        except Exception as e:
            logger.error("Numerical root finding failed for '%s': %s", expression_str, e)
            return {
                "status": "ERROR",
                "error_code": "ROOT_FINDING_FAILED",
                "message": f"Numerical root finding did not converge: {e}",
            }

    @staticmethod
    def optimize_function(
        expression_str: str,
        initial_guess: list[float] | float = 0.0,
        minimize_flag: bool = True,
        variable: str | list[str] = "x",
        bounds: list[tuple[float | None, float | None]] | None = None,
    ) -> dict[str, Any]:
        """Performs scalar or multivariable numerical minimization or maximization."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)

        if isinstance(variable, list) and len(variable) > 1:
            # Multivariable optimization
            symbols = [sympy.Symbol(v) for v in variable]
            sym_func = sympy.lambdify(symbols, expr, modules=["numpy"])

            # Wrapper for SciPy vector input: x is array [x0, x1, ...]
            def objective(x_vec):
                val = float(sym_func(*x_vec))
                return val if minimize_flag else -val

            x0 = np.array(initial_guess, dtype=float)
            res = scipy.optimize.minimize(objective, x0, bounds=bounds)

            opt_x = [round(float(v), 6) for v in res.x]
            opt_val = float(sym_func(*res.x))

            return {
                "status": "SUCCESS",
                "optimization_type": "MINIMIZATION" if minimize_flag else "MAXIMIZATION",
                "converged": bool(res.success),
                "optimal_point": opt_x,
                "optimal_value": round(opt_val, 6),
                "message": str(res.message),
                "iterations": int(res.nit) if hasattr(res, "nit") else None,
            }
        else:
            # Scalar optimization
            var_name = variable[0] if isinstance(variable, list) else variable
            sym = sympy.Symbol(var_name)
            sym_func = sympy.lambdify(sym, expr, modules=["numpy"])

            def objective_scalar(x_val):
                val = x_val[0] if isinstance(x_val, (np.ndarray, list)) else x_val
                v = float(sym_func(val))
                return v if minimize_flag else -v

            x0 = float(initial_guess[0] if isinstance(initial_guess, list) else initial_guess)
            res = scipy.optimize.minimize(objective_scalar, np.array([x0]))

            opt_x = float(res.x[0])
            opt_val = float(sym_func(opt_x))

            return {
                "status": "SUCCESS",
                "optimization_type": "MINIMIZATION" if minimize_flag else "MAXIMIZATION",
                "converged": bool(res.success),
                "optimal_point": round(opt_x, 6),
                "optimal_value": round(opt_val, 6),
                "message": str(res.message),
            }

    @staticmethod
    def integrate_quad(
        expression_str: str,
        lower_bound: float,
        upper_bound: float,
        variable: str = "x",
    ) -> dict[str, Any]:
        """Calculates definite numerical integration using adaptive quadrature."""
        expr = MathExpressionParser.parse_to_sympy(expression_str)
        sym = sympy.Symbol(variable)
        f_num = sympy.lambdify(sym, expr, modules=["numpy"])

        try:
            val, abserr = scipy.integrate.quad(f_num, lower_bound, upper_bound)
            return {
                "status": "SUCCESS",
                "method": "SCIPY_QUAD",
                "integral": round(float(val), 8),
                "estimated_error": float(abserr),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "is_exact": False,
            }
        except Exception as e:
            logger.error("Numerical quadrature failed for '%s': %s", expression_str, e)
            return {
                "status": "ERROR",
                "error_code": "QUAD_INTEGRATION_FAILED",
                "message": f"Numerical integration failed: {e}",
            }

    @staticmethod
    def solve_ode(
        ode_expression_str: str,
        initial_value: float = 1.0,
        t_span: tuple[float, float] = (0.0, 10.0),
        y_var: str = "y",
        t_var: str = "t",
        initial_condition: float | None = None,
        variable: str | None = None,
        independent_var: str | None = None,
    ) -> dict[str, Any]:
        """Solves ordinary differential equation dy/dt = f(t, y) with initial condition y(t0) = y0."""
        if initial_condition is not None:
            initial_value = initial_condition
        if variable is not None:
            y_var = variable
        if independent_var is not None:
            t_var = independent_var

        # 1. First attempt exact symbolic solution via SymPy dsolve
        try:
            t = sympy.Symbol(t_var)
            y = sympy.Function(y_var)(t)
            # dy/dt
            ode_expr = MathExpressionParser.parse_to_sympy(ode_expression_str)
            # Form eq: Derivative(y(t), t) - f(t, y) = 0
            ode_eq = sympy.Eq(sympy.diff(y, t), ode_expr.subs(sympy.Symbol(y_var), y))
            sym_sol = sympy.dsolve(ode_eq, y, ics={y.subs(t, t_span[0]): initial_value})

            return {
                "status": "SUCCESS",
                "solution_type": "EXACT_SYMBOLIC",
                "solution": str(sym_sol.rhs),
                "latex": sympy.latex(sym_sol.rhs),
                "has_solution": True,
                "is_exact": True,
            }
        except Exception as e:
            logger.debug("Symbolic dsolve failed (%s); proceeding with numerical solve_ivp", e)

        # 2. Numerical IVP solve via SciPy
        try:
            expr = MathExpressionParser.parse_to_sympy(ode_expression_str)
            t_sym = sympy.Symbol(t_var)
            y_sym = sympy.Symbol(y_var)
            f_num = sympy.lambdify((t_sym, y_sym), expr, modules=["numpy"])

            def rhs_func(t_val, y_arr):
                return [float(f_num(t_val, y_arr[0]))]

            sol = scipy.integrate.solve_ivp(
                rhs_func, t_span, [initial_value], method="RK45", rtol=1e-6
            )

            final_t = float(sol.t[-1])
            final_y = float(sol.y[0][-1])

            return {
                "status": "SUCCESS",
                "solution_type": "NUMERICAL_IVP",
                "initial_condition": {t_var: t_span[0], y_var: initial_value},
                "final_state": {t_var: round(final_t, 4), y_var: round(final_y, 6)},
                "evaluated_points_count": len(sol.t),
                "is_exact": False,
            }
        except Exception as e2:
            logger.error("Numerical ODE solve failed: %s", e2)
            return {
                "status": "ERROR",
                "error_code": "ODE_SOLVE_FAILED",
                "message": f"Could not solve differential equation: {e2}",
            }
