"""
ZYE AI — Windows Event XML Parser (Day 40).
Parses raw Windows Event XML output from Get-WinEvent, safely handles XML namespaces,
extracts System and EventData elements, and constructs NormalizedAuthEvent instances.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from zye_cybersecurity.authentication.auth_models import (
    NormalizedAuthEvent,
    get_utc_iso_timestamp,
)
from zye_cybersecurity.authentication.logon_type_analyzer import LogonTypeAnalyzer
from zye_cybersecurity.authentication.status_code_analyzer import StatusCodeAnalyzer

logger = logging.getLogger("zye.cybersecurity.xml_parser")

XML_NS = {
    "e": "http://schemas.microsoft.com/win/2004/08/events/event",
}


class EventXmlParserError(ValueError):
    """Raised when XML parsing encounters malformed or unrecoverable event structures."""
    pass


class EventXmlParser:
    """Namespace-safe parser for Windows Event XML documents."""

    @staticmethod
    def _clean_field_value(val: Optional[str]) -> Optional[str]:
        """Convert placeholder values ('-', '', whitespace) to None."""
        if val is None:
            return None
        cleaned = val.strip()
        if cleaned in ("-", "", "%%0"):
            return None
        return cleaned

    @staticmethod
    def parse_timestamp_to_utc(ts_str: Optional[str]) -> str:
        """
        Normalize Windows System TimeCreated SystemTime string to UTC ISO 8601.
        Accepts ISO formats (e.g. '2026-11-22T10:00:00.0000000Z').
        """
        if not ts_str:
            return get_utc_iso_timestamp()

        cleaned = ts_str.strip()
        try:
            if cleaned.endswith("Z"):
                dt = datetime.fromisoformat(cleaned[:-1] + "+00:00")
            elif "+" in cleaned or "-" in cleaned[10:]:
                dt = datetime.fromisoformat(cleaned)
            else:
                dt = datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return get_utc_iso_timestamp()

    @classmethod
    def parse_single_event_xml(cls, xml_text: str) -> NormalizedAuthEvent:
        """
        Parse a single <Event xmlns="..."> XML string into a NormalizedAuthEvent.
        """
        if not xml_text or not xml_text.strip():
            raise EventXmlParserError("INVALID_EVENT_XML: XML string is empty.")

        try:
            root = ET.fromstring(xml_text.strip())
        except Exception as e:
            raise EventXmlParserError(f"INVALID_EVENT_XML: XML syntax error: {e}") from e

        def _find(elem: ET.Element, tag: str) -> Optional[ET.Element]:
            res = elem.find(f"e:{tag}", XML_NS)
            if res is None:
                res = elem.find(tag)
            return res

        system = _find(root, "System")
        event_id = 4625
        event_record_id: Optional[int] = None
        timestamp_utc = get_utc_iso_timestamp()
        computer = "LOCAL_COMPUTER"
        channel = "Security"
        provider_name = "Microsoft-Windows-Security-Auditing"

        if system is not None:
            eid_elem = _find(system, "EventID")
            if eid_elem is not None and eid_elem.text:
                try:
                    event_id = int(eid_elem.text.strip())
                except ValueError:
                    pass

            time_elem = _find(system, "TimeCreated")
            if time_elem is not None:
                raw_time = time_elem.attrib.get("SystemTime")
                timestamp_utc = cls.parse_timestamp_to_utc(raw_time)

            rec_elem = _find(system, "EventRecordID")
            if rec_elem is not None and rec_elem.text:
                try:
                    event_record_id = int(rec_elem.text.strip())
                except ValueError:
                    pass

            comp_elem = _find(system, "Computer")
            if comp_elem is not None and comp_elem.text:
                computer = comp_elem.text.strip()

            chan_elem = _find(system, "Channel")
            if chan_elem is not None and chan_elem.text:
                channel = chan_elem.text.strip()

            prov_elem = _find(system, "Provider")
            if prov_elem is not None and "Name" in prov_elem.attrib:
                provider_name = prov_elem.attrib["Name"]

        event_data: Dict[str, str] = {}
        ed_block = _find(root, "EventData")
        if ed_block is not None:
            data_elements = ed_block.findall("e:Data", XML_NS)
            if not data_elements:
                data_elements = ed_block.findall("Data")

            for d in data_elements:
                name = d.attrib.get("Name")
                val = d.text if d.text is not None else ""
                if name:
                    event_data[name] = val

        target_username = cls._clean_field_value(event_data.get("TargetUserName"))
        target_domain = cls._clean_field_value(event_data.get("TargetDomainName"))
        target_sid = cls._clean_field_value(event_data.get("TargetUserSid"))
        subject_username = cls._clean_field_value(event_data.get("SubjectUserName"))
        source_ip = cls._clean_field_value(event_data.get("IpAddress"))
        workstation_name = cls._clean_field_value(event_data.get("WorkstationName"))
        logon_process_name = cls._clean_field_value(event_data.get("LogonProcessName"))
        auth_package = cls._clean_field_value(event_data.get("AuthenticationPackageName"))
        status = StatusCodeAnalyzer.normalize_hex_code(event_data.get("Status"))
        sub_status = StatusCodeAnalyzer.normalize_hex_code(event_data.get("SubStatus"))
        process_name = cls._clean_field_value(event_data.get("ProcessName"))

        source_port: Optional[int] = None
        raw_port = cls._clean_field_value(event_data.get("IpPort"))
        if raw_port:
            try:
                source_port = int(raw_port)
            except ValueError:
                pass

        process_id: Optional[int] = None
        raw_pid = cls._clean_field_value(event_data.get("ProcessId"))
        if raw_pid:
            try:
                process_id = int(raw_pid, 16 if raw_pid.startswith("0x") else 10)
            except ValueError:
                pass

        logon_type: Optional[int] = None
        raw_lt = cls._clean_field_value(event_data.get("LogonType"))
        if raw_lt:
            try:
                logon_type = int(raw_lt)
            except ValueError:
                pass

        lt_info = LogonTypeAnalyzer.get_logon_type_info(logon_type)
        logon_type_name = lt_info.name
        status_info = StatusCodeAnalyzer.get_status_info(status)
        sub_status_info = StatusCodeAnalyzer.get_status_info(sub_status)
        failure_reason = StatusCodeAnalyzer.determine_failure_reason(status, sub_status)

        return NormalizedAuthEvent(
            event_id=event_id,
            event_record_id=event_record_id,
            timestamp_utc=timestamp_utc,
            computer=computer,
            channel=channel,
            provider_name=provider_name,
            target_username=target_username,
            target_domain=target_domain,
            target_sid=target_sid,
            subject_username=subject_username,
            source_ip=source_ip,
            source_port=source_port,
            workstation_name=workstation_name,
            logon_type=logon_type,
            logon_type_name=logon_type_name,
            logon_process_name=logon_process_name,
            authentication_package=auth_package,
            status=status,
            sub_status=sub_status,
            status_description=status_info.description,
            sub_status_description=sub_status_info.description,
            failure_reason=failure_reason,
            process_id=process_id,
            process_name=process_name,
            event_source="WINDOWS_SECURITY_LOG",
            raw_data=event_data,
        )

    def parse_event_xml(self, xml_text: str) -> Optional[NormalizedAuthEvent]:
        """Parse single XML text returning None gracefully on error."""
        try:
            return self.parse_single_event_xml(xml_text)
        except Exception as e:
            logger.debug("Failed parsing XML: %s", e)
            return None

    def parse_event_batch(self, xml_list: List[str]) -> List[NormalizedAuthEvent]:
        """Parse batch of XML strings, deduplicating by event_record_id."""
        seen_ids = set()
        events: List[NormalizedAuthEvent] = []
        for xml_str in xml_list:
            ev = self.parse_event_xml(xml_str)
            if ev is not None:
                if ev.event_record_id is not None:
                    if ev.event_record_id in seen_ids:
                        continue
                    seen_ids.add(ev.event_record_id)
                events.append(ev)
        return events

    @classmethod
    def parse_multiple_events_xml(cls, multi_xml_text: str) -> List[NormalizedAuthEvent]:
        """Parse multi-event XML stream or concatenated <Event>...</Event> blocks."""
        events: List[NormalizedAuthEvent] = []
        if not multi_xml_text or not multi_xml_text.strip():
            return events

        matches = re.findall(r"(<Event\b.*?</Event>)", multi_xml_text, re.DOTALL | re.IGNORECASE)
        if matches:
            for xml_block in matches:
                try:
                    ev = cls.parse_single_event_xml(xml_block)
                    events.append(ev)
                except Exception as e:
                    logger.warning("Skipping malformed event XML block: %s", e)
        else:
            try:
                events.append(cls.parse_single_event_xml(multi_xml_text))
            except Exception as e:
                logger.warning("Failed parsing single XML block: %s", e)

        return events
