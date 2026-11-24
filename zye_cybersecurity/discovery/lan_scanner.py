"""
ZYE AI — LAN Device Discovery Engine (Day 39).
Coordinates passive ARP cache inspection and authorized active Scapy ARP probes,
enforces Npcap fallbacks, handles hostname resolution with strict timeouts,
and aggregates normalized device inventories.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from zye_cybersecurity.discovery.arp_table_parser import ArpTableParser
from zye_cybersecurity.discovery.device_deduplicator import DeviceDeduplicator
from zye_cybersecurity.discovery.device_models import (
    DeviceObservation,
    NetworkDiscoveryResult,
    NetworkInterfaceInfo,
    get_utc_iso_timestamp,
    normalize_mac_address,
)
from zye_cybersecurity.discovery.interface_discovery import NetworkInterfaceDiscovery
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer
from zye_cybersecurity.security.scan_authorizer import ScanAuthorizer

logger = logging.getLogger("zye.cybersecurity.scanner")

# Check Scapy availability
_SCAPY_AVAILABLE = False
_NPCAP_AVAILABLE = False
try:
    import scapy.all as scapy_mod
    from scapy.layers.l2 import ARP, Ether
    from scapy.sendrecv import srp
    _SCAPY_AVAILABLE = True
    # Test whether pcap provider is functional
    try:
        from scapy.arch.windows import get_windows_if_list
        # If no pcap provider, scapy logs a warning or pcap is None
        from scapy.config import conf
        if getattr(conf, "use_pcap", False) and getattr(conf, "pcap_provider", None):
            _NPCAP_AVAILABLE = True
    except Exception:
        pass
except (ImportError, Exception):
    _SCAPY_AVAILABLE = False


class LanScanner:
    """Master orchestrator for local area network device discovery."""

    def __init__(
        self,
        interface_discovery: Optional[NetworkInterfaceDiscovery] = None,
        deduplicator: Optional[DeviceDeduplicator] = None,
        authorizer: Optional[ScanAuthorizer] = None,
    ) -> None:
        self.interface_discovery = interface_discovery or NetworkInterfaceDiscovery()
        self.deduplicator = deduplicator or DeviceDeduplicator()
        self.authorizer = authorizer or ScanAuthorizer()
        self._last_scan_result: Optional[NetworkDiscoveryResult] = None

    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        """Return operational capabilities and dependency statuses."""
        return {
            "scapy_available": _SCAPY_AVAILABLE,
            "npcap_available": _NPCAP_AVAILABLE,
            "passive_arp_supported": True,
            "active_arp_supported": _SCAPY_AVAILABLE and _NPCAP_AVAILABLE,
        }

    @staticmethod
    def resolve_hostname(ip: str, timeout_seconds: float = 0.5) -> Optional[str]:
        """
        Attempt reverse DNS lookup for an IP address under strict timeout bounds.
        Returns None on timeout or resolution failure; never invents hostnames.
        """
        orig_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout_seconds)
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except Exception:
            return None
        finally:
            socket.setdefaulttimeout(orig_timeout)

    def scan_lan(
        self,
        interface_name: Optional[str] = None,
        scan_mode: str = "passive",
        subnet_cidr: Optional[str] = None,
        timeout_seconds: float = 3.0,
        include_hostname: bool = False,
        authorized: bool = False,
        mock_arp_output: Optional[str] = None,
        mock_active_responses: Optional[List[Dict[str, str]]] = None,
    ) -> NetworkDiscoveryResult:
        """
        Execute LAN discovery across authorized local subnet.
        Supports passive ARP cache discovery (default) and authorized active ARP scanning.
        """
        t0 = time.perf_counter()
        scan_id = f"scan_{uuid.uuid4().hex[:12]}"
        timestamp = get_utc_iso_timestamp()
        warnings: List[str] = []
        errors: List[str] = []

        # 1. Resolve Target Interface
        target_iface: Optional[NetworkInterfaceInfo] = None
        if interface_name:
            target_iface = self.interface_discovery.get_interface_by_name(interface_name)
            if not target_iface:
                return NetworkDiscoveryResult(
                    status="FAILED",
                    scan_id=scan_id,
                    scan_timestamp_utc=timestamp,
                    scan_mode=scan_mode.upper(),
                    network_interface={"requested_name": interface_name},
                    discovery_summary={"total_observations": 0, "active_responses": 0, "passive_entries": 0, "duplicate_entries_removed": 0},
                    devices=[],
                    errors=[f"INVALID_INTERFACE_NAME: Specified interface '{interface_name}' not found on host."],
                    execution_time_ms=(time.perf_counter() - t0) * 1000,
                )
        else:
            target_iface = self.interface_discovery.get_primary_interface()

        if not target_iface:
            return NetworkDiscoveryResult(
                status="FAILED",
                scan_id=scan_id,
                scan_timestamp_utc=timestamp,
                scan_mode=scan_mode.upper(),
                network_interface={},
                discovery_summary={"total_observations": 0, "active_responses": 0, "passive_entries": 0, "duplicate_entries_removed": 0},
                devices=[],
                errors=["NO_ACTIVE_NETWORK_INTERFACE: No active network interface detected."],
                execution_time_ms=(time.perf_counter() - t0) * 1000,
            )

        # 2. Determine and Validate Target Subnet
        actual_cidr = subnet_cidr or target_iface.cidr
        if not actual_cidr:
            if target_iface.ipv4_address and target_iface.subnet_mask:
                try:
                    cfg = SubnetAnalyzer.calculate_subnet(target_iface.ipv4_address, target_iface.subnet_mask)
                    actual_cidr = cfg.cidr
                except Exception as e:
                    errors.append(f"INVALID_SUBNET: Could not calculate CIDR: {e}")
            else:
                errors.append(f"NO_IPV4_CONFIGURATION: Interface '{target_iface.name}' has no IPv4 configuration.")

        if errors:
            return NetworkDiscoveryResult(
                status="FAILED",
                scan_id=scan_id,
                scan_timestamp_utc=timestamp,
                scan_mode=scan_mode.upper(),
                network_interface=target_iface.to_dict(),
                discovery_summary={"total_observations": 0, "active_responses": 0, "passive_entries": 0, "duplicate_entries_removed": 0},
                devices=[],
                errors=errors,
                execution_time_ms=(time.perf_counter() - t0) * 1000,
            )

        raw_observations: List[DeviceObservation] = []
        mode = scan_mode.strip().lower()

        # 3. Passive ARP Discovery (Always attempted or as base)
        passive_entries: List[DeviceObservation] = []
        if mock_arp_output is not None:
            passive_entries = ArpTableParser.parse_arp_a_output(
                mock_arp_output,
                target_interface_ip=None,
                default_iface_name=target_iface.name,
            )
        else:
            passive_entries = ArpTableParser.get_live_arp_table(
                target_interface_ip=target_iface.ipv4_address,
                target_iface_alias=target_iface.name,
            )

        raw_observations.extend(passive_entries)

        # 4. Active Scan Handling
        active_count = 0
        if mode == "active":
            # Security Scope & Authorization Verification
            is_auth, auth_err = self.authorizer.authorize_active_scan(
                target_cidr=actual_cidr,  # type: ignore[arg-type]
                interface=target_iface,
                authorized=authorized,
            )
            if not is_auth:
                errors.append(auth_err or "ACTIVE_SCAN_NOT_AUTHORIZED")
                return NetworkDiscoveryResult(
                    status="FAILED",
                    scan_id=scan_id,
                    scan_timestamp_utc=timestamp,
                    scan_mode="ACTIVE",
                    network_interface=target_iface.to_dict(),
                    discovery_summary={"total_observations": 0, "active_responses": 0, "passive_entries": 0, "duplicate_entries_removed": 0},
                    devices=[],
                    errors=errors,
                    execution_time_ms=(time.perf_counter() - t0) * 1000,
                )

            # Check Npcap / Scapy capability
            if mock_active_responses is not None:
                # Use test mock responses
                for resp in mock_active_responses:
                    raw_observations.append(
                        DeviceObservation(
                            ip_address=resp["ip"],
                            mac_address=normalize_mac_address(resp["mac"]),
                            interface_name=target_iface.name,
                            neighbor_state="Reachable",
                            discovery_method="SCAPY_ACTIVE_ARP",
                            observation_status="ACTIVE_RESPONSE_OBSERVED",
                            confidence=1.0,
                        )
                    )
                    active_count += 1
            elif not _SCAPY_AVAILABLE:
                warnings.append("SCAPY_UNAVAILABLE: Scapy package not available. Fell back to passive ARP table discovery.")
            elif not _NPCAP_AVAILABLE:
                warnings.append("NPCAP_UNAVAILABLE: Npcap packet capture driver not installed on Windows host. Active ARP packet injection unavailable; fell back to passive ARP table discovery.")
            else:
                # Perform live Scapy ARP scan
                try:
                    active_obs = self._execute_scapy_arp_scan(actual_cidr, target_iface, timeout_seconds)  # type: ignore[arg-type]
                    raw_observations.extend(active_obs)
                    active_count += len(active_obs)
                except Exception as e:
                    logger.warning("Scapy active ARP scan failed: %s", e)
                    warnings.append(f"ACTIVE_SCAN_EXECUTION_ERROR: {e}. Fell back to passive ARP observations.")

        # 5. Deduplication & Historical Tracking
        deduped = self.deduplicator.deduplicate(raw_observations, track_history=True)

        # 6. Optional Hostname Enrichment
        if include_hostname:
            for d in deduped:
                if not d.hostname:
                    d.hostname = self.resolve_hostname(d.ip_address)

        total_obs = len(raw_observations)
        duplicates_removed = max(0, total_obs - len(deduped))
        passive_count = max(0, len(deduped) - active_count)

        result = NetworkDiscoveryResult(
            status="SCAN_COMPLETED",
            scan_id=scan_id,
            scan_timestamp_utc=timestamp,
            scan_mode=mode.upper(),
            network_interface={
                "name": target_iface.name,
                "local_ip": target_iface.ipv4_address,
                "subnet": actual_cidr,
                "gateway": target_iface.default_gateway,
                "mac_address": target_iface.mac_address,
                "adapter_type": target_iface.adapter_type,
            },
            discovery_summary={
                "total_observations": len(deduped),
                "active_responses": active_count,
                "passive_entries": passive_count,
                "duplicate_entries_removed": duplicates_removed,
            },
            devices=[d.to_dict() for d in deduped],
            warnings=warnings,
            errors=errors,
            execution_time_ms=(time.perf_counter() - t0) * 1000,
        )

        self._last_scan_result = result
        return result

    def _execute_scapy_arp_scan(
        self,
        target_cidr: str,
        iface: NetworkInterfaceInfo,
        timeout: float,
    ) -> List[DeviceObservation]:
        """Execute Scapy broadcast ARP request across subnet."""
        observations: List[DeviceObservation] = []
        timestamp = get_utc_iso_timestamp()

        try:
            # Construct ARP broadcast
            arp_req = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=target_cidr)
            # Send and receive packets with bounded timeout
            ans, _ = srp(arp_req, timeout=timeout, verbose=0, retry=1)
            for snd, rcv in ans:
                ip = rcv.psrc
                mac = normalize_mac_address(rcv.hwsrc)
                if ArpTableParser.is_valid_device_entry(ip, mac):
                    observations.append(
                        DeviceObservation(
                            ip_address=ip,
                            mac_address=mac,
                            interface_name=iface.name,
                            neighbor_state="Reachable",
                            discovery_method="SCAPY_ACTIVE_ARP",
                            observation_status="ACTIVE_RESPONSE_OBSERVED",
                            confidence=1.0,
                            first_seen=timestamp,
                            last_seen=timestamp,
                        )
                    )
        except Exception as e:
            logger.error("Error in Scapy ARP probe: %s", e)
            raise

        return observations

    def get_last_scan_status(self) -> Dict[str, Any]:
        """Return diagnostic status of the last executed scan."""
        caps = self.get_capabilities()
        if not self._last_scan_result:
            return {
                "scan_status": "IDLE",
                "last_scan_timestamp": None,
                "selected_interface": None,
                "scan_mode": None,
                "discovered_device_count": 0,
                "capabilities": caps,
                "last_error": None,
                "performance_ms": 0.0,
            }

        return {
            "scan_status": self._last_scan_result.status,
            "last_scan_timestamp": self._last_scan_result.scan_timestamp_utc,
            "selected_interface": self._last_scan_result.network_interface.get("name"),
            "scan_mode": self._last_scan_result.scan_mode,
            "discovered_device_count": len(self._last_scan_result.devices),
            "capabilities": caps,
            "last_error": self._last_scan_result.errors[0] if self._last_scan_result.errors else None,
            "warnings": self._last_scan_result.warnings,
            "performance_ms": self._last_scan_result.execution_time_ms,
        }
