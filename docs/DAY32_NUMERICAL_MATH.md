# ZYE AI — DAY 32 NUMERICAL MATHEMATICS REFERENCE
## SciPy Engine, Root Finding, Optimization, Quadrature & Differential Equations

### 1. Scalar & Multivariable Root Finding
- **Engine**: `scipy.optimize.root_scalar` & `scipy.optimize.root`
- **Algorithm Selection**:
  - When brackets $[a, b]$ with $f(a)f(b) < 0$ are supplied: `brentq` (Brent's method) or `ridder` with superlinear convergence.
  - When single initial guess is provided: Newton-Raphson or secant method.
- **Residual Guarantee**: Every root output verifies $|f(x^*)| < 10^{-6}$.

### 2. Numerical Optimization
- **Engine**: `scipy.optimize.minimize` & `scipy.optimize.minimize_scalar`
- **Capabilities**:
  - Scalar minimization / maximization over unconstrained or bounded intervals.
  - Multivariable optimization over $\mathbb{R}^n$ with optional box bounds.
  - Vector wrapping ensuring seamless conversion from NumPy arrays to scalar objectives.

### 3. Adaptive Quadrature Integration
- **Engine**: `scipy.integrate.quad`
- **Technique**: Fortran-level QUADPACK adaptive Gauss-Kronrod quadrature.
- **Output**: Returns numerical integral value accompanied by absolute error estimate ($\text{err} < 10^{-8}$).

### 4. Ordinary Differential Equations (ODE)
- **Engine**: `sympy.dsolve` with fallback to `scipy.integrate.solve_ivp`
- **Execution Flow**:
  1. Primary attempt: Exact analytical symbolic integration via SymPy `dsolve` with initial conditions $y(t_0) = y_0$.
  2. Fallback attempt: Explicit Runge-Kutta 4th/5th order (`RK45`) adaptive step-size numerical IVP integration.
