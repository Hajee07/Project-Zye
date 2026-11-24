# ZYE AI — DAY 31 CSV & EXCEL INGESTION SPECIFICATION

## 1. Overview & Format Coverage
The Day 31 ingestion pipeline handles diverse tabular data formats commonly found in enterprise and research workflows:
- **CSV (`.csv`)**: Comma-delimited files, streaming via DuckDB.
- **TSV (`.tsv`)**: Tab-delimited files, streaming via DuckDB.
- **Compressed CSV (`.csv.gz`)**: Gzip-compressed CSV streams.
- **Excel OpenXML (`.xlsx`)**: Modern multi-sheet workbooks via pandas/openpyxl.
- **Excel Legacy (`.xls`)**: Classic binary workbooks.
- **Parquet (`.parquet`)**: High-performance columnar data files.

---

## 2. Ingestion & Schema Inspection Workflow

```mermaid
flowchart TD
    A[Dataset File Path] --> B{Path & Format Validation}
    B -->|Invalid Path / Extension| E1[Reject: Structured Error Code]
    B -->|Size > 2GB| E2[Reject: DATASET_EXCEEDS_SIZE_LIMIT]
    B -->|Valid File| C{File Format}
    
    C -->|CSV / TSV / Parquet| D[Backend: DUCKDB]
    C -->|Excel .xlsx / .xls| E[Backend: PANDAS]
    
    D --> F[DuckDB DESCRIBE Statement<br/>LIMIT 0 Sample]
    E --> G[ExcelFile Sheet Enumeration<br/>Read First 10 Rows]
    
    F & G --> H[Classify Columns: Numeric, Date, Categorical, ID]
    H --> I[Exact Row Count Query]
    I --> J[Compile Ingestion Metadata & Schema Model]
```

---

## 3. Read-Only Disk Preservation Guarantee

ZYE AI strictly enforces read-only access on all analyzed datasets:
- **Zero In-Place Mutations**: Files are opened with read-only flags (`mode="r"` or DuckDB read functions).
- **No Temporary Overwrites**: Intermediate analysis results are stored exclusively in in-memory DuckDB tables or designated temporary directories.
- **Audit Verification**: Verified in `test_03_read_only_guarantee_preserves_disk_files` by asserting SHA hashes and byte sizes before and after analytical queries.
