# ZYE AI — Day 28 SQLite Database Schema & Migrations

## 1. Schema Versioning
Schema versions are stored in `schema_versions` table in `data/zye_assistant_db.sqlite`.
- **Target Schema Version:** `28`
- **Module Identifier:** `calendar`

```sql
CREATE TABLE IF NOT EXISTS schema_versions (
    module TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
```

## 2. The `events` Table (Day 28 Upgrades)
The legacy Day 14 `events` table was extended with non-destructive columns to support millisecond-precision UTC conflict detection and optimistic locking.

| Column | Type | Constraints / Default | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique event identifier |
| `title` | TEXT | NOT NULL | Meeting title or subject |
| `start_iso` | TEXT | NOT NULL | Local ISO 8601 string with timezone offset |
| `end_iso` | TEXT | NOT NULL | Local ISO 8601 string with timezone offset |
| `start_utc` | INTEGER | DEFAULT 0 | UTC epoch in milliseconds (indexed) |
| `end_utc` | INTEGER | DEFAULT 0 | UTC epoch in milliseconds (indexed) |
| `timezone_id` | TEXT | DEFAULT 'Asia/Kolkata' | IANA timezone identifier |
| `version` | INTEGER | DEFAULT 1 | Optimistic concurrency version |
| `source` | TEXT | DEFAULT 'voice' | Creation channel (`voice`, `mcp`, `ui`) |
| `operation_id` | TEXT | DEFAULT '' | UUID for idempotency duplicate protection |
| `location` | TEXT | DEFAULT 'online' | Physical or virtual meeting location |
| `notes` | TEXT | DEFAULT '' | Agenda or discussion points |
| `reminded_15m` | INTEGER | DEFAULT 0 | Legacy 15-minute flag (mirrored) |
| `reminded_2m` | INTEGER | DEFAULT 0 | Legacy 2-minute flag (mirrored) |
| `event_status` | TEXT | DEFAULT 'SCHEDULED' | `SCHEDULED`, `CANCELLED`, `COMPLETED`, `DELETED` |
| `created_at` | TEXT | DEFAULT (datetime('now')) | ISO creation timestamp |
| `updated_at` | TEXT | DEFAULT '' | ISO last update timestamp |

### Indices
- `idx_events_start_utc`: `CREATE INDEX IF NOT EXISTS idx_events_start_utc ON events(start_utc);`
- `idx_events_end_utc`: `CREATE INDEX IF NOT EXISTS idx_events_end_utc ON events(end_utc);`
- `idx_events_status`: `CREATE INDEX IF NOT EXISTS idx_events_status ON events(event_status);`

---

## 3. The `event_reminders` Table
Dedicated persistent reminder storage decoupling alarm scheduling from event rows.

```sql
CREATE TABLE IF NOT EXISTS event_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    reminder_type TEXT NOT NULL,
    offset_seconds INTEGER NOT NULL,
    due_at_utc INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER DEFAULT 0,
    claimed_at_utc INTEGER DEFAULT NULL,
    delivered_at_utc INTEGER DEFAULT NULL,
    last_error_code TEXT DEFAULT NULL,
    created_at_utc INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    UNIQUE(event_id, event_version, reminder_type)
);
```

### Indices
- `idx_reminders_due`: `CREATE INDEX IF NOT EXISTS idx_reminders_due ON event_reminders(due_at_utc, status);`
- `idx_reminders_event`: `CREATE INDEX IF NOT EXISTS idx_reminders_event ON event_reminders(event_id, status);`
