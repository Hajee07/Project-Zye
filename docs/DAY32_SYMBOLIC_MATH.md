# ZYE AI — DAY 32 SYMBOLIC MATHEMATICS REFERENCE
## SymPy Engine, Symbolic Algebra, Equations, Calculus & Linear Algebra

### 1. Symbolic Algebra Engine (`AlgebraEngine`)
- **Simplification (`simplify_expression`)**:
  Canonical transformation of polynomial, rational, logarithmic, exponential, and trigonometric expressions.
  Example: `sin(x)**2 + cos(x)**2` $\to 1$; `(x**2 - 1)/(x - 1)` $\to x + 1$.
- **Expansion (`expand_expression`)**:
  Full polynomial and trigonometric expansion.
  Example: `(x + 2)**2` $\to x^2 + 4x + 4$.
- **Factoring (`factor_expression`)**:
  Irreducible polynomial factorization over $\mathbb{Q}$ or requested domains.
  Example: `x**2 - 9` $\to (x - 3)(x + 3)$.
- **Term Collection (`collect_terms`)**:
  Collects coefficients with respect to target symbols.
- **Substitution (`substitute_expression`)**:
  Performs symbolic or numerical replacement of variables.

### 2. Domain-Aware Equation Solving (`EquationSolver`)
- **Single-Variable Equations (`solve_single_variable`)**:
  Employs `sympy.solveset` with automatic domain filtering (`REAL`, `COMPLEX`, `INTEGER`, `POSITIVE`). Falls back gracefully to `sympy.solve` when required.
- **Linear Systems (`solve_system` -> `linsolve`)**:
  Exact algebraic solutions for simultaneous linear systems $A\mathbf{x} = \mathbf{b}$.
- **Nonlinear Systems (`solve_system` -> `nonlinsolve`)**:
  Exact algebraic solutions for intersections of non-linear equations (e.g., circles, hyperplanes).
- **Inequalities (`solve_inequality`)**:
  Solves univariate inequalities, returning formal interval notation (e.g. `Interval.open(2, oo)`).

### 3. Calculus Engine (`CalculusEngine`)
- **Derivatives (`differentiate`)**:
  Supports arbitrary order $N$ differentiation ($d^n f / dx^n$) with symbolic chain, product, and quotient rules.
- **Gradients (`calculate_gradient`)**:
  Computes gradient vectors $[\partial f/\partial x_1, \dots, \partial f/\partial x_n]^T$ for multivariable scalar fields.
- **Integrals (`integrate`)**:
  - Indefinite: Returns anti-derivative with explicit $+ C$ integration constant.
  - Definite: Evaluates definite integrals over $[a, b]$, returning both exact symbolic rational and floating-point approximations.
- **Limits (`calculate_limit`)**:
  Computes two-sided limits, directional limits (left `-`, right `+`), and limits as $x \to \pm\infty$.
- **Taylor Series (`calculate_taylor_series`)**:
  Generates Taylor/Maclaurin polynomial expansions around point $x_0$ truncated at order $N$.

### 4. Matrix Algebra Engine (`MatrixEngine`)
- **Properties (`calculate_matrix_properties`)**:
  Determinants, rank, trace, invertibility detection, exact matrix inverse, eigenvalues, and algebraic multiplicities.
- **System Solving (`solve_matrix_system`)**:
  Exact symbolic LU solve for square, non-singular systems; automatic fallback to numerical least-squares for overdetermined or rectangular matrices.
- **SVD (`calculate_svd`)**:
  Singular Value Decomposition via SciPy linear algebra kernel.
