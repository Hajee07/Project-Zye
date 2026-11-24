# ZYE AI — Day 28 Conflict Detection & Free-Slot Engine

## 1. Conflict Interval Math
Meeting intervals are modeled as half-open sets $[start, end)$. Two meetings $A$ and $B$ collide if and only if:
$$\text{start}_A < \text{end}_B \quad \land \quad \text{end}_A > \text{start}_B$$

```
Case 1: Boundary Touching (NO CONFLICT)
[  Meeting A: 10:00 - 11:00  )
                             [  Meeting B: 11:00 - 12:00  )
Condition: 10:00 < 12:00 (True), BUT 11:00 > 11:00 (False) -> NOT CONFLICT

Case 2: Overlapping (CONFLICT)
[  Meeting A: 10:00 - 11:00  )
                  [  Meeting B: 10:30 - 11:30  )
Condition: 10:00 < 11:30 (True) AND 11:00 > 10:30 (True) -> CONFLICT DETECTED!
```

### SQL Implementation
```sql
SELECT id, title, start_iso, end_iso, start_utc, end_utc, location
FROM events
WHERE event_status NOT IN ('CANCELLED', 'DELETED')
  AND start_utc < ?   -- requested end_utc_ms
  AND end_utc > ?     -- requested start_utc_ms
  AND id != ?         -- exclude self during update
ORDER BY start_utc ASC;
```

---

## 2. Automatic Conflict Blocking
By default, `CalendarEventEngine.create_event` and `update_event` reject conflicting bookings with `status="CONFLICT_BLOCKED"`.
The response contains:
1. `conflicts`: List of all colliding meetings (titles, times, locations).
2. `suggested_slots`: Up to 3 alternative free time slots within business hours.
3. `explanation`: Natural speech summary explaining why the slot cannot be booked and offering alternatives.

### Force Override
If an urgent executive meeting must take priority, passing `force_override=True` bypasses conflict rejection and records the event while keeping track of overlapping commitments.

---

## 3. Free-Slot Availability Discovery
`find_free_time_slots` scans the target day between business hours (default 09:00 to 18:00):
1. Normalizes local working hours into UTC epoch boundaries $[day\_start, day\_end)$.
2. If scanning the current day, clips $day\_start$ to the next 15-minute mark ahead of current time to suppress impossible past slots.
3. Retrieves all busy blocks sorted by start time.
4. Identifies gaps that satisfy $cursor + duration\_ms \le busy\_start$.
5. Emits structured recommendation objects with human-readable labels (e.g. `11:00 AM - 12:00 PM`).
