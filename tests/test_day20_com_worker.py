"""
Unit Tests for Zye Day 20 Single-Threaded Apartment (STA) COM Worker.
Tests thread isolation, re-entrancy, queue execution, timeout handling, and lifecycle.
"""

import unittest
import threading
import time
from unittest.mock import MagicMock

from zye_office.com_worker import STACOMWorker, run_on_sta_worker, get_shared_sta_worker


class TestDay20COMWorker(unittest.TestCase):

    def setUp(self):
        self.worker = STACOMWorker.get_instance()

    def test_worker_singleton(self):
        w1 = STACOMWorker.get_instance()
        w2 = get_shared_sta_worker()
        self.assertIs(w1, w2)
        self.assertTrue(self.worker.is_alive())

    def test_run_simple_task(self):
        result = self.worker.run(lambda x, y: x + y, 10, 20)
        self.assertEqual(result, 30)

    def test_thread_isolation(self):
        caller_tid = threading.get_ident()
        worker_tid = self.worker.run(lambda: threading.get_ident())
        self.assertNotEqual(caller_tid, worker_tid)

    def test_reentrant_execution(self):
        def inner():
            return "nested_success"

        def outer():
            # Calling run from within the STA thread should execute synchronously
            return self.worker.run(inner)

        res = self.worker.run(outer)
        self.assertEqual(res, "nested_success")

    def test_exception_propagation(self):
        def failing_task():
            raise ValueError("STA worker test exception")

        with self.assertRaises(ValueError) as ctx:
            self.worker.run(failing_task)
        self.assertIn("STA worker test exception", str(ctx.exception))

    def test_timeout_handling(self):
        def slow_task():
            time.sleep(0.5)
            return "done"

        with self.assertRaises(TimeoutError):
            self.worker.run(slow_task, timeout=0.1)

    def test_run_on_sta_worker_helper(self):
        val = run_on_sta_worker(lambda: 42)
        self.assertEqual(val, 42)


if __name__ == "__main__":
    unittest.main()
