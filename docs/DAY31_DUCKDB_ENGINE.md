# ZYE AI — DAY 31 DUCKDB ENGINE SPECIFICATION

## 1. Engine Design & Rationale
DuckDB v2.0.1 serves as the primary analytical query engine for large-scale columnar data processing in ZYE AI Phase 3. Unlike traditional relational database servers (PostgreSQL, MySQL), DuckDB operates embedded in-process, directly scanning CSV, Parquet, and in-memory tables without network overhead or client-server serialization.

---

## 2. Resource Governance & Host Protection

To prevent analytical queries from exhausting RAM or freezing the user's Windows laptop, every `ManagedDuckDB` session applies deterministic resource limits immediately upon connection:

```python
con = duckdb.connect(database=":memory:")
con.execute(f"SET memory_limit = '{policy.max_memory_mb}MB';")
con.execute(f"SET threads = {policy.max_threads};")
con.execute(f"SET temp_directory = '{policy.temp_dir.as_posix()}';")
con.execute(f"SET max_temp_directory_size = '{policy.max_temp_disk_mb}MB';")
```

### Resource Limits Default Configuration:
- **Max Memory Budget**: 1,024 MB (1 GB)
- **Max CPU Threads**: 4 worker threads
- **Temp Spill Directory**: `<tempdir>/zye_duckdb_temp`
- **Max Temp Disk Space**: 2,048 MB (2 GB)
- **Query Timeout**: 60.0 seconds

---

## 3. High-Throughput Streaming CSV Ingestion

DuckDB's native `read_csv` table function streams CSV data in parallel chunks without loading the entire file into memory:

```sql
SELECT * FROM read_csv(
    'path/to/dataset.csv',
    auto_detect=true,
    header=true,
    sample_size=50000,
    null_padding=true,
    ignore_errors=true
)
```

### Ingestion Features:
1. **Auto-Detection**: Automatically infers delimiters (comma, tab, semicolon), quote characters, and escape formats.
2. **Null Padding**: Replaces missing fields on short lines with NULL instead of failing.
3. **Error Tolerance**: Skips corrupted lines and records parse warnings.
4. **Column Projection**: When only specific columns are queried (e.g., `SELECT ad_spend, revenue FROM ...`), unneeded columns are skipped during disk scan.
