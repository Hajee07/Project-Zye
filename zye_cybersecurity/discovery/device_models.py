"""
ZYE AI — Device Models & Network Discovery Data Structures (Day 39).
Provides normalized data classes and schemas for network interfaces,
subnet configurations, device observations, and discovery outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, List, Optional, Tuple


def get_utc_iso_timestamp() -> str:
    """Return the current UTC timestamp formatted as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def normalize_mac_address(mac: Optional[str]) -> str:
    """
    Normalize MAC address to uppercase colon-separated format (AA:BB:CC:DD:EE:FF).
    Returns UNKNOWN_MAC if input is empty or invalid.
    """
    if not mac or not isinstance(mac, str):
        return "UNKNOWN_MAC"
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    if len(cleaned) == 12:
        return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))
    return mac.upper()


def generate_device_id(mac: str, ip: str, iface: str) -> str:
    """Generate a deterministic device observation ID."""
    norm_mac = normalize_mac_address(mac)
    raw = f"{norm_mac}|{ip}|{iface}"
    return f"dev_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


@dataclass
class DeviceObservation:
    """Normalized observation record for a single network device."""
    ip_address: str
    mac_address: str
    interface_name: str
    device_id: str = ""
    hostname: Optional[str] = None
    vendor: Optional[str] = "UNKNOWN_VENDOR"
    interface_index: Optional[int] = None
    neighbor_state: str = "UNKNOWN"
    discovery_method: str = "WINDOWS_ARP_TABLE"
    first_seen: Optional[str] = None
    last_seen: str = field(default_factory=get_utc_iso_timestamp)
    observation_count: int = 1
    observation_status: str = "PASSIVE_ARP_OBSERVED"
    confidence: float = 0.50
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mac_address = normalize_mac_address(self.mac_address)
        if not self.device_id:
            self.device_id = generate_device_id(self.mac_address, self.ip_address, self.interface_name)
        if not self.first_seen:
            self.first_seen = self.last_seen

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkInterfaceInfo:
    """Normalized representation of a physical or virtual network interface."""
    name: str
    description: Optional[str] = None
    adapter_type: str = "UNKNOWN"  # WIFI, ETHERNET, VIRTUAL, VPN, LOOPBACK, UNKNOWN
    is_up: bool = False
    operational_status: str = "UNKNOWN"  # UP, DOWN, UNKNOWN
    is_physical: bool = True
    ipv4_address: Optional[str] = None
    ipv6_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    cidr: Optional[str] = None
    broadcast_address: Optional[str] = None
    mac_address: Optional[str] = None
    speed_mbps: int = 0
    mtu: int = 1500
    default_gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    interface_index: Optional[int] = None
    metric: Optional[int] = None

    def __post_init__(self) -> None:
        if self.mac_address:
            self.mac_address = normalize_mac_address(self.mac_address)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SubnetConfiguration:
    """Validated network configuration for an active interface."""
    local_ip: str
    subnet_mask: str
    cidr: str
    network_address: str
    broadcast_address: str
    default_gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    interface_mac: Optional[str] = None
    total_hosts: int = 0
    usable_hosts_range: Tuple[str, str] = ("", "")
    is_private: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkDiscoveryResult:
    """Structured result returned by LAN discovery MCP tools."""
    status: str
    scan_id: str
    scan_timestamp_utc: str
    scan_mode: str
    network_interface: dict[str, Any]
    discovery_summary: dict[str, Any]
    devices: List[dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
