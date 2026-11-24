    return report


# ---------------------------------------------------------------------------
# Tool 12: Solve Single-Variable Equation
# ---------------------------------------------------------------------------
@mcp.tool()
def solve_math_equation(
    equation: str,
    variable: str | None = None,
    domain: str = "REAL",
) -> dict[str, Any]:
    """Solves algebraic, polynomial, trigonometric, or exponential equations with domain awareness."""
    try:
        res = EquationSolver.solve_single_variable(equation, variable=variable, domain=domain)
        if res["status"] == "SUCCESS" and res["has_solutions"]:
            # Verify primary solution
            first_sol = res["solutions"][0]
            var_name = res["variable"]
            ver = MathematicalResultValidator.verify_equation_solution(equation, first_sol, variable=var_name)
            res["verification"] = ver
        v_tan, v_en = MathExplainer.generate_voice_summaries(
            "equation_solving", equation, res.get("solutions", []),
            res.get("verification", {}).get("verification_status")
        )
        res["markdown"] = MathExplainer.format_step_by_step_explanation(
            "solve_equation", equation, res.get("solutions", []),
            verification=res.get("verification")
        )
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "EQUATION_SOLVE_FAILED", "message": f"Solving error: {e}"}


# ---------------------------------------------------------------------------
# Tool 13: Solve Equation System
# ---------------------------------------------------------------------------
@mcp.tool()
def solve_math_system(
    equations: list[str],
    variables: list[str] | None = None,
) -> dict[str, Any]:
    """Solves linear or nonlinear simultaneous multi-variable equation systems."""
    try:
        res = EquationSolver.solve_system(equations, variables=variables)
        v_tan, v_en = MathExplainer.generate_voice_summaries("system_solve", ", ".join(equations), res.get("solutions", []))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "SYSTEM_SOLVE_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 14: Simplify Expression
