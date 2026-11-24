"""
Symbolic Equation & Inequality Solver.
Solves single-variable equations, linear systems, nonlinear systems, and inequalities with domain awareness.
"""

from __future__ import annotations

import logging
from typing import Any
import sympy

from .math_expression_parser import MathExpressionParser
from .symbolic_engine import SymbolicEngine

logger = logging.getLogger("zye.computer_intelligence.equations")


class EquationSolver:
    """Solves algebraic equations and systems using SymPy solvers."""

    @staticmethod
    def solve_single_variable(
        equation_str: str,
        variable: str | None = None,
        domain: str = "REAL",
    ) -> dict[str, Any]:
        """Solves single-variable equations over specified domains (Real, Complex, Integer)."""
        parsed = MathExpressionParser.parse_to_sympy(equation_str)

        # Extract variable
        free_vars = SymbolicEngine.extract_free_symbols(parsed)
        if variable:
            var_name = variable
        elif free_vars:
            var_name = free_vars[0]
        else:
            var_name = "x"

        sym = sympy.Symbol(var_name)
        domain_upper = domain.strip().upper()

        if domain_upper == "COMPLEX":
            domain_set = sympy.S.Complexes
        elif domain_upper == "INTEGER":
            domain_set = sympy.S.Integers
        else:
            domain_set = sympy.S.Reals

        solutions_list: list[str] = []
        is_finite = True

        try:
            # 1. Try solveset for domain-aware solution set
            sol_set = sympy.solveset(parsed, sym, domain=domain_set)

            if sol_set is sympy.S.EmptySet:
                solutions_list = []
            elif isinstance(sol_set, sympy.FiniteSet):
                solutions_list = [str(s) for s in sol_set]
            elif isinstance(sol_set, sympy.ConditionSet):
                # Fallback to solve() for closed-form solutions
                raw_sols = sympy.solve(parsed, sym)
                solutions_list = [str(s) for s in raw_sols]
            else:
                solutions_list = [str(sol_set)]
                is_finite = False
        except Exception as e:
            logger.debug("solveset failed, falling back to solve(): %s", e)
            try:
                raw_sols = sympy.solve(parsed, sym)
                solutions_list = [str(s) for s in raw_sols]
            except Exception as e2:
                logger.error("Equation solving failed for '%s': %s", equation_str, e2)
                return {
                    "status": "ERROR",
                    "error_code": "EQUATION_SOLVE_FAILED",
                    "message": f"Could not solve equation: {e2}",
                }

        # Format numerical approximations if solutions exist
        numeric_solutions = []
        for sol_str in solutions_list:
            try:
                parsed_sol = sympy.sympify(sol_str)
                numeric_val = float(parsed_sol.evalf())
                numeric_solutions.append(round(numeric_val, 6))
            except Exception:
                numeric_solutions.append(None)

        return {
            "status": "SUCCESS",
            "operation": "solve_single_variable",
            "equation": str(parsed),
            "variable": var_name,
            "domain": domain_upper,
            "solutions": solutions_list,
            "numeric_solutions": numeric_solutions,
            "solution_count": len(solutions_list),
            "is_finite": is_finite,
            "has_solutions": len(solutions_list) > 0,
        }

    @staticmethod
    def solve_system(
        equations: list[str],
        variables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Solves linear and nonlinear simultaneous equation systems."""
        if not equations:
            return {
                "status": "ERROR",
                "error_code": "EMPTY_EQUATION_SYSTEM",
                "message": "At least one equation must be provided.",
            }

        parsed_eqs = [MathExpressionParser.parse_to_sympy(eq) for eq in equations]

        # Extract all variables if not specified
        if variables:
            var_names = variables
        else:
            all_free = set()
            for eq in parsed_eqs:
                all_free.update(SymbolicEngine.extract_free_symbols(eq))
            var_names = sorted(list(all_free))

        symbols = [sympy.Symbol(v) for v in var_names]

        try:
            # 1. Try linsolve first (linear solver)
            try:
                lin_sol = sympy.linsolve(parsed_eqs, symbols)
                if lin_sol and lin_sol is not sympy.S.EmptySet:
                    solutions = []
                    for sol_tuple in lin_sol:
                        sol_dict = {str(symbols[i]): str(sol_tuple[i]) for i in range(len(symbols))}
                        solutions.append(sol_dict)
                    return {
                        "status": "SUCCESS",
                        "has_solutions": len(solutions) > 0,
                        "system_type": "LINEAR",
                        "equations": [str(eq) for eq in parsed_eqs],
                        "variables": var_names,
                        "solutions": solutions,
                        "solution_count": len(solutions),
                    }
            except Exception:
                pass

            # 2. Try nonlinsolve for nonlinear systems
            try:
                nonlin_sol = sympy.nonlinsolve(parsed_eqs, symbols)
                if nonlin_sol and nonlin_sol is not sympy.S.EmptySet:
                    solutions = []
                    for sol_tuple in nonlin_sol:
                        sol_dict = {str(symbols[i]): str(sol_tuple[i]) for i in range(len(symbols))}
                        solutions.append(sol_dict)
                    return {
                        "status": "SUCCESS",
                        "has_solutions": len(solutions) > 0,
                        "system_type": "NONLINEAR",
                        "equations": [str(eq) for eq in parsed_eqs],
                        "variables": var_names,
                        "solutions": solutions,
                        "solution_count": len(solutions),
                    }
            except Exception:
                pass

            # 3. Fallback to general sympy.solve
            try:
                gen_sol = sympy.solve(parsed_eqs, symbols, dict=True)
                if gen_sol:
                    solutions = [{str(k): str(v) for k, v in s.items()} for s in gen_sol]
                    return {
                        "status": "SUCCESS",
                        "has_solutions": len(solutions) > 0,
                        "system_type": "GENERAL",
                        "equations": [str(eq) for eq in parsed_eqs],
                        "variables": var_names,
                        "solutions": solutions,
                        "solution_count": len(solutions),
                    }
            except Exception:
                pass

            # Empty set -> no solution
            return {
                "status": "SUCCESS",
                "has_solutions": False,
                "system_type": "INCONSISTENT_OR_NO_SOLUTION",
                "equations": [str(eq) for eq in parsed_eqs],
                "variables": var_names,
                "solutions": [],
                "solution_count": 0,
            }
        except Exception as e:
            logger.error("System solving failed: %s", e)
            return {
                "status": "ERROR",
                "error_code": "SYSTEM_SOLVE_FAILED",
                "message": f"Failed to solve equation system: {e}",
            }

    @staticmethod
    def solve_inequality(
        inequality_str: str,
        variable: str | None = None,
    ) -> dict[str, Any]:
        """Solves single-variable inequalities over the real numbers."""
        rel = MathExpressionParser.parse_to_sympy(inequality_str)
        from sympy.core.relational import Relational
        if not isinstance(rel, Relational):
            return {
                "status": "ERROR",
                "error_code": "NOT_AN_INEQUALITY",
                "message": f"Input '{inequality_str}' is not a valid inequality.",
            }

        free_vars = SymbolicEngine.extract_free_symbols(rel)
        var_name = variable or (free_vars[0] if free_vars else "x")
        free_symbols = rel.free_symbols
        sym = [s for s in free_symbols if s.name == var_name][0] if any(s.name == var_name for s in free_symbols) else sympy.Symbol(var_name, real=True)

        try:
            try:
                sol_interval = sympy.solveset(rel, sym, domain=sympy.S.Reals)
            except Exception:
                sol_interval = sympy.reduce_inequalities(rel, sym)

            return {
                "status": "SUCCESS",
                "operation": "solve_inequality",
                "inequality": str(rel),
                "variable": var_name,
                "solution_interval": str(sol_interval),
                "solution_set": str(sol_interval),
                "latex": sympy.latex(sol_interval),
            }
        except Exception as e:
            logger.error("Inequality solving failed for '%s': %s", inequality_str, e)
            return {
                "status": "ERROR",
                "error_code": "INEQUALITY_SOLVE_FAILED",
                "message": f"Could not solve inequality: {e}",
            }
