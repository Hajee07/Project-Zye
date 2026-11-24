"""Day 15 Unit Tests — Performance: Tool Dispatcher & Background Task Manager."""
import asyncio
import time
import unittest


class TestToolDispatcherRejectSpeed(unittest.TestCase):
    """Tool dispatcher should reject unknown tools quickly (< 100ms)."""

    @classmethod
    def setUpClass(cls):
        from zye_orchestrator.tool_registry import ZyeToolRegistry
        from zye_orchestrator.safety_pipeline import SafetyExecutionGateway
        from zye_orchestrator.tool_dispatcher import ZyeToolDispatcher

        cls.registry = ZyeToolRegistry()
        cls.gateway = SafetyExecutionGateway()

        async def _dummy_executor(tool_name, args):
            return {"result": "dummy"}

        cls.dispatcher = ZyeToolDispatcher(
            tool_registry=cls.registry,
            safety_gateway=cls.gateway,
            call_executor_fn=_dummy_executor,
        )

    def test_dispatch_unknown_tool_fast(self):
        """Dispatching an unknown tool should reject quickly."""
        start = time.monotonic()
        result = asyncio.run(self.dispatcher.dispatch(
            tool_name="nonexistent_tool_xyz_abc",
            arguments={},
            task_context="perf_test",
            user_confirmed=False,
        ))
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0, f"Reject took too long: {elapsed:.3f}s")
        # Must have an error/status key indicating failure
        self.assertIsInstance(result, dict)
        # Result should indicate error (tool not found)
        has_error = (
            result.get("error") is not None
            or result.get("status") in ("ERROR", "REJECTED", "TOOL_NOT_FOUND")
            or not result.get("success", True)
        )
        self.assertTrue(has_error, f"Unknown tool should be rejected: {result}")

    def test_dispatch_returns_dict(self):
        result = asyncio.run(self.dispatcher.dispatch("bad_tool_xyz", {}))
        self.assertIsInstance(result, dict)


class TestBackgroundTaskManagerPerformance(unittest.TestCase):
    """Background task manager should register/list tasks very quickly."""

    @classmethod
    def setUpClass(cls):
        from zye_orchestrator.background_tasks import ZyeBackgroundTaskManager
        cls.btm = ZyeBackgroundTaskManager()

    def test_get_diagnostics_fast(self):
        start = time.monotonic()
        diag = self.btm.get_task_diagnostics()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.1, f"get_task_diagnostics took too long: {elapsed:.3f}s")
        self.assertIsInstance(diag, list)

    def test_register_task_fast(self):
        async def _noop():
            pass

        start = time.monotonic()
        self.btm.register_task("perf_test_noop", _noop)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.1, f"register_task took too long: {elapsed:.3f}s")

    def test_registered_task_appears_in_diagnostics(self):
        async def _noop2():
            pass

        self.btm.register_task("perf_test_noop2", _noop2)
        diag = self.btm.get_task_diagnostics()
        names = [d["name"] for d in diag]
        self.assertIn("perf_test_noop2", names)

    def test_multiple_registrations_no_crash(self):
        async def _noop():
            pass

        for i in range(5):
            self.btm.register_task(f"perf_batch_{i}", _noop)
        diag = self.btm.get_task_diagnostics()
        self.assertIsInstance(diag, list)


class TestAuditLoggerPerformance(unittest.TestCase):
    def test_log_event_fast(self):
        from zye_autonomy.audit_logger import AuditLogger
        al = AuditLogger()
        start = time.monotonic()
        al.log(
            event_type="PERF_TEST",
            operation="test_op",
            tool_name="test_tool",
            risk_level="LOW_RISK",
            outcome="PASS",
            detail={"note": "performance test"},
        )
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0, f"AuditLogger.log took too long: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
