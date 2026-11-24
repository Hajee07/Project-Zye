"""
Travel Planning Intelligence Engine for Zye Personal Assistant (Day 14 & Day 30).
Generates day-by-day itineraries, transit buffers, budget breakdowns,
packing checklists, travel risk assessments, and calendar conflict checks.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from zye_personal_assistant.database import get_db_connection, init_assistant_database

logger = logging.getLogger("zye.personal_assistant.travel")

TIER_MULTIPLIERS = {
    "ECONOMY": 0.6,
    "LOW": 0.6,
    "MODERATE": 1.0,
    "PREMIUM": 2.2,
    "CUSTOM": 1.0,
}


class TravelEngine:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path
        init_assistant_database(self._db_path)

    def plan_itinerary(
        self,
        destination: str,
        days: int,
        purpose: str = "Business & Exploration",
        budget_tier: str = "Moderate",
        start_date_iso: str = "",
        check_calendar_conflicts: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive, realistic day-by-day travel plan.
        Uses Central Gemini Gateway Slot 4 when available, or deterministic offline generator.
        """
        clean_dest = destination.strip()
        if not clean_dest:
            return {
                "status": "ERROR",
                "error_code": "TRAVEL_INVALID_DESTINATION",
                "message": "Destination cannot be empty.",
            }

        if days <= 0:
            return {
                "status": "ERROR",
                "error_code": "TRAVEL_INVALID_DURATION",
                "message": f"Invalid trip duration: {days} day(s). Must be at least 1 day.",
            }

        days_count = min(days, 30)
        tier_clean = budget_tier.strip().upper()
        if tier_clean not in TIER_MULTIPLIERS:
            tier_clean = "MODERATE"

        # Check calendar conflicts if requested and start date is provided
        conflicts: list[dict[str, Any]] = []
        if check_calendar_conflicts and start_date_iso.strip():
            conflicts = self._check_calendar_conflicts(start_date_iso.strip(), days_count)

        # Try Gemini Gateway first (Slot 4: PERSONAL_ASSISTANT)
        plan_data = self._generate_with_gemini(clean_dest, days_count, purpose, tier_clean, start_date_iso)
        if not plan_data:
            # Fall back to offline deterministic itinerary
            plan_data = self._generate_offline(clean_dest, days_count, purpose, tier_clean, start_date_iso)

        if conflicts:
            plan_data["calendar_conflicts_detected"] = len(conflicts)
            plan_data["conflicting_events"] = conflicts

        # Persist to SQLite travel_plans table
        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO travel_plans (destination, days, purpose, budget_tier, itinerary_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (clean_dest, days_count, purpose, tier_clean, json.dumps(plan_data), now_str),
                )
        except Exception as e:
            logger.warning("Failed to store travel plan: %s", e)
        finally:
            conn.close()

        return plan_data

    def _check_calendar_conflicts(self, start_date_iso: str, days: int) -> list[dict[str, Any]]:
        """Inspect existing calendar events during trip window to identify conflicts."""
        conflicts: list[dict[str, Any]] = []
        try:
            start_dt = datetime.fromisoformat(start_date_iso.split("T")[0])
            end_dt = start_dt + timedelta(days=days)
            w_start = start_dt.strftime("%Y-%m-%d")
            w_end = end_dt.strftime("%Y-%m-%d")

            conn = get_db_connection(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT id, title, start_iso, end_iso, location
                    FROM events
                    WHERE event_status != 'CANCELLED'
                      AND NOT (end_iso <= ? OR start_iso >= ?);
                    """,
                    (w_start, w_end),
                ).fetchall()
                for r in rows:
                    conflicts.append({
                        "event_id": r["id"],
                        "title": r["title"],
                        "start_iso": r["start_iso"],
                        "end_iso": r["end_iso"],
                        "location": r["location"],
                    })
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Calendar conflict check failed: %s", exc)
        return conflicts

    def _generate_with_gemini(
        self, destination: str, days: int, purpose: str, budget_tier: str, start_date_iso: str = ""
    ) -> Optional[dict[str, Any]]:
        """Attempt to generate grounded itinerary via Central Gemini Gateway."""
        try:
            from gemini_gateway import ZyeGeminiGateway
            gw = ZyeGeminiGateway.get_instance()
            date_ctx = f" starting on {start_date_iso}" if start_date_iso else ""
            prompt = (
                f"Create a realistic {days}-day travel itinerary for {destination}{date_ctx}. "
                f"Purpose: {purpose}. Budget tier: {budget_tier}. "
                "Include day-by-day morning/afternoon/evening schedule with transit buffers, "
                "estimated cost breakdown (transport, lodging, food, activities, reserve), "
                "tailored packing checklist, and top travel risks with mitigations. "
                "Format strictly as valid JSON without markdown fences."
            )
            res = gw.generate_response(prompt=prompt, workload="PERSONAL_ASSISTANT")
            if res.get("status") in ("SUCCESS", "CACHED") and res.get("text"):
                raw_text = res["text"].strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                try:
                    data = json.loads(raw_text)
                    data["status"] = "SUCCESS"
                    data["destination"] = destination
                    data["days"] = days
                    data["purpose"] = purpose
                    data["budget_tier"] = budget_tier
                    data["is_live_verified"] = False
                    data["disclaimer"] = "Estimates are modeled approximations, not live bookings. Airfare and hotel rates require verified checkout."
                    data["generated_at"] = datetime.now(timezone.utc).isoformat()
                    return data
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Gemini travel generation fell back: %s", e)
        return None

    def _generate_offline(
        self, destination: str, days: int, purpose: str, budget_tier: str, start_date_iso: str = ""
    ) -> dict[str, Any]:
        """Deterministic offline itinerary generator when internet or API is unavailable."""
        mult = TIER_MULTIPLIERS.get(budget_tier, 1.0)
        base_daily_cost = 120.0 * mult

        days_schedule = []
        curr_dt = None
        if start_date_iso:
            try:
                curr_dt = datetime.fromisoformat(start_date_iso.split("T")[0])
            except Exception:
                curr_dt = None

        for d in range(1, days + 1):
            date_label = (curr_dt + timedelta(days=d - 1)).strftime("%Y-%m-%d") if curr_dt else f"Day {d}"
            if d == 1:
                title = f"{date_label}: Arrival, Check-in & Orientation in {destination}"
                morning = f"Transit arrival at {destination}, private/shuttle transfer to accommodations"
                afternoon = "Hotel check-in, orientation walk around central district, acquire local transit card"
                evening = "Welcome dinner featuring regional cuisine and schedule briefing"
            elif d == days:
                title = f"{date_label}: Wrap-up, Souvenirs & Return Journey"
                morning = "Final landmark visit or breakfast briefing, pack and hotel checkout"
                afternoon = "Light souvenir shopping in central marketplace and casual lunch"
                evening = f"Transfer to transit terminal and departure from {destination}"
            else:
                title = f"{date_label}: Core {purpose} Operations & Exploration"
                morning = f"High-energy morning activities / primary business sessions in {destination} (3-4 hours)"
                afternoon = "Secondary site exploration, local cultural visit, and structured lunch"
                evening = "Evening networking, sunset viewpoint visit, or leisure dining"

            days_schedule.append({
                "day": d,
                "date": date_label,
                "title": title,
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening,
                "transit_buffer": "30-45 minutes between distinct geographical zones",
                "estimated_duration_hours": 8.0,
                "unverified_opening_hours": ["Attractions and regional venues require local operating hours verification."],
            })

        estimated_costs = {
            "lodging_total": round(days * 75.0 * mult, 2),
            "transport_total": round(140.0 * mult + days * 20.0, 2),
            "meals_total": round(days * 40.0 * mult, 2),
            "activities_total": round(days * 25.0 * mult, 2),
            "emergency_reserve": round(days * 25.0 * mult, 2),
            "estimated_grand_total": round(days * base_daily_cost + 140.0 * mult, 2),
            "currency": "USD (Estimates modeled)",
        }

        # Tailor checklist based on purpose
        checklist = [
            "Passport / Government ID & physical/digital boarding passes",
            "Laptop, phone, high-speed charging cables, and universal power adapter",
            "Cabin-baggage approved high-capacity power bank",
            "Prescription medications and travel-size first aid",
            "Comfortable all-weather walking shoes and light rain jacket",
        ]
        if "business" in purpose.lower():
            checklist.extend(["Business attire / presentation portfolio", "Company ID & corporate cards"])
        elif "family" in purpose.lower():
            checklist.extend(["Family documentation & medical insurance cards", "Children activities / snacks for transit"])

        risks = [
            {
                "risk": "Transit delays, traffic congestion, or missed connections",
                "mitigation": "Maintain 60-90 minute buffers prior to major scheduled departures.",
                "severity": "MEDIUM",
            },
            {
                "risk": "Unverified attraction operating hours or seasonal closures",
                "mitigation": "Confirm ticket availability and opening hours online 24 hours in advance.",
                "severity": "LOW",
            },
            {
                "risk": "Unexpected local expense overruns",
                "mitigation": "Hold the dedicated 15% contingency reserve in accessible funds.",
                "severity": "LOW",
            },
            {
                "risk": "Sudden weather disruption",
                "mitigation": "Review daily weather updates each morning and maintain flexible afternoon alternatives.",
                "severity": "MEDIUM",
            },
        ]

        return {
            "status": "SUCCESS",
            "destination": destination,
            "days": days,
            "purpose": purpose,
            "budget_tier": budget_tier,
            "itinerary": days_schedule,
            "estimated_costs": estimated_costs,
            "packing_checklist": checklist,
            "risks_and_mitigation": risks,
            "is_live_verified": False,
            "disclaimer": "Estimates are modeled approximations, not live bookings. Airfare and hotel rates require verified checkout.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
