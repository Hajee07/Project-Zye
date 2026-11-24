# ZYE AI — DAY 32 SECURITY & AST SANDBOX SPECIFICATION
## Zero Code Execution & Mathematical AST Isolation

### 1. Threat Model & Attack Vectors
In an autonomous voice assistant that evaluates expressions provided by users or external tools, dynamic evaluation functions such as `eval()`, `exec()`, or unguarded `sympy.sympify()` present severe vulnerabilities:
1. **Remote Code Execution**: `__import__('os').system('cmd')`
2. **Filesystem Intrusion**: `open('C:/Windows/win.ini').read()`
3. **Reflection & Sandbox Escape**: `(1).__class__.__bases__[0].__subclasses__()`
4. **Denial of Service (CPU Exhaustion)**: `2**9999999999`
5. **Stack Overflow / Recursion DoS**: Nested expressions `sin(sin(sin(...)))` > 1000 levels.

### 2. Defense-in-Depth Mechanisms
The ZYE Mathematical Sandbox (`ExpressionSecurityValidator`) enforces 4 strict defensive layers:

#### Layer 1: Pre-Parse Keyword Screening
Scans raw input strings for prohibited keywords and dunder methods:
- `__\w+__` (Dunder methods)
- `import`, `lambda`, `open`, `exec`, `eval`, `system`, `subprocess`, `globals`, `locals`, `exit`, `quit`, `breakpoint`

#### Layer 2: Syntactic Limits
- Maximum length: **1,000 characters**.
- Preprocessing normalization: Transforms `^` $\to$ `**` and `2x` $\to$ `2*x` without altering semantics.

#### Layer 3: AST Whitelisting
Constructs a Python Abstract Syntax Tree via `ast.parse(normalized, mode='eval')` and validates every node against an immutable whitelist:
- **Allowed AST Nodes**: `Expression`, `BinOp`, `UnaryOp`, `Call`, `Name`, `Constant`, `Compare`, `Tuple`, `List`, `Load`, operators (`Add`, `Sub`, `Mult`, `Div`, `FloorDiv`, `Mod`, `Pow`, `UAdd`, `USub`), and comparisons (`Eq`, `NotEq`, `Lt`, `LtE`, `Gt`, `GtE`).
- **Prohibited AST Nodes**: `Attribute`, `Import`, `ImportFrom`, `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, `Delete`, `Assign`, `AugAssign`, `For`, `While`, `If`, `With`, `Raise`, `Try`, `Assert`, etc.

#### Layer 4: Mathematical Whitelist & Magnitude Clamping
- **Allowed Function Names**: `sin`, `cos`, `tan`, `sec`, `csc`, `cot`, `asin`, `acos`, `atan`, `asec`, `acsc`, `acot`, `sinh`, `cosh`, `tanh`, `sech`, `csch`, `coth`, `asinh`, `acosh`, `atanh`, `exp`, `log`, `ln`, `sqrt`, `cbrt`, `Abs`, `abs`, `factorial`, `floor`, `ceiling`, `ceil`, `gamma`, `sign`, `min`, `max`.
- **Allowed Constants**: `pi`, `E`, `e`, `I`, `i`, `oo`, `inf`, `zoo`, `nan`.
- **Maximum Exponent Value**: Powers exceeding $|b| > 100.0$ in $a^b$ are rejected immediately to eliminate algorithmic complexity bombs.
- **Maximum AST Depth**: Trees exceeding a depth of **25** levels trigger `MathSecurityError`.
