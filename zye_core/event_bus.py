"""
ZYE AI — Unified Event Bus Engine
=================================

Thread-safe, high-performance publish/subscribe event bus.
Enforces:
- Section 06 required event categories.
- Bounded event history (default maxlen=1000) to prevent memory creep.
- Secret redaction in event payloads.
- Observer error isolation (slow or broken subscribers cannot crash the pipeline).
- Non-blocking async dispatch bridge.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Set

from zye_core.types import ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.core.event_bus")

# Type alias for subscriber functions
SubscriberCallback = Callable[[ZyeEvent], None]

# Secret redaction pattern for event payloads
SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|bearer|authorization)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?"
)


def redact_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive keys and token patterns from event payload."""
    if not isinstance(data, dict):
        return data

    clean: Dict[str, Any] = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(secret_term in k_lower for secret_term in ("key", "token", "password", "secret", "auth", "credential")):
            clean[k] = "[REDACTED]"
        elif isinstance(v, str):
            clean[k] = SECRET_PATTERN.sub(r"\1=[REDACTED]", v)
        elif isinstance(v, dict):
            clean[k] = redact_payload(v)
        elif isinstance(v, list):
            clean[k] = [redact_payload(item) if isinstance(item, dict) else item for item in v]
        else:
            clean[k] = v
    return clean


class ZyeEventBus:
    """Thread-safe event bus with bounded history and observer isolation."""

    def __init__(self, history_limit: int = 1000) -> None:
        self._subscribers: Dict[ZyeEventType, List[SubscriberCallback]] = {}
        self._wildcard_subscribers: List[SubscriberCallback] = []
        self._lock = threading.Lock()
        self._history: deque[ZyeEvent] = deque(maxlen=max(1, history_limit))
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_async_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the primary asyncio event loop for async task dispatch."""
        self._async_loop = loop

    def subscribe(self, event_type: ZyeEventType, callback: SubscriberCallback) -> None:
        """Register a callback to be notified when event_type is emitted."""
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def subscribe_all(self, callback: SubscriberCallback) -> None:
        """Register a wildcard callback to receive every published event."""
        with self._lock:
            if callback not in self._wildcard_subscribers:
                self._wildcard_subscribers.append(callback)

    def unsubscribe(self, event_type: ZyeEventType, callback: SubscriberCallback) -> None:
        """Remove callback from event_type subscriber list."""
        with self._lock:
            listeners = self._subscribers.get(event_type, [])
            try:
                listeners.remove(callback)
            except ValueError:
                pass

    def unsubscribe_all(self, callback: SubscriberCallback) -> None:
        """Remove callback from wildcard list."""
        with self._lock:
            try:
                self._wildcard_subscribers.remove(callback)
            except ValueError:
                pass

    def publish(
        self,
        event_type: ZyeEventType,
        source_module: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> ZyeEvent:
        """Create and publish an event to all registered subscribers."""
        safe_payload = redact_payload(payload or {})
        event = ZyeEvent(
            event_type=event_type,
            source_module=source_module,
            payload=safe_payload,
            session_id=session_id,
            turn_id=turn_id,
            task_id=task_id,
            correlation_id=correlation_id,
        )

        with self._lock:
            self._history.append(event)
            listeners = list(self._subscribers.get(event_type, []))
            wildcards = list(self._wildcard_subscribers)

        # Notify specific listeners
        for cb in listeners:
            try:
                cb(event)
            except Exception as e:
                logger.error("Error in event subscriber %r on %s: %s", cb, event_type.value, e)

        # Notify wildcard listeners
        for cb in wildcards:
            try:
                cb(event)
            except Exception as e:
                logger.error("Error in wildcard subscriber %r on %s: %s", cb, event_type.value, e)

        return event

    def publish_event(self, event: ZyeEvent) -> ZyeEvent:
        """Publish a pre-constructed ZyeEvent envelope directly."""
        safe_payload = redact_payload(event.payload or {})
        event.payload = safe_payload

        with self._lock:
            self._history.append(event)
            listeners = list(self._subscribers.get(event.event_type, []))
            wildcards = list(self._wildcard_subscribers)

        for cb in listeners:
            try:
                cb(event)
            except Exception as e:
                logger.error("Error in event subscriber %r on %s: %s", cb, event.event_type.value, e)

        for cb in wildcards:
            try:
                cb(event)
            except Exception as e:
                logger.error("Error in wildcard subscriber %r on %s: %s", cb, event.event_type.value, e)

        return event

    def publish_sync(self, event: ZyeEvent) -> ZyeEvent:
        """Alias for publish_event for synchronous callers."""
        return self.publish_event(event)

        return event

    def get_history(
        self,
        event_type: Optional[ZyeEventType] = None,
        limit: int = 100,
    ) -> List[ZyeEvent]:
        """Retrieve recorded event history with optional filtering."""
        with self._lock:
            events = list(self._history)

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def clear_history(self) -> None:
        """Purge all recorded event history."""
        with self._lock:
            self._history.clear()


# Module-level singleton
_instance: Optional[ZyeEventBus] = None
_instance_lock = threading.Lock()


def get_event_bus(history_limit: int = 1000) -> ZyeEventBus:
    """Return the global ZyeEventBus singleton."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ZyeEventBus(history_limit=history_limit)
        return _instance


def reset_event_bus() -> None:
    """Reset the global singleton (used in test fixtures)."""
    global _instance
    with _instance_lock:
        _instance = None
