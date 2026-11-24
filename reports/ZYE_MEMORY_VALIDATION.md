# ZYE AI — Persistent Memory & Background Extraction Report

**Subsystem:** `zye_memory` (`memory_store.py`, `memory_service.py`)  
**Specification:** Master Specification Section 21  
**Status:** VERIFIED & PASSING  

---

## 1. Problem Statement

Extracting long-term user facts, preferences, and project context directly inside the conversational request loop introduces severe latency spikes, causing audio stuttering or broken streaming in Gemini Live.

---

## 2. Implemented Architecture

### 2.1 Non-Blocking Background Memory Service (`memory_service.py`)
- **Queue Handoff:** Callers invoke `submit_turn(user_text, assistant_text)`. The exchange is pushed into a bounded queue (`maxsize=128`) and returns immediately in microseconds without blocking the caller.
- **Worker Isolation:** A dedicated daemon thread (`ZyeMemoryWorker`) pulls exchanges off the queue and extracts durable facts defensively.
- **Failure Resilience:** Swallows all worker-side extraction errors; a failed extraction never crashes the host process or disrupts user interaction.

### 2.2 SQLite Fact Store (`memory_store.py`)
- **Storage:** SQLite database (`data/memory.db`) with WAL mode enabled.
- **Schema:**
  ```sql
  CREATE TABLE facts (
      id TEXT PRIMARY KEY,
      content TEXT NOT NULL,
      source TEXT NOT NULL,
      confidence REAL NOT NULL,
      created_at REAL NOT NULL,
      updated_at REAL NOT NULL,
      access_count INTEGER NOT NULL DEFAULT 0,
      tags TEXT NOT NULL DEFAULT '[]'
  );
  ```
- **Connection Model:** Per-operation contextmanager pattern with guaranteed `finally: conn.close()` ensuring zero file locks on Windows.

---

## 3. Test Evidence

```
tests/test_memory_scheduler.py::test_fact_store_crud PASSED                    [ 50%]
tests/test_memory_scheduler.py::test_memory_service_background_extraction PASSED [100%]
```
- **CLI Verification:** `python doctor.py --memory-health` returned exit code 0.
