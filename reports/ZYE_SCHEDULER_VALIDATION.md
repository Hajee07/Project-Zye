# ZYE AI — Persistent Task Scheduler & Worker Lease Validation

**Subsystem:** `zye_scheduler` (`task_scheduler.py`)  
**Specification:** Master Specification Section 24  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Autonomous assistants that execute cron jobs or delayed maintenance tasks must ensure:
1. Zero overlapping execution of the same task.
2. Resilience against zombie task states if a worker process crashes mid-execution.
3. Durable persistence surviving system reboots.

---

## 2. Engineering Solution

### 2.1 SQLite Persistence & Atomic Leases
- Database: `data/tasks.db` in SQLite WAL mode.
- Table `scheduled_tasks`:
  ```sql
  CREATE TABLE scheduled_tasks (
      id TEXT PRIMARY KEY,
      prompt TEXT NOT NULL,
      schedule_type TEXT NOT NULL,
      schedule_value TEXT NOT NULL,
      status TEXT NOT NULL,
      next_run REAL NOT NULL,
      last_run REAL,
      lease_expires REAL,
      run_count INTEGER NOT NULL DEFAULT 0,
      metadata TEXT NOT NULL DEFAULT '{}'
  );
  ```

### 2.2 Atomic Lease Acquisition & Zombie Recovery
```python
SELECT id FROM scheduled_tasks
WHERE (status = 'active' AND next_run <= :now)
   OR (status = 'running' AND lease_expires IS NOT NULL AND lease_expires < :now);
```
- Atomic `UPDATE scheduled_tasks SET status = 'running', lease_expires = :new_lease WHERE id = :id` guarantees only a single worker can acquire a task.
- If a worker crashes, `lease_expires < :now` automatically allows the next polling cycle to recover and execute the zombie task.

### 2.3 Rescheduling Logic
- `once`: Sets `status = 'completed'`, clears lease.
- `interval`: Increments `run_count`, advances `next_run = now + interval_seconds`, sets `status = 'active'`.

---

## 3. Test Evidence

```
tests/test_memory_scheduler.py::test_task_scheduler_lifecycle_and_worker_leases PASSED [ 50%]
tests/test_memory_scheduler.py::test_task_scheduler_zombie_lease_recovery PASSED       [100%]
```
- **CLI Verification:** `python doctor.py --scheduler-health` returned exit code 0.
