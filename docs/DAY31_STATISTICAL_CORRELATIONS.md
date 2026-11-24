# ZYE AI — DAY 31 STATISTICAL CORRELATION ENGINE SPECIFICATION

## 1. Mathematical Foundation

The Correlation Engine (`zye_computer_intelligence/statistics/correlation_engine.py`) provides two foundational measures of statistical association:

### A. Pearson Product-Moment Correlation ($r$)
Measures the linear relationship between two continuous variables $X$ and $Y$:
$$r = \frac{\sum_{i=1}^n (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^n (x_i - \bar{x})^2} \sqrt{\sum_{i=1}^n (y_i - \bar{y})^2}}$$
Computed directly in DuckDB using the native `corr(a, b)` aggregate function.

### B. Spearman Rank-Order Correlation ($\rho$)
Measures monotonic relationships between two ranked variables:
$$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$
Computed in DuckDB by ranking pairwise non-null observations with window functions (`RANK() OVER (ORDER BY a)`), then calculating Pearson correlation over the ranks.

---

## 2. Classification & Interpretation Thresholds

| Coefficient Range | Classification | Descriptive Interpretation |
|---|---|---|
| $r \ge 0.70$ | `STRONG_POSITIVE` | Strong positive linear/monotonic association |
| $0.40 \le r < 0.70$ | `MODERATE_POSITIVE` | Moderate positive association |
| $0.15 \le r < 0.40$ | `WEAK_POSITIVE` | Weak positive association |
| $-0.15 < r < 0.15$ | `NEAR_ZERO` | No observable linear association |
| $-0.40 < r \le -0.15$ | `WEAK_NEGATIVE` | Weak negative association |
| $-0.70 < r \le -0.40$ | `MODERATE_NEGATIVE` | Moderate negative association |
| $r \le -0.70$ | `STRONG_NEGATIVE` | Strong inverse linear/monotonic association |

---

## 3. Noncausality Guardrail Policy

Every correlation output returned by ZYE AI includes an explicit epistemic warning:
> *"Statistical correlation does not imply causation. These coefficients describe observed linear or monotonic association within the dataset, not underlying causal mechanisms. Confounding variables and data collection artifacts may influence observed relationships."*

Voice outputs generated for Gemini Live synthesize this policy naturally:
> *"Mukkiyamaana correlation: ad_spend matrum revenue naduvula strong positive association irukku (r=0.9995). Idhu linear relationship mattum dhaan, causation kidayaadhu."*