# ---------------------------------------------------------------------------
@mcp.tool()
def simplify_math_expression(expression: str) -> dict[str, Any]:
    """Simplifies an algebraic or mathematical expression to its canonical simplest form."""
    try:
        res = AlgebraEngine.simplify_expression(expression)
        v_tan, v_en = MathExplainer.generate_voice_summaries("simplify", expression, res["result"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "SIMPLIFY_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 15: Expand Expression
# ---------------------------------------------------------------------------
@mcp.tool()
def expand_math_expression(expression: str) -> dict[str, Any]:
    """Expands algebraic polynomials, powers, and products."""
    try:
        res = AlgebraEngine.expand_expression(expression)
        v_tan, v_en = MathExplainer.generate_voice_summaries("expand", expression, res["result"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "EXPAND_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 16: Factor Expression
# ---------------------------------------------------------------------------
@mcp.tool()
def factor_math_expression(expression: str) -> dict[str, Any]:
    """Factors polynomials and expressions into irreducible symbolic factors."""
    try:
        res = AlgebraEngine.factor_expression(expression)
        v_tan, v_en = MathExplainer.generate_voice_summaries("factor", expression, res["result"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "FACTOR_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 17: Differentiate Expression
# ---------------------------------------------------------------------------
@mcp.tool()
def differentiate_expression(
    expression: str,
    variable: str | None = None,
    order: int = 1,
) -> dict[str, Any]:
    """Calculates exact first or higher-order symbolic derivatives."""
    try:
        res = CalculusEngine.differentiate(expression, variable=variable, order=order)
        v_tan, v_en = MathExplainer.generate_voice_summaries("differentiate", expression, res["derivative"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "DIFF_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 18: Integrate Expression
# ---------------------------------------------------------------------------
@mcp.tool()
def integrate_expression(
    expression: str,
    variable: str | None = None,
    lower_bound: float | str | None = None,
    upper_bound: float | str | None = None,
) -> dict[str, Any]:
    """Calculates definite or indefinite symbolic integrals."""
    try:
        res = CalculusEngine.integrate(
            expression, variable=variable, lower_bound=lower_bound, upper_bound=upper_bound
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("integrate", expression, res["result"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "INTEGRATE_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 19: Calculate Limit
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_mathematical_limit(
    expression: str,
    variable: str | None = None,
    target_point: float | str = 0,
    direction: str = "+-",
) -> dict[str, Any]:
    """Evaluates symbolic two-sided, left, right, or infinite limits."""
    try:
        res = CalculusEngine.calculate_limit(
            expression, variable=variable, target_point=target_point, direction=direction
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("limit", expression, res["limit"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "LIMIT_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 20: Taylor / Maclaurin Series
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_taylor_series(
    expression: str,
    variable: str | None = None,
    expansion_point: float | str = 0,
    order: int = 6,
) -> dict[str, Any]:
    """Calculates Taylor or Maclaurin series polynomial expansion."""
    try:
        res = CalculusEngine.calculate_taylor_series(
            expression, variable=variable, expansion_point=expansion_point, order=order
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("taylor_series", expression, res["truncated_polynomial"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "SERIES_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 21: Solve Matrix Equation
# ---------------------------------------------------------------------------
@mcp.tool()
def solve_matrix_equation(
    matrix_A: list[list[float | int]],
    vector_b: list[float | int] | list[list[float | int]],
) -> dict[str, Any]:
    """Solves matrix linear equation system A @ x = b."""
    try:
        res = MatrixEngine.solve_matrix_system(matrix_A, vector_b)
        v_tan, v_en = MathExplainer.generate_voice_summaries("matrix_solve", "A @ x = b", res.get("solution", []))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "MATRIX_SOLVE_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 22: Calculate Matrix Properties
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_matrix_properties(matrix: list[list[float | int]]) -> dict[str, Any]:
    """Calculates determinant, rank, trace, inverse, and eigenvalues of a matrix."""
    try:
        res = MatrixEngine.calculate_matrix_properties(matrix)
        v_tan, v_en = MathExplainer.generate_voice_summaries("matrix_properties", "Matrix", f"det={res['determinant']}, rank={res['rank']}")
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "MATRIX_PROPS_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 23: Find Numerical Root
# ---------------------------------------------------------------------------
@mcp.tool()
def find_numerical_root(
    expression: str,
    initial_guess: float = 1.0,
    bracket: list[float] | None = None,
    variable: str = "x",
) -> dict[str, Any]:
    """Finds a verified numerical root of f(x) = 0 using SciPy."""
    try:
        b_tuple = (float(bracket[0]), float(bracket[1])) if bracket and len(bracket) == 2 else None
        res = NumericalEngine.find_scalar_root(
            expression, initial_guess=initial_guess, bracket=b_tuple, variable=variable
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("numerical_root", expression, res.get("root"))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "NUMERICAL_ROOT_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 24: Optimize Function
# ---------------------------------------------------------------------------
@mcp.tool()
def optimize_math_function(
    expression: str,
    initial_guess: list[float] | float = 0.0,
    minimize: bool = True,
    variable: str = "x",
) -> dict[str, Any]:
    """Performs scalar or multivariable numerical minimization or maximization via SciPy."""
    try:
        res = NumericalEngine.optimize_function(
            expression, initial_guess=initial_guess, minimize_flag=minimize, variable=variable
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("optimization", expression, res.get("optimal_value"))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "OPTIMIZATION_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 25: Numerical Quadrature Integration
# ---------------------------------------------------------------------------
@mcp.tool()
def integrate_function_numerically(
    expression: str,
    lower_bound: float,
    upper_bound: float,
    variable: str = "x",
) -> dict[str, Any]:
    """Performs numerical definite integration via SciPy adaptive quadrature."""
    try:
        res = NumericalEngine.integrate_quad(
            expression, lower_bound=lower_bound, upper_bound=upper_bound, variable=variable
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("numerical_quad", expression, res.get("integral"))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "QUAD_INTEGRATION_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 26: Solve Differential Equation
# ---------------------------------------------------------------------------
@mcp.tool()
def solve_differential_equation(
    ode_expression: str,
    initial_value: float,
    t_start: float = 0.0,
    t_end: float = 10.0,
    y_variable: str = "y",
    t_variable: str = "t",
) -> dict[str, Any]:
    """Solves ordinary differential equation dy/dt = f(t, y) symbolically or numerically."""
    try:
        res = NumericalEngine.solve_ode(
            ode_expression_str=ode_expression,
            initial_value=initial_value,
            t_span=(t_start, t_end),
            y_var=y_variable,
            t_var=t_variable,
        )
        v_tan, v_en = MathExplainer.generate_voice_summaries("ode_solve", f"dy/dt = {ode_expression}", res.get("solution") or res.get("final_state"))
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "ODE_SOLVE_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 27: Evaluate Expression & Precision
# ---------------------------------------------------------------------------
@mcp.tool()
def evaluate_math_expression(
    expression: str,
    substitutions: dict[str, Any] | None = None,
    precision: int = 6,
) -> dict[str, Any]:
    """Evaluates mathematical expression with optional variable substitution and precision formatting."""
    try:
        if substitutions:
            subbed = AlgebraEngine.substitute_expression(expression, substitutions)
            expr_str = subbed["result"]
        else:
            expr_str = expression

        parsed = MathExpressionParser.parse_to_sympy(expr_str)
        res = PrecisionManager.format_result(parsed, precision_digits=precision)
        v_tan, v_en = MathExplainer.generate_voice_summaries("evaluation", expression, res["exact"])
        res["status"] = "SUCCESS"
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except MathSecurityError as e:
        return {"status": "ERROR", "error_code": "MATH_SECURITY_REJECTED", "message": str(e)}
    except Exception as e:
        return {"status": "ERROR", "error_code": "EVALUATION_FAILED", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 28: Verify Mathematical Solution
# ---------------------------------------------------------------------------
@mcp.tool()
def verify_math_solution(
    equation: str,
    proposed_solution: str,
    variable: str = "x",
) -> dict[str, Any]:
    """Validates proposed solution against equation by calculating exact or numerical residual."""
    try:
        res = MathematicalResultValidator.verify_equation_solution(
            equation_str=equation, solution_str=proposed_solution, variable=variable
        )
        res["status"] = "SUCCESS"
        res["equation"] = equation
        res["proposed_solution"] = proposed_solution
        v_tan, v_en = MathExplainer.generate_voice_summaries("verify", equation, res["verification_status"])
        res["voice_tanglish"] = v_tan
        res["voice_en"] = v_en
        return res
    except Exception as e:
        return {"status": "ERROR", "error_code": "VERIFICATION_ERROR", "message": str(e)}