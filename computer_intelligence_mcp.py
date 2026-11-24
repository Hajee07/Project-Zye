"""
ZYE AI — Computer Intelligence MCP Server (Day 34 / Phase 3)
Big Data Intelligence, Columnar Analytics, DuckDB Engine, Mathematics,
Hybrid Search, SHA-256 Duplicate Detection & Cross-Document Entity Linking.

Exposes 66 FastMCP tools (11 Big Data + 17 Mathematics + 17 Hybrid Search Intelligence +
9 SHA-256 Deduplication + 12 Cross-Document Entity Linking).
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any
# Initialize FastMCP Server (compatible with mcp 1.x, 2.x, or fallback shim)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

from zye_computer_intelligence.data_engine.dataset_loader import DatasetLoader
from zye_computer_intelligence.data_engine.duckdb_engine import ManagedDuckDB
from zye_computer_intelligence.statistics.correlation_engine import CorrelationEngine
from zye_computer_intelligence.statistics.summary_statistics import SummaryStatistics
from zye_computer_intelligence.statistics.segment_analytics import SegmentAnalytics
from zye_computer_intelligence.statistics.trend_engine import TrendEngine
from zye_computer_intelligence.statistics.anomaly_engine import AnomalyEngine
from zye_computer_intelligence.reporting.analysis_report import AnalysisReportBuilder
from zye_computer_intelligence.reporting.result_formatter import ResultFormatter
from zye_computer_intelligence.security.resource_policy import JobManager
from zye_computer_intelligence.mathematics import (
    AlgebraEngine,
    CalculusEngine,
    EquationSolver,
    MathExplainer,
    MathExpressionParser,
    MathematicalResultValidator,
    MatrixEngine,
    NumericalEngine,
    PrecisionManager,
    MathSecurityError,
)

from zye_computer_intelligence.mathematics.expression_security import (
    ExpressionSecurityValidator,
    MathSecurityError,
)
from zye_computer_intelligence.mathematics.math_expression_parser import MathExpressionParser
from zye_computer_intelligence.mathematics.symbolic_engine import SymbolicEngine
from zye_computer_intelligence.mathematics.algebra_engine import AlgebraEngine
from zye_computer_intelligence.mathematics.equation_solver import EquationSolver
from zye_computer_intelligence.mathematics.calculus_engine import CalculusEngine
from zye_computer_intelligence.mathematics.matrix_engine import MatrixEngine
from zye_computer_intelligence.mathematics.numerical_engine import NumericalEngine
from zye_computer_intelligence.mathematics.result_validator import MathematicalResultValidator
from zye_computer_intelligence.mathematics.precision_manager import PrecisionManager
from zye_computer_intelligence.mathematics.math_explainer import MathExplainer

from zye_computer_intelligence.search.search_query_planner import SearchQueryPlanner, SearchMode
from zye_computer_intelligence.search.local_search_engine import LocalSearchEngine
from zye_computer_intelligence.search.local_index_manager import LocalIndexManager
from zye_computer_intelligence.search.local_document_extractor import LocalDocumentExtractor
from zye_computer_intelligence.search.web_search_engine import WebSearchEngine
from zye_computer_intelligence.search.web_content_extractor import WebContentExtractor
from zye_computer_intelligence.search.search_result_normalizer import SearchResultNormalizer
from zye_computer_intelligence.search.search_result_ranker import SearchResultRanker
from zye_computer_intelligence.search.evidence_validation_engine import EvidenceValidationEngine
from zye_computer_intelligence.search.citation_builder import CitationBuilder
from zye_computer_intelligence.search.hybrid_search_engine import HybridSearchEngine
from zye_computer_intelligence.search.search_cache import SearchCache
from zye_computer_intelligence.security.local_search_policy import LocalSearchPolicy
from zye_computer_intelligence.security.web_url_security import SSRFProtectionPolicy, WebSecurityError
from zye_computer_intelligence.security.untrusted_content_guard import UntrustedContentGuard

_local_search_engine = LocalSearchEngine()
_web_search_engine = WebSearchEngine()
_hybrid_search_engine = HybridSearchEngine(local_engine=_local_search_engine, web_engine=_web_search_engine)
_search_index_manager = LocalIndexManager()

from zye_computer_intelligence.deduplication import (
    SHA256DuplicateEngine,
    DuplicateReportGenerator,
    calculate_file_sha256,
    compare_files_byte_by_byte,
)
from zye_computer_intelligence.entity_linking import (
    CrossDocumentEntityLinker,
    DocumentRelationshipIndex,
    DEFAULT_DB_PATH,
)

_duplicate_engine = SHA256DuplicateEngine()
_entity_linker = CrossDocumentEntityLinker()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("zye.computer_intelligence.mcp")

mcp = FastMCP("computer_intelligence")
job_manager = JobManager()


# ---------------------------------------------------------------------------
# Tool 1: Schema Inspection
# ---------------------------------------------------------------------------
@mcp.tool()
def inspect_dataset_schema(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Inspects dataset source metadata, row counts, columns, and data types without full loading."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    return {
        "status": "SUCCESS",
        "file_name": loaded["file_name"],
        "format": loaded["format"],
        "backend": loaded["backend"],
        "size_mb": loaded["size_mb"],
        "row_count": schema.get("row_count", 0),
        "column_count": schema.get("column_count", 0),
        "columns": schema.get("columns", []),
        "numeric_columns": schema.get("numeric_columns", []),
        "categorical_columns": schema.get("categorical_columns", []),
        "date_columns": schema.get("date_columns", []),
        "identifier_columns": schema.get("identifier_columns", []),
    }

# ---------------------------------------------------------------------------
# Tool 2: Dataset Profiling
# ---------------------------------------------------------------------------
@mcp.tool()
def profile_large_dataset(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """Generates complete statistical and data-quality profile including nulls, distincts, and distributions."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    all_cols = schema.get("column_names", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)

        num_profiles = SummaryStatistics.profile_numeric_columns(engine, source_sql, num_cols)
        cat_profiles = SummaryStatistics.profile_categorical_columns(engine, source_sql, cat_cols)
        missing_info = SummaryStatistics.analyze_missing_values(engine, source_sql, all_cols)
        dup_info = SummaryStatistics.analyze_duplicate_rows(engine, source_sql)

    duration_ms = (time.perf_counter() - t0) * 1000

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        profile={
            "missing_values": missing_info,
            "duplicate_records": dup_info,
            "categorical_profiles": cat_profiles,
        },
        statistics={"numeric_distributions": num_profiles},
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )
    voice_tan, voice_en = ResultFormatter.format_voice_summaries(report)
    markdown = ResultFormatter.format_markdown_report(report)

    report["markdown"] = markdown
    report["voice_tanglish"] = voice_tan
    report["voice_en"] = voice_en
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

