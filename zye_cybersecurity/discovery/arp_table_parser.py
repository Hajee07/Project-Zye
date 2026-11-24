"""
ZYE AI — Windows ARP & Neighbor Table Parser (Day 39).
Parses Get-NetNeighbor and arp -a output, filters multicast/broadcast,
normalizes MAC addresses, interprets neighbor states, and extracts device observations.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict, List, Optional, Set

from zye_cybersecurity.discovery.device_models import (
    DeviceObservation,
    generate_device_id,
    get_utc_iso_timestamp,
    normalize_mac_address,
)
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer

logger = logging.getLogger("zye.cybersecurity.arp")

# Invalid MAC addresses to filter out
INVALID_MACS: Set[str] = {
    "FF:FF:FF:FF:FF:FF",
    "00:00:00:00:00:00",
    "UNKNOWN_MAC",
}


class ArpTableParser:
    """Parses local ARP caches and Windows neighbor tables into normalized observations."""

    @staticmethod
    def is_valid_device_entry(ip: str, mac: str) -> bool:
        """
        Validate whether an IP and MAC entry represents a legitimate unicast device.
        Rejects multicast, broadcast, loopback, and reserved MACs.
        """
        norm_mac = normalize_mac_address(mac)
        if norm_mac in INVALID_MACS or len(norm_mac) != 17:
            return False

        if SubnetAnalyzer.is_multicast_or_broadcast(ip):
            return False

        if ip.startswith("127.") or ip == "0.0.0.0":
            return False

        return True

    @staticmethod
    def map_neighbor_state_to_status(state: str) -> tuple[str, float]:
        """
        Map Windows neighbor state string to observation status and confidence score.
        Returns (observation_status, confidence).
        """
        s = state.strip().upper()
        if s == "REACHABLE":
            return "PASSIVE_ARP_OBSERVED", 0.70
        if s == "PERMANENT":
            return "PASSIVE_ARP_OBSERVED", 0.60
        if s in ("DELAY", "PROBE"):
            return "PASSIVE_ARP_OBSERVED", 0.50
        if s == "STALE":
            return "STALE_NEIGHBOR_ENTRY", 0.40
        if s in ("INCOMPLETE", "UNREACHABLE"):
            return "UNRESOLVED", 0.20
        return "PASSIVE_ARP_OBSERVED", 0.45

    @classmethod
    def parse_arp_a_output(
        cls,
        output_text: str,
        target_interface_ip: Optional[str] = None,
        default_iface_name: str = "Wi-Fi",
    ) -> List[DeviceObservation]:
        """
        Parse standard Windows 'arp -a' output.
        Format:
          Interface: 10.93.34.248 --- 0x14
            Internet Address      Physical Address      Type
            10.93.34.1            50-2e-91-cb-ce-51     dynamic
            10.93.34.255          ff-ff-ff-ff-ff-ff     static
        """
        observations: List[DeviceObservation] = []
        if not output_text:
            return observations

        current_iface_ip: Optional[str] = None
        current_iface_name = default_iface_name
        timestamp = get_utc_iso_timestamp()

        # Regex for Interface header: Interface: 10.93.34.248 --- 0x14
        iface_regex = re.compile(r"Interface:\s*([0-9.]+)\s*---\s*(0x[0-9a-fA-F]+|\d+)", re.IGNORECASE)
        # Regex for ARP entry: 10.93.34.1 50-2e-91-cb-ce-51 dynamic
        entry_regex = re.compile(
            r"^\s*([0-9.]+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})\s+(\w+)",
            re.IGNORECASE,
        )

        for line in output_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            iface_match = iface_regex.search(line_str)
            if iface_match:
                current_iface_ip = iface_match.group(1).strip()
                current_iface_name = f"if_{current_iface_ip}"
                continue

            # If target interface IP specified, skip lines from other interfaces
            if target_interface_ip and current_iface_ip and current_iface_ip != target_interface_ip:
                continue

            entry_match = entry_regex.match(line_str)
            if entry_match:
                ip = entry_match.group(1).strip()
                raw_mac = entry_match.group(2).strip()
                entry_type = entry_match.group(3).strip().lower()

                if not cls.is_valid_device_entry(ip, raw_mac):
                    continue

                norm_mac = normalize_mac_address(raw_mac)
                state = "Reachable" if entry_type == "dynamic" else "Permanent"
                status, confidence = cls.map_neighbor_state_to_status(state)

                obs = DeviceObservation(
                    ip_address=ip,
                    mac_address=norm_mac,
                    interface_name=current_iface_name,
                    neighbor_state=state,
                    discovery_method="WINDOWS_ARP_TABLE",
                    first_seen=timestamp,
                    last_seen=timestamp,
                    observation_status=status,
                    confidence=confidence,
                )
                observations.append(obs)

        return observations

    @classmethod
    def parse_net_neighbor_output(
        cls,
        output_text: str,
        target_iface_alias: Optional[str] = None,
    ) -> List[DeviceObservation]:
        """
        Parse Windows PowerShell Get-NetNeighbor output.
        Format:
          IPAddress        : 10.93.34.1
          LinkLayerAddress : 50-2E-91-CB-CE-51
          State            : Reachable
          InterfaceAlias   : Wi-Fi
          InterfaceIndex   : 20
        """
        observations: List[DeviceObservation] = []
        if not output_text:
            return observations

        timestamp = get_utc_iso_timestamp()
        # Split on blocks separated by blank lines or headers
        blocks = re.split(r"\n\s*\n", output_text.strip())

        for block in blocks:
            ip: Optional[str] = None
            mac: Optional[str] = None
            state = "UNKNOWN"
            iface_alias = "UNKNOWN"
            iface_idx: Optional[int] = None

            for line in block.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                key = k.strip().lower()
                val = v.strip()

                if key == "ipaddress":
                    ip = val
                elif key == "linklayeraddress":
                    mac = val
                elif key == "state":
                    state = val
                elif key == "interfacealias":
                    iface_alias = val
                elif key == "interfaceindex":
                    try:
                        iface_idx = int(val)
                    except ValueError:
                        pass

            if not ip or not mac:
                continue

            if target_iface_alias and iface_alias.lower() != target_iface_alias.lower():
                continue

            if not cls.is_valid_device_entry(ip, mac):
                continue

            norm_mac = normalize_mac_address(mac)
            status, confidence = cls.map_neighbor_state_to_status(state)

            obs = DeviceObservation(
                ip_address=ip,
                mac_address=norm_mac,
                interface_name=iface_alias,
                interface_index=iface_idx,
                neighbor_state=state,
                discovery_method="WINDOWS_NET_NEIGHBOR",
                first_seen=timestamp,
                last_seen=timestamp,
                observation_status=status,
                confidence=confidence,
            )
            observations.append(obs)

        return observations

    @classmethod
    def get_live_arp_table(
        cls,
        target_interface_ip: Optional[str] = None,
        target_iface_alias: Optional[str] = None,
    ) -> List[DeviceObservation]:
        """
        Retrieve live ARP cache entries from Windows host.
        Tries arp -a first (sub-millisecond native utility); falls back to Get-NetNeighbor.
        """
        # 1. Try fast native arp -a
        try:
            res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=1.5, check=False)
            if res.returncode == 0 and res.stdout.strip():
                entries = cls.parse_arp_a_output(
                    res.stdout,
                    target_interface_ip=target_interface_ip,
                    default_iface_name=target_iface_alias or "Wi-Fi",
                )
                if entries:
                    return entries
        except Exception as e:
            logger.debug("arp -a fast query failed: %s", e)

        # 2. Fallback to PowerShell Get-NetNeighbor
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-NetNeighbor -AddressFamily IPv4 | Format-List IPAddress, LinkLayerAddress, State, InterfaceAlias, InterfaceIndex"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return cls.parse_net_neighbor_output(res.stdout, target_iface_alias=target_iface_alias)
        except Exception as e:
            logger.debug("Get-NetNeighbor query unavailable: %s", e)

        return []
