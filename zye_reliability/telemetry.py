"""
Zye AI — Telemetry, Metrics & Audit Engine (Day 17).
Provides rotating file telemetry logging, error distribution aggregation, tool health metrics,
server reliability analytics, and correlation trace context.
"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional
import uuid

from zye_reliability.error_handler import redact_error_details

# Context variable for current trace ID
current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_trace_id", default=""
)


class CorrelationContext:
    """Helper to get and set current asynchronous execution trace IDs."""

    @staticmethod
    def get_trace_id() -> str:
        tid = current_trace_id.get()
        if not tid:
            tid = uuid.uuid4().hex[:12]
            current_trace_id.set(tid)
        return tid

    @staticmethod
    def set_trace_id(trace_id: str) -> None:
        current_trace_id.set(trace_id)


class ZyeTelemetryLogger:
    """Thread-safe telemetry logger writing structured JSON records to logs/zye_telemetry.log."""

    _instance: Optional[ZyeTelemetryLogger] = None

    def __init__(self, log_path: Optional[Path] = None) -> None:
        if log_path is None:
            # Walk up to locate project root
            origin = Path(__file__).resolve().parent
            curr = origin
            root = origin
            for _ in range(5):
                if (curr / "zye_config.toml").is_file():
                    root = curr
                    break
                curr = curr.parent
            self.log_path = root / "logs" / "zye_telemetry.log"
        else:
            self.log_path = log_path

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # Unique logger if custom path, otherwise standard singleton
        logger_name = f"zye.telemetry.{abs(hash(str(self.log_path)))}" if log_path is not None else "zye.telemetry"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Ensure our handler writes to this specific log_path
        existing = [h for h in self._logger.handlers if isinstance(h, RotatingFileHandler)]
        if not existing:
            try:
                rfh = RotatingFileHandler(
                    self.log_path,
                    maxBytes=5 * 1024 * 1024,
                    backupCount=3,
                    encoding="utf-8",
                )
                rfh.setFormatter(logging.Formatter("%(message)s"))
                self._logger.addHandler(rfh)
            except Exception:
                self._logger.addHandler(logging.NullHandler())

    def close(self) -> None:
        """Close and remove all file handlers to release file locks on Windows."""
        for handler in list(self._logger.handlers):
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
            self._logger.removeHandler(handler)

    @classmethod
    def get_instance(cls, log_path: Optional[Path] = None) -> ZyeTelemetryLogger:
        if cls._instance is None:
            cls._instance = cls(log_path=log_path)
        return cls._instance

    def _write_record(self, record: dict[str, Any]) -> None:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        # Redact any strings in record
        sanitized = json.loads(redact_error_details(json.dumps(record, ensure_ascii=False)))
        self._logger.info(json.dumps(sanitized, ensure_ascii=False))
        for handler in self._logger.handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def log_tool_execution(
        self,
        tool_name: str,
        trace_id: str,
        duration_ms: float,
        status: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log execution latency and outcome of an MCP tool invocation."""
        record = {
            "event_type": "tool_execution",
            "tool_name": tool_name,
            "trace_id": trace_id,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "details": details or {},
        }
        self._write_record(record)

    def log_error(
        self,
        tool_name: str,
        trace_id: str,
        error_code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log an error occurrence with sanitized message and classification code."""
        record = {
            "event_type": "error",
            "tool_name": tool_name,
            "trace_id": trace_id,
            "error_code": error_code,
            "message": message,
            "details": details or {},
        }
        self._write_record(record)

    def log_recovery(
        self,
        server_name: str,
        trace_id: str,
        action: str,
        result: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Log MCP server hot reload, crash restart, or application recovery event."""
        record = {
            "event_type": "server_recovery",
            "server_name": server_name,
            "trace_id": trace_id,
            "action": action,
            "result": result,
            "details": details or {},
        }
        self._write_record(record)

    def _read_recent_records(self, last_n_minutes: int) -> list[dict[str, Any]]:
        """Read and parse records written within the past N minutes."""
        if not self.log_path.is_file():
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=last_n_minutes)
        records: list[dict[str, Any]] = []

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        data = json.loads(s)
                        ts_str = data.get("timestamp")
                        if ts_str:
                            rec_dt = datetime.fromisoformat(ts_str)
                            if rec_dt >= cutoff:
                                records.append(data)
                    except Exception:
                        continue
        except Exception:
            pass

        return records

    def get_error_summary(self, last_n_minutes: int = 60) -> dict[str, Any]:
        """Aggregate error occurrences by error code and identify frequent culprits."""
        records = self._read_recent_records(last_n_minutes)
        errors = [r for r in records if r.get("event_type") == "error"]

        code_counts: dict[str, int] = {}
        tool_counts: dict[str, int] = {}

        for err in errors:
            code = err.get("error_code", "UNKNOWN")
            tool = err.get("tool_name", "UNKNOWN")
            code_counts[code] = code_counts.get(code, 0) + 1
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "time_window_minutes": last_n_minutes,
            "total_errors": len(errors),
            "by_error_code": code_counts,
            "by_tool": tool_counts,
            "recent_errors": errors[-10:] if errors else [],
        }

    def get_tool_health(self, tool_name: str, last_n_minutes: int = 60) -> dict[str, Any]:
        """Calculate success rate and average execution latency for a specified tool."""
        records = self._read_recent_records(last_n_minutes)
        tool_execs = [
            r for r in records
            if r.get("event_type") == "tool_execution" and r.get("tool_name") == tool_name
        ]

        total = len(tool_execs)
        if total == 0:
            return {
                "tool_name": tool_name,
                "total_calls": 0,
                "success_rate": 1.0,
                "avg_duration_ms": 0.0,
                "status": "IDLE",
            }

        successes = sum(1 for r in tool_execs if r.get("status") in ("success", "SUCCESS"))
        total_duration = sum(r.get("duration_ms", 0.0) for r in tool_execs)
        success_rate = round(successes / total, 4)
        avg_dur = round(total_duration / total, 2)

        status = "HEALTHY" if success_rate >= 0.9 else ("DEGRADED" if success_rate >= 0.6 else "UNHEALTHY")

        return {
            "tool_name": tool_name,
            "total_calls": total,
            "success_calls": successes,
            "failed_calls": total - successes,
            "success_rate": success_rate,
            "avg_duration_ms": avg_dur,
            "status": status,
        }

    def get_server_health(self, server_name: str, last_n_minutes: int = 60) -> dict[str, Any]:
        """Assess overall health status and recovery frequency of an MCP server."""
        records = self._read_recent_records(last_n_minutes)
        recovs = [
            r for r in records
            if r.get("event_type") == "server_recovery" and r.get("server_name") == server_name
        ]

        total_recoveries = len(recovs)
        successful_recoveries = sum(1 for r in recovs if r.get("result") == "SUCCESS")

        status = "HEALTHY"
        if total_recoveries > 3:
            status = "FLAPPING"
        elif total_recoveries > 0 and successful_recoveries < total_recoveries:
            status = "DEGRADED"

        return {
            "server_name": server_name,
            "time_window_minutes": last_n_minutes,
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "health_status": status,
        }
