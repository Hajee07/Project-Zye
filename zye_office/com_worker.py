"""
Dedicated Single-Threaded Apartment (STA) COM Worker — Zye Day 20.
Enforces Windows COM apartment threading safety by serializing all Office COM operations
on a dedicated background worker thread with explicit CoInitializeEx / CoUninitialize.
"""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import sys
import threading
import time
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger("zye.office.com_worker")


class STACOMWorker:
    """
    Dedicated worker thread maintaining a Single-Threaded Apartment (COINIT_APARTMENTTHREADED).
    Prevents RPC_E_WRONG_THREAD (0x8001010E) COM marshaling exceptions by ensuring all COM
    invocations run exclusively inside this thread.
    """

    _instance: Optional["STACOMWorker"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "STACOMWorker":
        """Singleton accessor for global COM STA worker."""
        with cls._lock:
            if cls._instance is None or not cls._instance.is_alive():
                cls._instance = STACOMWorker()
                cls._instance.start()
            return cls._instance

    def __init__(self) -> None:
        self._queue: queue.Queue[Optional[Tuple[Callable[..., Any], Tuple[Any, ...], dict[str, Any], concurrent.futures.Future[Any]]]] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._thread_id: Optional[int] = None

    def start(self) -> None:
        """Start the background STA thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, name="Zye-Office-STA-Worker", daemon=True)
        self._thread.start()
        # Wait briefly for thread to initialize
        deadline = time.monotonic() + 5.0
        while self._thread_id is None and time.monotonic() < deadline:
            time.sleep(0.02)
        logger.info("STA COM Worker thread started (TID: %s)", self._thread_id)

    def is_alive(self) -> bool:
        """Check if worker thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def _worker_loop(self) -> None:
        """Main loop of the STA worker thread with CoInitializeEx lifecycle."""
        self._thread_id = threading.get_ident()
        coinit_success = False
        try:
            import pythoncom
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            coinit_success = True
            logger.debug("CoInitializeEx(COINIT_APARTMENTTHREADED) succeeded on STA worker.")
        except Exception as exc:
            logger.error("Failed to initialize COM on worker thread: %s", exc)

        while not self._stop_event.is_set():
            try:
                task = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if task is None:
                # Poison pill received
                self._queue.task_done()
                break

            func, args, kwargs, future = task
            try:
                if not future.cancelled():
                    result = func(*args, **kwargs)
                    future.set_result(result)
            except Exception as exc:
                if not future.cancelled():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

        if coinit_success:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
                logger.debug("CoUninitialize() executed on STA worker.")
            except Exception as exc:
                logger.warning("Error during CoUninitialize: %s", exc)

        logger.info("STA COM Worker thread terminated.")

    def run(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> Any:
        """
        Submit a callable to the STA worker thread and block until completion or timeout.
        If the current thread is already the STA worker thread, execute directly.
        """
        if threading.get_ident() == self._thread_id:
            # Re-entrant execution within same STA thread
            return func(*args, **kwargs)

        if not self.is_alive():
            self.start()

        future: concurrent.futures.Future[Any] = concurrent.futures.Future()
        self._queue.put((func, args, kwargs, future))

        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            logger.error("Operation on STA COM Worker timed out after %ss: %s", timeout, func)
            raise TimeoutError(f"Office COM operation timed out after {timeout} seconds.")

    def stop(self, timeout: float = 3.0) -> None:
        """Gracefully stop the worker thread."""
        self._stop_event.set()
        self._queue.put(None)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            logger.info("STA COM Worker stopped.")


def run_on_sta_worker(func: Callable[..., Any], *args: Any, timeout: float = 30.0, **kwargs: Any) -> Any:
    """Global helper function to execute an operation on the dedicated STA COM worker."""
    worker = STACOMWorker.get_instance()
    return worker.run(func, *args, timeout=timeout, **kwargs)


def get_shared_sta_worker() -> STACOMWorker:
    """Convenience accessor for global STA COM worker."""
    return STACOMWorker.get_instance()
