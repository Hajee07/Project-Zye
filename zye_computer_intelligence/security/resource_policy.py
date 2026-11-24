"""
Resource Governance & Analysis Job Lifecycle Management.
Controls CPU thread allocation, memory budgets, and query cancellation tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any
import uuid

logger = logging.getLogger("zye.computer_intelligence.resource")


@dataclass
class ResourcePolicy:
    """Resource constraints for analytical execution."""
    max_memory_mb: int = 1024  # 1 GB default memory limit for DuckDB
    max_threads: int = 4       # Bounded CPU threads
    temp_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "zye_duckdb_temp")
    max_temp_disk_mb: int = 2048 # 2 GB temporary spill limit
    query_timeout_seconds: float = 60.0

    def __post_init__(self):
        self.temp_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class AnalysisJob:
    """Represents a tracked analytical execution job."""
    job_id: str
    dataset_path: str
    operation: str
    status: str = "QUEUED"  # QUEUED, RUNNING, COMPLETED, CANCELLED, FAILED, TIMED_OUT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    duration_ms: float = 0.0
    progress_pct: int = 0
    result: dict[str, Any] | None = None
    error_message: str | None = None
    cancellation_requested: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def request_cancellation(self) -> None:
        with self._lock:
            self.cancellation_requested = True
            if self.status in ("QUEUED", "RUNNING"):
                self.status = "CANCELLED"
                self.completed_at = datetime.now(timezone.utc).isoformat()


class JobManager:
    """Thread-safe manager for analysis jobs."""
    _instance: JobManager | None = None
    _lock = threading.Lock()

    def __new__(cls) -> JobManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.jobs = {}
                cls._instance.policy = ResourcePolicy()
            return cls._instance

    def create_job(self, dataset_path: str, operation: str) -> AnalysisJob:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = AnalysisJob(job_id=job_id, dataset_path=dataset_path, operation=operation)
        with self._lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job:
            job.request_cancellation()
            return True
        return False

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            recent = sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]
            return [
                {
                    "job_id": j.job_id,
                    "dataset_path": j.dataset_path,
                    "operation": j.operation,
                    "status": j.status,
                    "created_at": j.created_at,
                    "duration_ms": j.duration_ms,
                    "error_message": j.error_message,
                }
                for j in recent
            ]
