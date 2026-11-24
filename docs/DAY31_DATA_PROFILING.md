# ZYE AI — DAY 31 DATASET PROFILING & QUALITY SPECIFICATION

## 1. Overview
The Dataset Profiling Engine (`zye_computer_intelligence/statistics/summary_statistics.py`) computes statistical summaries and data-quality diagnostics across tabular datasets of arbitrary size.

---

## 2. Profiling Dimensions

### A. Numeric Distribution Profiling
For every eligible numeric column, the engine computes:
- **Count & Null Count**: Total populated observations and missing records.
- **Central Tendency**: Arithmetic Mean and Median ($50^{\text{th}}$ percentile).
- **Dispersion**: Sample Standard Deviation ($\sigma$) and Variance ($s^2$).
- **Extremes**: Minimum and Maximum values.
- **Quartiles**: First Quartile ($Q_1$, $25^{\text{th}}$ percentile) and Third Quartile ($Q_3$, $75^{\text{th}}$ percentile).
- **Interquartile Range**: $IQR = Q_3 - Q_1$.

### B. Data Quality & Missing-Value Distinction
The profiler rigorously differentiates between distinct categories of missing data:
1. **`NULL` (SQL NULL / NaN)**: Unallocated or unrecorded fields.
2. **Empty String (`""`)**: Text fields with zero character length.
3. **Whitespace String (`"   "`)**: Strings containing only space or tab characters.

### C. Duplicate-Row Analytics
- **Exact Row Duplicates**: Identifies identical records where all columns match across multiple rows.
- **Key-Column Duplicates**: Detects duplicate business transaction IDs, customer IDs, or composite keys.
