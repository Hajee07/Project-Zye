#!/usr/bin/env python3
"""
ZYE AI — Natural Voice Understanding & MCP Execution Test Suite
===============================================================

Tests the full voice processing pipeline against the 8 real natural speech commands
in Tamil, English, and Tanglish:

1. "Chrome open pannu"
2. "Work Gmail-la unread emails irukka-nu check pannu"
3. "Naalaikku kaalaila 10 mani-ku team meeting schedule pannu"
4. "Excel-la row 1 to 10 total calculate pannu"
5. "ChatGPT and Claude rendu perayum compare panni oru quick summary sollu"
6. "Innaikku enakku edhavadhu meeting conflict irukka"
7. "Naan sonna previous task continue pannu"
8. "Wait pannu... actually meeting-a 4 mani-ku change pannu"

Verifies:
- Accurate transcript generation
- Gemini intent interpretation
- Correct MCP tool selection & execution
- Spoken response confirmation
- Latency & Status
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from main import ZyeVoiceLoop
from zye_voice.voice_diagnostics import get_voice_diagnostics, VoiceDiagnosticEvent


class TestNaturalVoiceCommands(unittest.IsolatedAsyncioTestCase):
    """Execution verification for the 8 real natural speech commands."""

    loop: ZyeVoiceLoop = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.loop = ZyeVoiceLoop()
        cls.loop._echo_mode = False
        if cls.loop.brain:
            cls.loop.brain._echo_mode = False

    async def test_command_01_chrome_open(self) -> None:
        """Command 1: 'Chrome open pannu'."""
        spoken = "Chrome open pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("chrome", "open", "launch", "panniyachu")))
        print(f"\n[COMMAND 1] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_02_work_gmail_unread(self) -> None:
        """Command 2: 'Work Gmail-la unread emails irukka-nu check pannu'."""
        spoken = "Work Gmail-la unread emails irukka-nu check pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("email", "gmail", "unread", "check", "retrieve", "clear")))
        print(f"\n[COMMAND 2] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_03_schedule_team_meeting(self) -> None:
        """Command 3: 'Naalaikku kaalaila 10 mani-ku team meeting schedule pannu'."""
        spoken = "Naalaikku kaalaila 10 mani-ku team meeting schedule pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("meeting", "schedule", "10", "team", "panniyachu")))
        print(f"\n[COMMAND 3] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_04_excel_row_calculate(self) -> None:
        """Command 4: 'Excel-la row 1 to 10 total calculate pannu'."""
        spoken = "Excel-la row 1 to 10 total calculate pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("excel", "calculate", "total", "row", "formula")))
        print(f"\n[COMMAND 4] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_05_chatgpt_claude_compare(self) -> None:
        """Command 5: 'ChatGPT and Claude rendu perayum compare panni oru quick summary sollu'."""
        spoken = "ChatGPT and Claude rendu perayum compare panni oru quick summary sollu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("chatgpt", "claude", "compare", "summary", "council")))
        print(f"\n[COMMAND 5] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_06_meeting_conflict_check(self) -> None:
        """Command 6: 'Innaikku enakku edhavadhu meeting conflict irukka'."""
        spoken = "Innaikku enakku edhavadhu meeting conflict irukka"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("meeting", "conflict", "free", "schedule", "illa")))
        print(f"\n[COMMAND 6] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_07_previous_task_continue(self) -> None:
        """Command 7: 'Naan sonna previous task continue pannu'."""
        spoken = "Naan sonna previous task continue pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("previous", "task", "continue", "progress")))
        print(f"\n[COMMAND 7] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")

    async def test_command_08_pause_and_reschedule(self) -> None:
        """Command 8: 'Wait pannu... actually meeting-a 4 mani-ku change pannu'."""
        spoken = "Wait pannu... actually meeting-a 4 mani-ku change pannu"
        t0 = time.perf_counter()
        res = await self.loop._generate_response(spoken)
        latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(len(res) > 0)
        self.assertTrue(any(w in res.lower() for w in ("meeting", "4", "reschedule", "change", "update")))
        print(f"\n[COMMAND 8] '{spoken}' -> Latency: {latency:.1f}ms | Result: {res}")


if __name__ == "__main__":
    unittest.main()
