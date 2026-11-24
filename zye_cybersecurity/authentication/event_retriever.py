"""
ZYE AI — Windows Security Event Retriever (Day 40).
Executes bounded PowerShell Get-WinEvent queries against the Windows Security log,
supports deterministic mock provider injection, and handles access restrictions safely.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from zye_cybersecurity.authentication.auth_models import NormalizedAuthEvent
from zye_cybersecurity.authentication.event_xml_parser import EventXmlParser

logger = logging.getLogger("zye.cybersecurity.event_retriever")


class RetrievalStatus:
    SUCCESS = "SUCCESS"
    NO_EVENTS = "NO_EVENTS_FOUND"
    NO_EVENTS_FOUND = "NO_EVENTS_FOUND"
    ACCESS_DENIED = "SECURITY_LOG_ACCESS_DENIED"
    SECURITY_LOG_ACCESS_DENIED = "SECURITY_LOG_ACCESS_DENIED"
    AUDIT_POLICY_DISABLED = "AUDIT_POLICY_DISABLED"
    TIMEOUT = "EVENT_QUERY_TIMEOUT"
    EVENT_QUERY_TIMEOUT = "EVENT_QUERY_TIMEOUT"
    QUERY_FAILED = "EVENT_QUERY_FAILED"
    EVENT_QUERY_FAILED = "EVENT_QUERY_FAILED"


# Mock provider signature: Callable[[int, int], Tuple[str, List[Any], Optional[str]]]
_MOCK_PROVIDER: Optional[Callable[[int, int], Tuple[str, List[Any], Optional[str]]]] = None


class EventRetriever:
    """Retrieves Event ID 4625 records from Windows Security log or injected mock provider."""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    @classmethod
    def set_mock_provider(
        cls,
        provider: Callable[[int, int], Tuple[str, List[Any], Optional[str]]],
    ) -> None:
        """Inject a deterministic mock event provider for tests and diagnostics."""
        global _MOCK_PROVIDER
        _MOCK_PROVIDER = provider

    @classmethod
    def reset_mock_provider(cls) -> None:
        """Clear mock provider and restore live Windows EventLog retrieval."""
        global _MOCK_PROVIDER
        _MOCK_PROVIDER = None

    def retrieve_raw_events(
        self,
        minutes: int = 60,
        max_events: int = 500,
    ) -> Tuple[str, List[Any], str]:
        """Instance method for raw event retrieval."""
        return self.__class__.fetch_failed_logon_events_raw(minutes, max_events, self.timeout_seconds)

    @classmethod
    def fetch_failed_logon_events_raw(
        cls,
        time_window_minutes: int = 60,
        max_events: int = 500,
        timeout_seconds: float = 5.0,
    ) -> Tuple[str, List[Any], str]:
        """Fetch raw events (either XML strings or parsed events) with error message."""
        if _MOCK_PROVIDER is not None:
            try:
                res = _MOCK_PROVIDER(time_window_minutes, max_events)
                status = res[0]
                evs = res[1] if len(res) > 1 else []
                err = res[2] if len(res) > 2 and res[2] is not None else ""
                return status, evs, err
            except Exception as e:
                return RetrievalStatus.QUERY_FAILED, [], f"Mock provider error: {e}"

        status, evs, err = cls.fetch_failed_logon_events(time_window_minutes, max_events, timeout_seconds)
        return status, evs, err or ""

    @classmethod
    def fetch_failed_logon_events(
        cls,
        time_window_minutes: int = 60,
        max_events: int = 500,
        timeout_seconds: float = 5.0,
    ) -> Tuple[str, List[NormalizedAuthEvent], Optional[str]]:
        """
        Query Windows Security Event Log for Event ID 4625 records within time_window_minutes.
        Returns (status, events_list, error_message).
        """
        # 1. Check Mock Provider
        if _MOCK_PROVIDER is not None:
            try:
                res = _MOCK_PROVIDER(time_window_minutes, max_events)
                status = res[0]
                raw_list = res[1] if len(res) > 1 else []
                err = res[2] if len(res) > 2 else None
                # If mock provider returned XML strings, parse them
                parsed_events: List[NormalizedAuthEvent] = []
                parser = EventXmlParser()
                for item in raw_list:
                    if isinstance(item, str):
                        ev = parser.parse_event_xml(item)
                        if ev is not None:
                            parsed_events.append(ev)
                    elif isinstance(item, NormalizedAuthEvent):
                        parsed_events.append(item)
                return status, parsed_events, err
            except Exception as e:
                return RetrievalStatus.QUERY_FAILED, [], f"Mock provider error: {e}"

        # 2. Construct Bounded PowerShell Command
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $startTime = (Get-Date).AddMinutes(-{time_window_minutes})
    $events = Get-WinEvent -FilterHashtable @{{LogName='Security'; Id=4625; StartTime=$startTime}} -MaxEvents {max_events}
    foreach ($e in $events) {{
        $e.ToXml()
    }}
}} catch {{
    Write-Output "ERROR: $($_.Exception.Message)"
}}
"""

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Windows EventLog query timed out after %s seconds", timeout_seconds)
            return RetrievalStatus.TIMEOUT, [], f"EVENT_QUERY_TIMEOUT: Security event query timed out after {timeout_seconds}s"
        except Exception as e:
            logger.error("Failed to execute PowerShell event query: %s", e)
            return RetrievalStatus.QUERY_FAILED, [], f"EVENT_QUERY_FAILED: {e}"

        stdout = (res.stdout or "").strip()
        stderr = (res.stderr or "").strip()

        combined_err = f"{stdout}\n{stderr}".lower()

        if "no events were found that match the specified selection criteria" in combined_err:
            return RetrievalStatus.NO_EVENTS_FOUND, [], None

        if any(k in combined_err for k in ["access is denied", "unauthorized operation", "requires elevation"]):
            return (
                RetrievalStatus.SECURITY_LOG_ACCESS_DENIED,
                [],
                "SECURITY_LOG_ACCESS_DENIED: Access to the Windows Security event log requires administrative privileges.",
            )

        if any(k in combined_err for k in ["log was not found", "audit policy", "provider could not be found"]):
            return (
                RetrievalStatus.AUDIT_POLICY_DISABLED,
                [],
                "AUDIT_POLICY_DISABLED: Windows Logon/Logoff auditing policy may be disabled or unconfigured.",
            )

        if not stdout:
            return RetrievalStatus.NO_EVENTS_FOUND, [], None

        # Parse output XML
        events = EventXmlParser.parse_multiple_events_xml(stdout)
        if events:
            return RetrievalStatus.SUCCESS, events, None

        if "error:" in combined_err:
            return RetrievalStatus.QUERY_FAILED, [], f"EVENT_QUERY_FAILED: {stdout}"

        return RetrievalStatus.NO_EVENTS_FOUND, [], None
