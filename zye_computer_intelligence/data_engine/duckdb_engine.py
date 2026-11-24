"""
Managed DuckDB Execution Engine.
Provides in-memory connection pooling, memory ceilings, thread bounding, and safe query execution.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import duckdb

from zye_computer_intelligence.security.resource_policy import ResourcePolicy

logger = logging.getLogger("zye.computer_intelligence.duckdb")


class ManagedDuckDB:
    """Encapsulates a managed, resource-governed DuckDB connection."""

    def __init__(self, policy: ResourcePolicy | None = None):
        self.policy = policy or ResourcePolicy()
        self.con: duckdb.DuckDBPyConnection | None = None
        self._is_closed = False

    def __enter__(self) -> ManagedDuckDB:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def open(self) -> duckdb.DuckDBPyConnection:
        """Initializes and configures the in-memory DuckDB connection."""
        if self.con is None or self._is_closed:
            self.con = duckdb.connect(database=":memory:")
            try:
                self.con.execute(f"SET memory_limit = '{self.policy.max_memory_mb}MB';")
                self.con.execute(f"SET threads = {self.policy.max_threads};")
                temp_path = self.policy.temp_dir.as_posix()
                self.con.execute(f"SET temp_directory = '{temp_path}';")
                self.con.execute(f"SET max_temp_directory_size = '{self.policy.max_temp_disk_mb}MB';")
            except Exception as e:
                logger.warning("DuckDB resource tuning warning: %s", e)
            self._is_closed = False
        return self.con

    def execute(self, sql: str, parameters: list[Any] | None = None) -> duckdb.DuckDBPyConnection:
        """Executes a SQL statement and returns the DuckDB connection cursor."""
        con = self.open()
        if parameters:
            return con.execute(sql, parameters)
        return con.execute(sql)

    def query_df(self, sql: str, parameters: list[Any] | None = None, max_rows: int = 100_000) -> Any:
        """Executes query and materializes into a bounded Pandas DataFrame."""
        con = self.open()
        if parameters:
            res = con.execute(sql, parameters)
        else:
            res = con.execute(sql)
        df = res.df()
        if len(df) > max_rows:
            return df.iloc[:max_rows]
        return df

    def close(self) -> None:
        """Closes the connection safely."""
        if self.con is not None and not self._is_closed:
            try:
                self.con.close()
            except Exception as e:
                logger.debug("DuckDB connection close exception: %s", e)
            finally:
                self.con = None
                self._is_closed = True

    def get_csv_read_sql(self, file_path: Path | str, sample_size: int = 50_000) -> str:
        """Constructs safe read_csv SQL expression with robust auto-detection."""
        posix_path = Path(file_path).as_posix()
        # auto_detect=true, header=true, null_padding=true, ignore_errors=true
        return f"SELECT * FROM read_csv('{posix_path}', auto_detect=true, header=true, sample_size={sample_size}, null_padding=true, ignore_errors=true)"
