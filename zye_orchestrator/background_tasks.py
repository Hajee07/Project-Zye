"""
Background Task Manager for Zye Master MCP Orchestrator (Day 15).
Oversees the lifecycle of proactive background daemons (Watchdog, Meeting Reminders,
Health Monitoring), prevents duplicates, tracks errors, and coordinates graceful shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger("zye.orchestrator.background_tasks")


class TaskState(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BackgroundTaskRecord:
    def __init__(self, name: str, coro_fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self.name = name
        self.coro_fn = coro_fn
        self.state = TaskState.INITIALIZED
        self.task: Optional[asyncio.Task] = None
        self.started_at: str = ""
        self.last_success: str = ""
        self.last_error: str = ""
        self.restart_count: int = 0
        self.is_cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "started_at": self.started_at,
            "last_success": self.last_success,
            "last_error": self.last_error,
            "restart_count": self.restart_count,
            "is_cancelled": self.is_cancelled,
        }


class ZyeBackgroundTaskManager:
    """
    Coordinates and monitors all asynchronous long-running background tasks.
    Prevents duplicate loops and ensures reliable cancellation on shutdown.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTaskRecord] = {}
        self._shutting_down = False

    def register_task(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, None]],
    ) -> BackgroundTaskRecord:
        """Register a background task definition without starting it."""
        clean_name = name.strip()
        if clean_name in self._tasks:
            logger.debug("Task '%s' already registered.", clean_name)
            return self._tasks[clean_name]

        rec = BackgroundTaskRecord(name=clean_name, coro_fn=coro_fn)
        self._tasks[clean_name] = rec
        return rec

    def start_task(self, name: str) -> bool:
        """Start a registered background task. Prevents duplicate running tasks."""
        if self._shutting_down:
            logger.warning("Cannot start background task '%s' during shutdown.", name)
            return False

        rec = self._tasks.get(name)
        if not rec:
            logger.error("Cannot start unregistered background task: '%s'", name)
            return False

        if rec.task and not rec.task.done():
            logger.debug("Task '%s' is already running.", name)
            return True

        async def _wrapped_runner() -> None:
            rec.state = TaskState.RUNNING
            rec.started_at = datetime.now(timezone.utc).isoformat()
            logger.info("Background task '%s' started.", name)
            try:
                await rec.coro_fn()
                rec.state = TaskState.STOPPED
                rec.last_success = datetime.now(timezone.utc).isoformat()
                logger.info("Background task '%s' stopped normally.", name)
            except asyncio.CancelledError:
                rec.state = TaskState.CANCELLED
                rec.is_cancelled = True
                logger.info("Background task '%s' received cancellation.", name)
            except Exception as exc:
                rec.state = TaskState.FAILED
                rec.last_error = str(exc)
                logger.error("Background task '%s' crashed: %s", name, exc)

        rec.is_cancelled = False
        rec.task = asyncio.create_task(_wrapped_runner(), name=f"zye_bg_{name}")
        return True

    async def cancel_task(self, name: str, timeout: float = 3.0) -> bool:
        """Cancel and wait for a single background task."""
        rec = self._tasks.get(name)
        if not rec or not rec.task:
            return True

        if not rec.task.done():
            rec.task.cancel()
            rec.is_cancelled = True
            try:
                await asyncio.wait_for(asyncio.shield(rec.task), timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.debug("Exception during task cancellation for '%s': %s", name, e)

        rec.state = TaskState.CANCELLED
        return True

    async def cancel_all(self, timeout: float = 5.0) -> dict[str, bool]:
        """Cancel all registered background tasks in parallel."""
        self._shutting_down = True
        results = {}
        for name in list(self._tasks.keys()):
            results[name] = await self.cancel_task(name, timeout=timeout)
        return results

    def get_task_diagnostics(self) -> list[dict[str, Any]]:
        """Return diagnostic state for all managed tasks."""
        return [rec.to_dict() for rec in self._tasks.values()]