# ---------------------------------------------------------------------------
# Tool 3: General Large Dataset Analysis
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_large_dataset(
    file_path: str,
    operation: str = "DATASET_PROFILE",
    group_by: list[str] | None = None,
    metric: str | None = None,
    aggregation: str = "SUM",
    date_column: str | None = None,
    time_interval: str = "MONTH",
    sort_desc: bool = True,
    limit: int = 50,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Executes validated large dataset analysis according to specified operation."""
    op_upper = operation.strip().upper()
    if op_upper == "DATASET_PROFILE":
        return profile_large_dataset(file_path, sheet_name=sheet_name)
    elif op_upper in ("GROUP_AGGREGATE", "SEGMENT_COMPARISON") and group_by and metric:
        return aggregate_dataset_by_group(
            file_path=file_path,
            group_by=group_by,
            metric=metric,
            aggregation=aggregation,
            sort_desc=sort_desc,
            limit=limit,
            sheet_name=sheet_name,
        )
    elif op_upper == "TIME_TREND" and date_column and metric:
        return analyze_dataset_trends(
            file_path=file_path,
            date_column=date_column,
            metric=metric,
            aggregation=aggregation,
            interval=time_interval,
            sheet_name=sheet_name,
        )
    elif op_upper == "CORRELATION_MATRIX":
        return calculate_dataset_correlations(file_path, method="PEARSON", sheet_name=sheet_name)
    elif op_upper == "OUTLIER_SUMMARY":
        return detect_dataset_outliers(file_path, sheet_name=sheet_name)
    else:
        return profile_large_dataset(file_path, sheet_name=sheet_name)

# ---------------------------------------------------------------------------
# Tool 4: Statistical Correlations
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_dataset_correlations(
    file_path: str,
    method: str = "PEARSON",
    columns: list[str] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Calculates Pearson or Spearman correlations across numeric columns with ranking and noncausality checks."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = columns or schema.get("numeric_columns", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        corr_results = CorrelationEngine.calculate_correlation_matrix(
            duck_engine=engine,
            source_sql=source_sql,
            numeric_columns=num_cols,
            method=method,
        )

    duration_ms = (time.perf_counter() - t0) * 1000

    if corr_results["status"] != "SUCCESS":
        return corr_results

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        correlations=corr_results,
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )
    voice_tan, voice_en = ResultFormatter.format_voice_summaries(report)
    markdown = ResultFormatter.format_markdown_report(report)

    report["markdown"] = markdown
    report["voice_tanglish"] = voice_tan
    report["voice_en"] = voice_en
    return report

# ---------------------------------------------------------------------------
# Tool 5: Group Aggregation
# ---------------------------------------------------------------------------
@mcp.tool()
def aggregate_dataset_by_group(
    file_path: str,
    group_by: list[str],
    metric: str,
    aggregation: str = "SUM",
    sort_desc: bool = True,
    limit: int = 50,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Computes group-by aggregations and category percentages using DuckDB SQL."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = SegmentAnalytics.aggregate_by_group(
            duck_engine=engine,
            source_sql=source_sql,
            group_by_cols=group_by,
            metric_col=metric,
            agg=aggregation,
            sort_desc=sort_desc,
            limit=limit,
        )
    return res

# ---------------------------------------------------------------------------
# Tool 6: Time Trends
# ---------------------------------------------------------------------------
@mcp.tool()
def analyze_dataset_trends(
    file_path: str,
    date_column: str,
    metric: str,
    aggregation: str = "SUM",
    interval: str = "MONTH",
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Evaluates time-series trends, periodic growth deltas, and trajectory direction."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = TrendEngine.analyze_time_trends(
            duck_engine=engine,
            source_sql=source_sql,
            date_col=date_column,
            metric_col=metric,
            agg=aggregation,
            interval=interval,
        )
    return res

# ---------------------------------------------------------------------------
# Tool 7: Outlier Detection
# ---------------------------------------------------------------------------
@mcp.tool()
def detect_dataset_outliers(
    file_path: str,
    columns: list[str] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Identifies statistical anomalies, IQR boundaries, and negative metric values."""
    loaded = DatasetLoader.load_and_inspect(file_path, sheet_name=sheet_name)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = columns or schema.get("numeric_columns", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)
        res = AnomalyEngine.detect_outliers_and_anomalies(
            duck_engine=engine,
            source_sql=source_sql,
            numeric_cols=num_cols,
        )
    return res

# ---------------------------------------------------------------------------
# Tool 8: Segment Comparison
# ---------------------------------------------------------------------------
@mcp.tool()
def compare_dataset_segments(
    file_path: str,
    segment_column: str,
    metric: str,
    aggregation: str = "SUM",
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Compares categorical segments and calculates their contribution to overall metric."""
    return aggregate_dataset_by_group(
        file_path=file_path,
        group_by=[segment_column],
        metric=metric,
        aggregation=aggregation,
        sort_desc=True,
        limit=50,
        sheet_name=sheet_name,
    )

# ---------------------------------------------------------------------------
# Tool 9: Job Status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_dataset_analysis_status(job_id: str) -> dict[str, Any]:
    """Inspects the execution progress and state of an active analysis job."""
    job = job_manager.get_job(job_id)
    if not job:
        return {
            "status": "ERROR",
            "error_code": "JOB_NOT_FOUND",
            "message": f"Analysis job '{job_id}' does not exist.",
        }
    return {
        "status": "SUCCESS",
        "job_id": job.job_id,
        "job_status": job.status,
        "operation": job.operation,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "duration_ms": job.duration_ms,
        "error_message": job.error_message,
    }

# ---------------------------------------------------------------------------
# Tool 10: Cancel Job
# ---------------------------------------------------------------------------
@mcp.tool()
def cancel_dataset_analysis(job_id: str) -> dict[str, Any]:
    """Safely cancels an authorized running analysis job."""
    cancelled = job_manager.cancel_job(job_id)
    if not cancelled:
        return {
            "status": "ERROR",
            "error_code": "JOB_NOT_FOUND",
            "message": f"Could not cancel job '{job_id}': Job not found.",
        }
    return {
        "status": "SUCCESS",
        "job_id": job_id,
        "message": f"Analysis job '{job_id}' cancellation signal recorded.",
    }

# ---------------------------------------------------------------------------
# Tool 11: Full Report Retrieval
# ---------------------------------------------------------------------------
@mcp.tool()
def get_dataset_analysis_report(file_path: str, include_voice: bool = True) -> dict[str, Any]:
    """Retrieves complete verified analysis report for a dataset with markdown and voice scripts."""
    t0 = time.perf_counter()
    loaded = DatasetLoader.load_and_inspect(file_path)
    if loaded["status"] != "SUCCESS":
        return loaded

    schema = loaded["schema"]
    num_cols = schema.get("numeric_columns", [])
    cat_cols = schema.get("categorical_columns", [])
    all_cols = schema.get("column_names", [])

    with ManagedDuckDB() as engine:
        source_sql = schema.get("read_sql") or engine.get_csv_read_sql(file_path)

        num_profiles = SummaryStatistics.profile_numeric_columns(engine, source_sql, num_cols)
        missing_info = SummaryStatistics.analyze_missing_values(engine, source_sql, all_cols)
        dup_info = SummaryStatistics.analyze_duplicate_rows(engine, source_sql)

        corrs = None
        if len(num_cols) >= 2:
            corrs = CorrelationEngine.calculate_correlation_matrix(
                engine, source_sql, num_cols, method="PEARSON"
            )

        outliers = None
        if num_cols:
            outliers = AnomalyEngine.detect_outliers_and_anomalies(engine, source_sql, num_cols)

    duration_ms = (time.perf_counter() - t0) * 1000

    report = AnalysisReportBuilder.build_report(
        dataset_meta=loaded,
        backend=loaded["backend"],
        profile={"missing_values": missing_info, "duplicate_records": dup_info},
        statistics={"numeric_distributions": num_profiles},
        correlations=corrs if corrs and corrs.get("status") == "SUCCESS" else None,
        outliers=outliers,
        duration_ms=duration_ms,
        rows_scanned=schema.get("row_count", 0),
    )

    markdown = ResultFormatter.format_markdown_report(report)
    report["markdown"] = markdown

    if include_voice:
        v_tan, v_en = ResultFormatter.format_voice_summaries(report)
        report["voice_tanglish"] = v_tan
        report["voice_en"] = v_en

    return report

# ---------------------------------------------------------------------------
# Tool 29: Search Local Sources
# ---------------------------------------------------------------------------
@mcp.tool()
def search_local_sources(
    query: str,
    root_path: str | None = None,
    file_types: list[str] | None = None,
    max_results: int = 10,
    exact_phrase: bool = False,
) -> dict[str, Any]:
    """Searches authorized local computer sources, files, codebases, and documents."""
    try:
        return _local_search_engine.search_local_sources(
            query=query,
            root_path=root_path,
            file_types=file_types,
            max_results=max_results,
            exact_phrase=exact_phrase,
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "LOCAL_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 30: Search Local Documents
# ---------------------------------------------------------------------------
@mcp.tool()
def search_local_documents(
    query: str,
    root_path: str | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Searches specifically across document formats (PDF, DOCX, TXT, Markdown)."""
    try:
        return _local_search_engine.search_local_documents(
            query=query, root_path=root_path, max_results=max_results
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "LOCAL_DOCUMENT_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 31: Search Local Code
# ---------------------------------------------------------------------------
@mcp.tool()
def search_local_code(
    query: str,
    root_path: str | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Searches codebase files (Python, JS, TS, HTML, SQL) with line and symbol matches."""
    try:
        return _local_search_engine.search_local_code(
            query=query, root_path=root_path, max_results=max_results
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "LOCAL_CODE_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 32: Search Local Datasets
# ---------------------------------------------------------------------------
@mcp.tool()
def search_local_datasets(
    query: str,
    root_path: str | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Searches tabular and columnar data files (CSV, Excel, DuckDB, Parquet)."""
    try:
        return _local_search_engine.search_local_datasets(
            query=query, root_path=root_path, max_results=max_results
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "LOCAL_DATASET_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 33: Search Web Sources
# ---------------------------------------------------------------------------
@mcp.tool()
def search_web_sources(
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Performs live internet search across authorized web providers."""
    try:
        return _web_search_engine.search_web(query=query, max_results=max_results)
    except Exception as e:
        return {"status": "ERROR", "error_code": "WEB_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 34: Search Web Domain
# ---------------------------------------------------------------------------
@mcp.tool()
def search_web_domain(
    query: str,
    domain: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Performs domain-restricted web search (e.g. site:docs.python.org)."""
    try:
        return _web_search_engine.search_web_by_domain(
            query=query, domain=domain, max_results=max_results
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "DOMAIN_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 35: Fetch Web Page
# ---------------------------------------------------------------------------
@mcp.tool()
def fetch_web_page(
    url: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Safely fetches a web page, verifies SSRF safety, and extracts clean text."""
    try:
        return WebContentExtractor.fetch_and_extract(url=url, timeout=timeout)
    except Exception as e:
        return {"status": "ERROR", "error_code": "WEB_FETCH_ERROR", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 36: Extract Web Content
# ---------------------------------------------------------------------------
@mcp.tool()
def extract_web_content(
    html_content: str,
    source_url: str = "",
) -> dict[str, Any]:
    """Parses HTML DOM, strips scripts/ads/cookie banners, and extracts structured text."""
    try:
        return WebContentExtractor.extract_from_html(html_content, source_url=source_url)
    except Exception as e:
        return {"status": "ERROR", "error_code": "HTML_EXTRACTION_ERROR", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 37: Execute Hybrid Search
# ---------------------------------------------------------------------------
@mcp.tool()
def execute_hybrid_search(
    query: str,
    search_mode: str = "auto",
    max_results: int = 10,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Orchestrates hybrid local and web search with multi-factor ranking and citations."""
    try:
        return _hybrid_search_engine.execute_hybrid_search(
            query=query,
            search_mode=search_mode,
            max_results=max_results,
            force_refresh=force_refresh,
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "HYBRID_SEARCH_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 38: Compare Local & Web Sources
# ---------------------------------------------------------------------------
@mcp.tool()
def compare_local_web_sources(
    local_query: str,
    web_query: str,
    domain_filter: str | None = None,
) -> dict[str, Any]:
    """Compares local project files against live online documentation to spot version gaps."""
    try:
        return _hybrid_search_engine.compare_local_web_sources(
            local_query=local_query,
            web_query=web_query,
            domain_filter=domain_filter,
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "COMPARISON_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 39: Verify Search Evidence
# ---------------------------------------------------------------------------
@mcp.tool()
def verify_search_evidence(
    claims: list[str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    """Corroborates claims across search results, reporting confidence and contradictions."""
    try:
        hres = _hybrid_search_engine.execute_hybrid_search(query=query or (claims[0] if claims else "evidence"))
        return hres.get("evidence_validation", {})
    except Exception as e:
        return {"status": "ERROR", "error_code": "EVIDENCE_VALIDATION_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 40: Get Search Citations
# ---------------------------------------------------------------------------
@mcp.tool()
def get_search_citations(
    query: str,
    search_mode: str = "auto",
) -> dict[str, Any]:
    """Retrieves structured citations and voice summaries for a given search query."""
    try:
        hres = _hybrid_search_engine.execute_hybrid_search(query=query, search_mode=search_mode)
        citations = hres.get("citations", [])
        md = CitationBuilder.format_markdown_citations(citations)
        v_tan, v_en = CitationBuilder.format_voice_citations(citations)
        return {
            "status": "SUCCESS",
            "query": query,
            "citations_count": len(citations),
            "citations": citations,
            "markdown": md,
            "voice_tanglish": v_tan,
            "voice_en": v_en,
        }
    except Exception as e:
        return {"status": "ERROR", "error_code": "CITATIONS_EXTRACTION_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 41: Get Local Index Status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_local_index_status() -> dict[str, Any]:
    """Returns status, document counts, and storage metrics for the SQLite FTS5 index."""
    try:
        return _search_index_manager.get_index_status()
    except Exception as e:
        return {"status": "ERROR", "error_code": "INDEX_STATUS_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 42: Rebuild Local Search Index
# ---------------------------------------------------------------------------
@mcp.tool()
def rebuild_local_search_index(
    root_dir: str | None = None,
) -> dict[str, Any]:
    """Walks authorized directories and incrementally rebuilds the full-text search index."""
    try:
        target = Path(root_dir) if root_dir else None
        return _search_index_manager.rebuild_index(root_dir=target)
    except Exception as e:
        return {"status": "ERROR", "error_code": "REBUILD_INDEX_FAILED", "message": str(e)}

# ---------------------------------------------------------------------------
# Tool 43: Get Search Job Status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_search_job_status(job_id: str) -> dict[str, Any]:
    """Queries the status of an asynchronous background search task."""
    job = job_manager.get_job(job_id)
    if not job:
        return {"status": "ERROR", "error_code": "JOB_NOT_FOUND", "message": f"Search job '{job_id}' not found."}
    return {
        "status": "SUCCESS",
        "job_id": job.job_id,
        "job_status": job.status,
        "job_type": job.job_type,
        "target_file": job.target_file,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
    }

# ---------------------------------------------------------------------------
# Tool 44: Cancel Search Job
# ---------------------------------------------------------------------------
@mcp.tool()
def cancel_search_job(job_id: str) -> dict[str, Any]:
    """Safely cancels an active background search job."""
    success = job_manager.cancel_job(job_id)
    if not success:
        return {"status": "ERROR", "error_code": "JOB_NOT_FOUND_OR_FINAL", "message": f"Job '{job_id}' cannot be cancelled."}
    return {"status": "SUCCESS", "job_id": job_id, "action": "CANCELLED"}

# ---------------------------------------------------------------------------
# Tool 45: Refresh Search Results
# ---------------------------------------------------------------------------
@mcp.tool()
def refresh_search_results(
    query: str,
    search_mode: str = "auto",
) -> dict[str, Any]:
    """Bypasses cache and executes a fresh live search query."""
    try:
        return _hybrid_search_engine.execute_hybrid_search(
            query=query, search_mode=search_mode, force_refresh=True
        )
    except Exception as e:
        return {"status": "ERROR", "error_code": "REFRESH_SEARCH_FAILED", "message": str(e)}


# ===========================================================================
# DAY 34 CAPABILITY 01: SHA-256 DUPLICATE DETECTION TOOLS (Tools 46 - 54)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 46: Scan Duplicate Files
# ---------------------------------------------------------------------------
@mcp.tool()
def scan_duplicate_files(
    directories: list[str],
    recursive: bool = True,
    min_size_bytes: int = 1,
    max_size_bytes: int = 500 * 1024 * 1024,
    verify_bytes: bool = True,
) -> dict[str, Any]:
    """
    Executes a multi-stage SHA-256 duplicate file detection scan across authorized directories.
    Multi-stage pipeline: size pruning -> streaming 1MB SHA-256 -> byte verification.
    STRICTLY READ-ONLY: Never deletes or modifies any files.
    """
    try:
        res = _duplicate_engine.scan_directories_sync(
            directories=directories,
            recursive=recursive,
            min_file_size_bytes=min_size_bytes,
            max_file_size_bytes=max_size_bytes,
            verify_bytes=verify_bytes,
        )
        return {"status": "SUCCESS", "result": res.model_dump()}
    except Exception as exc:
        logger.error("scan_duplicate_files failed: %s", exc)
        return {"status": "ERROR", "error_code": "SCAN_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 47: Compare Two Files
# ---------------------------------------------------------------------------
@mcp.tool()
def compare_two_files(
    path_a: str,
    path_b: str,
    verify_bytes: bool = True,
) -> dict[str, Any]:
    """
    Compares two files using streaming SHA-256 hash and byte-for-byte comparison.
    Returns whether the files are exact duplicates with zero collision risk.
    """
    try:
        res = _duplicate_engine.compare_two_files(path_a, path_b, verify_bytes=verify_bytes)
        return {"status": "SUCCESS", "comparison": res}
    except Exception as exc:
        return {"status": "ERROR", "error_code": "COMPARE_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 48: Get Duplicate Scan Report
# ---------------------------------------------------------------------------
@mcp.tool()
def get_duplicate_scan_report(
    directories: list[str],
    format: str = "markdown",
) -> dict[str, Any]:
    """
    Runs duplicate detection and formats the results into an audit report (Markdown or JSON).
    Highlights potential reclaimable bytes and lists all duplicate groups.
    """
    try:
        res = _duplicate_engine.scan_directories_sync(directories=directories)
        report_text = _duplicate_engine.generate_report(res, format=format)
        return {
            "status": "SUCCESS",
            "format": format,
            "report": report_text,
            "duplicate_groups_count": res.duplicate_groups_count,
            "potential_reclaimable_bytes": res.potential_reclaimable_bytes,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "REPORT_GEN_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 49: Calculate Storage Reclamation
# ---------------------------------------------------------------------------
@mcp.tool()
def calculate_storage_reclamation(directories: list[str]) -> dict[str, Any]:
    """
    Calculates estimated reclaimable storage without double-counting hard links.
    Returns human-readable and raw byte totals.
    """
    try:
        res = _duplicate_engine.scan_directories_sync(directories=directories)
        from zye_computer_intelligence.deduplication.storage_calculator import format_bytes_human
        return {
            "status": "SUCCESS",
            "total_files_scanned": res.total_files_scanned,
            "total_bytes_scanned": res.total_bytes_scanned,
            "duplicate_groups_count": res.duplicate_groups_count,
            "duplicate_files_count": res.duplicate_files_count,
            "potential_reclaimable_bytes": res.potential_reclaimable_bytes,
            "potential_reclaimable_human": format_bytes_human(res.potential_reclaimable_bytes),
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "RECLAMATION_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 50: Find Largest Duplicate Groups
# ---------------------------------------------------------------------------
@mcp.tool()
def find_largest_duplicate_groups(
    directories: list[str],
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Finds top duplicate file groups sorted by potential reclaimable storage descending.
    """
    try:
        res = _duplicate_engine.scan_directories_sync(directories=directories)
        sorted_groups = sorted(res.groups, key=lambda g: g.potential_reclaimable_bytes, reverse=True)[:top_n]
        return {
            "status": "SUCCESS",
            "top_n": top_n,
            "groups": [g.model_dump() for g in sorted_groups],
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "LARGEST_GROUPS_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 51: Check File Hard Links
# ---------------------------------------------------------------------------
@mcp.tool()
def check_file_hard_links(directories: list[str]) -> dict[str, Any]:
    """
    Scans directories to detect files that share identical NTFS/POSIX inodes (hard links).
    Hard links share physical storage and thus have zero reclaimable bytes.
    """
    try:
        res = _duplicate_engine.scan_directories_sync(directories=directories)
        hard_link_groups = [g.model_dump() for g in res.groups if g.duplicate_type == "HARD_LINK_COPIES"]
        return {
            "status": "SUCCESS",
            "hard_link_groups_count": len(hard_link_groups),
            "groups": hard_link_groups,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "HARD_LINK_CHECK_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 52: Filter Duplicates By Extension
# ---------------------------------------------------------------------------
@mcp.tool()
def filter_duplicates_by_extension(
    directories: list[str],
    extension: str,
) -> dict[str, Any]:
    """
    Scans for duplicate files restricted to a specific file extension (e.g. '.pdf', '.docx', '.csv').
    """
    try:
        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        res = _duplicate_engine.scan_directories_sync(
            directories=directories,
            include_extensions=[ext],
        )
        return {
            "status": "SUCCESS",
            "extension": ext,
            "duplicate_groups_count": res.duplicate_groups_count,
            "potential_reclaimable_bytes": res.potential_reclaimable_bytes,
            "groups": [g.model_dump() for g in res.groups],
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "FILTER_BY_EXT_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 53: Verify Duplicate Integrity
# ---------------------------------------------------------------------------
@mcp.tool()
def verify_duplicate_integrity(path_a: str, path_b: str) -> dict[str, Any]:
    """
    Verifies cryptographic hash and binary byte parity of two files to confirm exact match.
    """
    try:
        res = _duplicate_engine.compare_two_files(path_a, path_b, verify_bytes=True)
        return {
            "status": "SUCCESS",
            "verified": res.get("match", False),
            "details": res,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "INTEGRITY_CHECK_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 54: Get Deduplication Status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_deduplication_status() -> dict[str, Any]:
    """
    Returns engine configuration, safety policies, chunk buffer sizes, and limits.
    """
    from zye_computer_intelligence.security.processing_resource_policy import ProcessingResourcePolicy
    return {
        "status": "SUCCESS",
        "engine": "SHA256DuplicateEngine",
        "read_only": True,
        "chunk_size_bytes": 1024 * 1024,
        "max_files_cap": ProcessingResourcePolicy.MAX_TOTAL_FILES_TO_SCAN,
        "max_scan_bytes_cap": ProcessingResourcePolicy.MAX_TOTAL_SCAN_BYTES,
        "supported_operations": [
            "streaming_sha256",
            "byte_for_byte_verification",
            "hard_link_resolution",
            "storage_reclamation_estimation",
            "markdown_and_json_reports",
        ],
    }


# ===========================================================================
# DAY 34 CAPABILITY 02: CROSS-DOCUMENT ENTITY LINKING TOOLS (Tools 55 - 66)
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 55: Index Document Entities
# ---------------------------------------------------------------------------
@mcp.tool()
def index_document_entities(file_path: str) -> dict[str, Any]:
    """
    Extracts entities across 9 categories from a document and updates the entity graph.
    Extracts provenance: page, sheet, line, section, and surrounding snippet.
    """
    try:
        res = _entity_linker.index_documents_sync([file_path])
        return {
            "status": "SUCCESS",
            "document": file_path,
            "total_mentions": res.total_mentions_found,
            "unique_entities": res.unique_entities_count,
            "resolved_entities": res.resolved_entities_count,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "INDEX_DOC_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 56: Index Directory Entities
# ---------------------------------------------------------------------------
@mcp.tool()
def index_directory_entities(
    dir_path: str,
    recursive: bool = True,
) -> dict[str, Any]:
    """
    Scans and indexes all supported documents in a directory into the entity knowledge graph.
    """
    try:
        res = _entity_linker.index_directory_sync(dir_path, recursive=recursive)
        return {
            "status": "SUCCESS",
            "directory": dir_path,
            "documents_processed": res.total_documents_processed,
            "mentions_found": res.total_mentions_found,
            "unique_entities": res.unique_entities_count,
            "relationships_created": res.relationships_count,
            "duration_ms": res.duration_ms,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "INDEX_DIR_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 57: Search Entities
# ---------------------------------------------------------------------------
@mcp.tool()
def search_entities(
    query: str,
    entity_types: list[str] | None = None,
    min_confidence: float = 0.0,
) -> dict[str, Any]:
    """
    Searches canonical entities and aliases in the knowledge graph.
    Supports filtering by taxonomy types (e.g. PERSON, ORGANIZATION, PROJECT).
    """
    try:
        results = _entity_linker.search_entities(
            query=query,
            entity_types=entity_types,
            min_confidence=min_confidence,
        )
        return {"status": "SUCCESS", "query": query, "count": len(results), "entities": results}
    except Exception as exc:
        return {"status": "ERROR", "error_code": "SEARCH_ENTITIES_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 58: Get Entity Profile
# ---------------------------------------------------------------------------
@mcp.tool()
def get_entity_profile(entity_id_or_name: str) -> dict[str, Any]:
    """
    Retrieves full profile for an entity including all source document mentions,
    evidence citations (page numbers, sheet names, line numbers), and connected graph relations.
    """
    try:
        profile = _entity_linker.get_entity_profile(entity_id_or_name)
        if not profile:
            return {"status": "NOT_FOUND", "message": f"Entity '{entity_id_or_name}' not found."}
        return {"status": "SUCCESS", "profile": profile}
    except Exception as exc:
        return {"status": "ERROR", "error_code": "GET_PROFILE_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 59: Find Cross-Document Connections
# ---------------------------------------------------------------------------
@mcp.tool()
def find_cross_document_connections(
    document_a: str,
    document_b: str,
) -> dict[str, Any]:
    """
    Identifies all entities shared between two documents to reveal latent cross-document links.
    """
    try:
        connections = _entity_linker.find_cross_document_connections(document_a, document_b)
        return {
            "status": "SUCCESS",
            "document_a": document_a,
            "document_b": document_b,
            "shared_entities_count": len(connections),
            "shared_entities": connections,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "CROSS_CONNECTIONS_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 60: Get Document Entities
# ---------------------------------------------------------------------------
@mcp.tool()
def get_document_entities(document_id: str) -> dict[str, Any]:
    """
    Returns all entities discovered within a specific document.
    """
    try:
        ents = _entity_linker.get_document_entities(document_id)
        return {"status": "SUCCESS", "document_id": document_id, "entities": ents}
    except Exception as exc:
        return {"status": "ERROR", "error_code": "GET_DOC_ENTITIES_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 61: Find Entity Relationships
# ---------------------------------------------------------------------------
@mcp.tool()
def find_entity_relationships(entity_id: str) -> dict[str, Any]:
    """
    Retrieves all incoming and outgoing semantic relationships for an entity.
    """
    try:
        prof = _entity_linker.get_entity_profile(entity_id)
        if not prof:
            return {"status": "NOT_FOUND", "message": f"Entity '{entity_id}' not found."}
        return {
            "status": "SUCCESS",
            "entity_id": entity_id,
            "relationships": prof.get("connected_relationships", []),
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "GET_RELATIONSHIPS_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 62: Get Entity Graph Statistics
# ---------------------------------------------------------------------------
@mcp.tool()
def get_entity_graph_statistics() -> dict[str, Any]:
    """
    Returns global metrics: total documents, entities by type, mentions, and relationships.
    """
    try:
        stats = _entity_linker.get_graph_statistics()
        return {"status": "SUCCESS", "statistics": stats}
    except Exception as exc:
        return {"status": "ERROR", "error_code": "GRAPH_STATS_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 63: Find Shared Projects and Technologies
# ---------------------------------------------------------------------------
@mcp.tool()
def find_shared_projects_and_technologies(
    doc_a: str,
    doc_b: str,
) -> dict[str, Any]:
    """
    Discovers projects and technical frameworks/tools shared across two documents.
    """
    try:
        conns = _entity_linker.find_cross_document_connections(doc_a, doc_b)
        relevant = [
            c for c in conns
            if c.get("entity_type") in ("PROJECT", "TECHNICAL_ENTITY", "PRODUCT")
        ]
        return {
            "status": "SUCCESS",
            "doc_a": doc_a,
            "doc_b": doc_b,
            "shared_count": len(relevant),
            "shared_items": relevant,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "SHARED_PROJ_TECH_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 64: Find Organizations and Members
# ---------------------------------------------------------------------------
@mcp.tool()
def find_organizations_and_members(organization_name: str) -> dict[str, Any]:
    """
    Discovers persons associated with a given organization based on co-occurrence and document context.
    """
    try:
        prof = _entity_linker.get_entity_profile(organization_name)
        if not prof:
            return {"status": "NOT_FOUND", "message": f"Organization '{organization_name}' not found."}

        associated_members = []
        for rel in prof.get("connected_relationships", []):
            if rel.get("relationship_type") == "PERSON_ASSOCIATED_WITH_ORGANIZATION":
                associated_members.append({
                    "person": rel.get("target_name"),
                    "evidence": rel.get("evidence"),
                    "source_document": rel.get("source_document_id"),
                })

        return {
            "status": "SUCCESS",
            "organization": organization_name,
            "associated_members_count": len(associated_members),
            "members": associated_members,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "FIND_ORG_MEMBERS_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 65: Check Entity Ambiguity
# ---------------------------------------------------------------------------
@mcp.tool()
def check_entity_ambiguity() -> dict[str, Any]:
    """
    Returns all entity resolution candidates marked as AMBIGUOUS requiring human or contextual verification.
    Guarantees no false merges of common first names or conflicting aliases.
    """
    try:
        with _entity_linker.query_engine.index._get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT c.*, ea.canonical_name as name_a, eb.canonical_name as name_b
                FROM entity_match_candidates c
                JOIN entities ea ON c.entity_a_id = ea.entity_id
                JOIN entities eb ON c.entity_b_id = eb.entity_id
                WHERE c.status = 'AMBIGUOUS'
                """
            ).fetchall()
            ambiguous_list = [dict(r) for r in rows]

        return {
            "status": "SUCCESS",
            "ambiguous_candidates_count": len(ambiguous_list),
            "candidates": ambiguous_list,
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "AMBIGUITY_CHECK_FAILED", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 66: Export Entity Graph
# ---------------------------------------------------------------------------
@mcp.tool()
def export_entity_graph(format: str = "json") -> dict[str, Any]:
    """
    Exports full graph statistics, top entities, and recent relationships.
    """
    try:
        stats = _entity_linker.get_graph_statistics()
        top_entities = _entity_linker.search_entities(query="", min_confidence=0.0)
        return {
            "status": "SUCCESS",
            "format": format,
            "statistics": stats,
            "entities_sample": top_entities[:50],
        }
    except Exception as exc:
        return {"status": "ERROR", "error_code": "EXPORT_GRAPH_FAILED", "message": str(exc)}


# ============================================================================
# Main Entry Point (FastMCP / MCPServer stdio runner)
# ============================================================================

def main() -> int:
    """Run FastMCP / MCPServer stdio transport if invoked directly."""
    try:
        mcp.run(transport="stdio")
        return 0
    except Exception as exc:
        import sys
        sys.stderr.write(f"ZyeComputerIntelligence server error: {exc}\n")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())


