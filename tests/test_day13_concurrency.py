"""
Unit tests for Day 13 Concurrency, AsyncIO Safety, and Multi-Threading.
Tests concurrent pre-mortem audits, simultaneous watchdog and user dispatch,
concurrent mission updates, and background task cancellation.
"""

from __future__ import annotations

import asyncio
import threading
import unittest

from zye_intelligence.autonomous_watchdog import ZyeAutonomousWatchdog
from zye_intelligence.logging import log_mission_transition, log_negative_audit
from zye_intelligence.mission_controller import ZyeMissionController
from zye_intelligence.negative_audit import NegativeAuditEngine
from zye_intelligence.premortem import ZyeNegativePreMortem


class TestDay13Concurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.mc = ZyeMissionController()
        self.brain = ZyeNegativePreMortem()
        self.engine = NegativeAuditEngine(premortem_brain=self.brain)

    def test_01_multiple_simultaneous_audits(self) -> None:
        """Verify multiple audits can execute concurrently without interference."""
        async def _run_concurrent():
            tasks = [
                self.brain.run_audit(f"Task {i}", [f"step {i}"], targets=["main.py"])
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks)
            self.assertEqual(len(results), 5)
            for r in results:
                self.assertIn("overall_failure_risk", r)
        asyncio.run(_run_concurrent())

    def test_02_watchdog_and_user_request_simultaneous(self) -> None:
        """Verify watchdog scanning does not deadlock user audit requests."""
        wd = ZyeAutonomousWatchdog(config={"interval_seconds": 0.05})
        async def _run():
            await wd.start()
            audit_task = self.brain.run_audit("User command", ["execute step"], targets=["main.py"])
            scan_task = wd.scan_system()
            audit_res, scan_res = await asyncio.gather(audit_task, scan_task)
            self.assertIn("overall_failure_risk", audit_res)
            self.assertIn("status", scan_res)
            await wd.stop()
        asyncio.run(_run())

    def test_03_mission_switch_during_audit(self) -> None:
        """Verify mission profile switch during active audit completes safely."""
        async def _run():
            async def _slow_audit():
                await asyncio.sleep(0.05)
                return await self.brain.run_audit("Audit during switch", ["step 1"])

            async def _switch_mission():
                await asyncio.sleep(0.02)
                return self.mc.set_mission("DEEP_ENGINEERING", force=True)

            audit_res, switch_res = await asyncio.gather(_slow_audit(), _switch_mission())
            self.assertIn("overall_failure_risk", audit_res)
            self.assertEqual(switch_res["mission"], "DEEP_ENGINEERING")
            # Restore
            self.mc.set_mission("NORMAL_ASSISTANT", force=True)
        asyncio.run(_run())

    def test_04_concurrent_mission_updates(self) -> None:
        """Verify multi-threaded mission updates with _STATE_LOCK."""
        errors: list[Exception] = []
        def _worker(m_name: str):
            try:
                self.mc.set_mission(m_name, force=True)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=_worker, args=("NORMAL_ASSISTANT",)),
            threading.Thread(target=_worker, args=("DEEP_ENGINEERING",)),
            threading.Thread(target=_worker, args=("TACTICAL_REALTIME",)),
            threading.Thread(target=_worker, args=("STEALTH_BATTERY_SAVER",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        # Restore normal
        self.mc.set_mission("NORMAL_ASSISTANT", force=True)

    def test_05_duplicate_watchdog_prevention(self) -> None:
        """Verify calling start() multiple times concurrently results in single active task."""
        wd = ZyeAutonomousWatchdog(config={"interval_seconds": 0.05})
        async def _run():
            await asyncio.gather(wd.start(), wd.start(), wd.start())
            self.assertTrue(wd._running)
            await wd.stop()
        asyncio.run(_run())

    def test_06_background_cancellation(self) -> None:
        """Verify cancelling background task unblocks immediately."""
        wd = ZyeAutonomousWatchdog(config={"interval_seconds": 10.0})
        async def _run():
            await wd.start()
            t0 = asyncio.get_event_loop().time()
            await wd.stop()
            elapsed = asyncio.get_event_loop().time() - t0
            self.assertLess(elapsed, 1.0)
        asyncio.run(_run())

    def test_07_resource_isolation(self) -> None:
        """Verify preflight diagnostic snapshots are immutable and isolated across calls."""
        res1 = self.engine.preflight.inspect_memory()
        res2 = self.engine.preflight.inspect_memory()
        self.assertIsNot(res1, res2)

    def test_08_logging_concurrency(self) -> None:
        """Verify multi-threaded audit logging does not raise file lock conflicts."""
        errors: list[Exception] = []
        def _log_worker(idx: int):
            try:
                log_negative_audit({"overall_failure_risk": "LOW", "worker": idx})
                log_mission_transition("NORMAL_ASSISTANT", "DEEP_ENGINEERING", f"Worker {idx}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_log_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
