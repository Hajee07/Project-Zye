"""
Unit tests for ZYE Memory Infrastructure and Task Scheduler with Worker Leases.
"""

from __future__ import annotations

import os
import tempfile
import time
import pytest
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEventType
from zye_memory.memory_service import MemoryService
from zye_memory.memory_store import FactStore
from zye_scheduler.task_scheduler import TaskScheduler, ScheduledTask


def test_fact_store_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory.db")
        store = FactStore(db_path=db_path)

        # 1. Add facts
        f1 = store.add_fact("User prefers dark mode", source="test", tags=["ui"])
        f2 = store.add_fact("User works at DeepMind as Senior Architect", source="test", tags=["profile"])

        # 2. Search facts
        results = store.search_facts("dark mode")
        assert len(results) == 1
        assert results[0].id == f1.id
        assert "dark mode" in results[0].content

        # 3. List facts
        all_facts = store.list_facts()
        assert len(all_facts) == 2

        # 4. Delete fact
        deleted = store.delete_fact(f1.id)
        assert deleted is True
        assert len(store.list_facts()) == 1


def test_memory_service_background_extraction():
    bus = ZyeEventBus()
    events_received = []
    bus.subscribe(ZyeEventType.MEMORY_UPDATED, lambda ev: events_received.append(ev))

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory.db")
        store = FactStore(db_path=db_path)
        service = MemoryService(store=store, event_bus=bus)

        service.start()
        try:
            # Submit non-blocking turn
            enqueued = service.submit_turn("Hello Zye, my name is John Doe and I prefer python for coding.")
            assert enqueued is True

            # Wait briefly for background worker
            time.sleep(0.5)

            facts = store.list_facts()
            assert len(facts) >= 1
            assert any("John Doe" in f.content or "python" in f.content for f in facts)
            assert len(events_received) >= 1
        finally:
            service.stop()


def test_task_scheduler_lifecycle_and_worker_leases():
    bus = ZyeEventBus()
    started_events = []
    completed_events = []
    bus.subscribe(ZyeEventType.TASK_STARTED, lambda ev: started_events.append(ev))
    bus.subscribe(ZyeEventType.TASK_COMPLETED, lambda ev: completed_events.append(ev))

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        scheduler = TaskScheduler(db_path=db_path, event_bus=bus)

        # 1. Schedule one-off task due immediately
        t_once = scheduler.schedule(
            prompt="Clean temporary cache files",
            schedule_type="once",
            schedule_value="0",
            initial_delay_seconds=0.0,
        )
        assert t_once.status == "active"

        # 2. Schedule interval task
        t_interval = scheduler.schedule(
            prompt="Health check",
            schedule_type="interval",
            schedule_value="60.0",
            initial_delay_seconds=0.0,
        )

        executed_prompts = []
        def mock_executor(task: ScheduledTask):
            executed_prompts.append(task.prompt)

        # Run polling cycle
        count = scheduler.run_due_tasks_once(executor=mock_executor)
        assert count == 2
        assert "Clean temporary cache files" in executed_prompts
        assert "Health check" in executed_prompts

        # Verify t_once completed
        tasks = scheduler.list_tasks()
        once_task = [t for t in tasks if t.id == t_once.id][0]
        assert once_task.status == "completed"

        # Verify interval task rescheduled to active
        interval_task = [t for t in tasks if t.id == t_interval.id][0]
        assert interval_task.status == "active"
        assert interval_task.run_count == 1
        assert interval_task.next_run > time.time()

        # Check events
        assert len(started_events) == 2
        assert len(completed_events) == 2


def test_task_scheduler_zombie_lease_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        scheduler = TaskScheduler(db_path=db_path)

        task = scheduler.schedule(
            prompt="Zombie test",
            schedule_type="once",
            schedule_value="0",
            initial_delay_seconds=0.0,
        )

        # Acquire task with very short lease (0.1s)
        due = scheduler.acquire_due_tasks(lease_seconds=0.1)
        assert len(due) == 1
        assert due[0].status == "running"

        # Second immediate acquisition attempt should get nothing (active lease)
        due_again = scheduler.acquire_due_tasks(lease_seconds=0.1)
        assert len(due_again) == 0

        # Wait for lease to expire
        time.sleep(0.2)

        # Zombie recovery: acquisition now succeeds!
        recovered = scheduler.acquire_due_tasks(lease_seconds=60.0)
        assert len(recovered) == 1
        assert recovered[0].id == task.id
