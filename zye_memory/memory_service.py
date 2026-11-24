"""
ZYE AI — Non-Blocking Background Memory Service
===============================================

Implements Section 21 of Master Engineering Specification.
Extracts durable user facts (preferences, ongoing tasks, relationships, names)
on an isolated background daemon thread. Never blocks real-time audio or Gemini Live turns.
Publishes MEMORY_UPDATED events to ZyeEventBus.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType
from zye_memory.memory_store import Fact, FactStore

logger = logging.getLogger("zye.memory.service")

# Heuristic patterns for extracting durable facts without blocking on LLM calls
PREFERENCE_PATTERNS = [
    re.compile(r"(?i)\b(?:my name is|call me|i am|i'm)\s+([A-Za-z0-9_ -]{2,30})"),
    re.compile(r"(?i)\b(?:i prefer|i like|i love|my favorite)\s+([A-Za-z0-9_ -]{3,60})"),
    re.compile(r"(?i)\b(?:i work at|my job is|i am a|i'm a)\s+([A-Za-z0-9_ -]{3,60})"),
    re.compile(r"(?i)\b(?:remember that|note that|keep in mind that)\s+([^.!?\n]{5,120})"),
]


class MemoryService:
    """
    Dedicated worker thread for background memory processing.
    Completely isolated from real-time speech and turn execution.
    """

    def __init__(
        self,
        store: Optional[FactStore] = None,
        event_bus: Optional[ZyeEventBus] = None,
        max_queue_size: int = 128,
    ) -> None:
        self.store = store or FactStore()
        self.event_bus = event_bus
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background processing worker."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="ZyeMemoryWorker",
            daemon=True,
        )
        self._worker_thread.start()
        logger.info("ZYE Background MemoryService started.")

    def stop(self, timeout: float = 2.0) -> None:
        """Stop worker cleanly."""
        if not self._running:
            return
        self._running = False
        try:
            self._queue.put(None, timeout=0.1)
        except queue.Full:
            pass
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
        logger.info("ZYE Background MemoryService stopped.")

    def submit_turn(self, user_text: str, assistant_text: str = "") -> bool:
        """
        Non-blocking handoff from conversation turn.
        Returns True if enqueued, False if dropped due to queue congestion.
        """
        if not user_text or not user_text.strip():
            return False

        try:
            self._queue.put_nowait({"user": user_text, "assistant": assistant_text, "ts": time.time()})
            return True
        except queue.Full:
            logger.warning("MemoryService queue full. Dropping turn extraction to protect response path.")
            return False

    def _worker_loop(self) -> None:
        """Background extraction loop."""
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
                if item is None:
                    break

                self._process_exchange(item["user"], item.get("assistant", ""))
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as exc:
                logger.error("Unhandled error in memory worker loop: %s", exc)

    def _process_exchange(self, user_text: str, assistant_text: str) -> None:
        """Extract durable facts defensively."""
        extracted_facts: List[str] = []

        # 1. Regex heuristic fact extraction
        for pat in PREFERENCE_PATTERNS:
            match = pat.search(user_text)
            if match:
                captured = match.group(0).strip()
                extracted_facts.append(captured)

        # 2. Persist extracted facts
        for f_text in extracted_facts:
            # Avoid redundant duplicate insertions
            existing = self.store.search_facts(f_text, limit=1)
            if not existing:
                fact = self.store.add_fact(f_text, source="conversation", confidence=0.9, tags=["user_profile"])
                logger.info("Durable memory fact recorded: %s", fact.content)
                if self.event_bus:
                    self.event_bus.publish_sync(
                        ZyeEvent(
                            event_type=ZyeEventType.MEMORY_UPDATED,
                            source_module="zye.memory.service",
                            payload={"fact_id": fact.id, "content": fact.content},
                        )
                    )


__all__ = ["MemoryService"]
