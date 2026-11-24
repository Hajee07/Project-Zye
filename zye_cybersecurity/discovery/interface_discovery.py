"""
ZYE AI — Network Interface Discovery Engine (Day 39).
Identifies physical and virtual adapters using psutil and Windows route tables,
distinguishes Wi-Fi, Ethernet, VPN, Virtual, and Loopback interfaces,
determines default routes, and retrieves hardware descriptors.
"""

from __future__ import annotations

import logging
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import psutil

from zye_cybersecurity.discovery.device_models import NetworkInterfaceInfo, normalize_mac_address
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer

logger = logging.getLogger("zye.cybersecurity.interfaces")


class NetworkInterfaceDiscovery:
    """Discovers, categorizes, and audits network interfaces on the host system."""

    def __init__(self) -> None:
        self._route_cache: Optional[Dict[str, Any]] = None

    def _get_windows_route_info(self) -> Dict[str, Any]:
        """
        Parse Windows 'route print 0.0.0.0' output to extract interface descriptions,
        interface indices, default gateways, and route metrics.
        Cached to minimize process spawns.
        """
        if self._route_cache is not None:
            return self._route_cache

        route_data: Dict[str, Any] = {
            "interfaces_by_index": {},  # index -> {mac, desc}
            "interfaces_by_mac": {},    # normalized_mac -> {index, desc}
            "default_gateways": {},     # interface_ip -> {gateway, metric}
        }
        try:
            res = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            stdout = res.stdout or ""

            # 1. Parse Interface List
            # Format:  19...00 ff a1 a5 7e 6c ......TAP-Windows Adapter V9
            if_list_match = re.search(r"Interface List\s*\n(.*?)\n=+", stdout, re.DOTALL)
            if if_list_match:
                lines = if_list_match.group(1).strip().splitlines()
                for line in lines:
                    m = re.match(r"^\s*(\d+)\.\.\.([0-9a-fA-F ]+)\s*\.{3,}\s*(.*)$", line)
                    if m:
                        idx = int(m.group(1))
                        raw_mac = m.group(2).replace(" ", ":").strip()
                        desc = m.group(3).strip()
                        norm_mac = normalize_mac_address(raw_mac)
                        entry = {"index": idx, "mac": norm_mac, "description": desc}
                        route_data["interfaces_by_index"][idx] = entry
                        if norm_mac != "UNKNOWN_MAC":
                            route_data["interfaces_by_mac"][norm_mac] = entry
                    else:
                        m_no_mac = re.match(r"^\s*(\d+)\s*\.{3,}\s*(.*)$", line)
                        if m_no_mac:
                            idx = int(m_no_mac.group(1))
                            desc = m_no_mac.group(2).strip()
                            route_data["interfaces_by_index"][idx] = {"index": idx, "mac": "UNKNOWN_MAC", "description": desc}

            # 2. Parse IPv4 Route Table Active Routes
            # Network Destination   Netmask       Gateway       Interface     Metric
            # 0.0.0.0               0.0.0.0       10.93.34.171  10.93.34.248  35
            route_match = re.search(r"Active Routes:\s*Network Destination.*?\n(.*?)=+", stdout, re.DOTALL)
            if route_match:
                rlines = route_match.group(1).strip().splitlines()
                for rline in rlines:
                    parts = rline.split()
                    if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                        gw = parts[2]
                        if_ip = parts[3]
                        try:
                            metric = int(parts[4])
                        except ValueError:
                            metric = 999
                        # Keep lowest metric route for each interface
                        if if_ip not in route_data["default_gateways"] or metric < route_data["default_gateways"][if_ip]["metric"]:
                            route_data["default_gateways"][if_ip] = {"gateway": gw, "metric": metric}

        except Exception as e:
            logger.debug("Failed to query route print 0.0.0.0: %s", e)

        self._route_cache = route_data
        return route_data

    @staticmethod
    def classify_adapter(name: str, desc: Optional[str] = None) -> Tuple[str, bool]:
        """
        Classify adapter type and physical/virtual status based on name and description.
        Returns (adapter_type, is_physical).
        """
        combined = f"{name} {desc or ''}".lower()

        if "loopback" in combined or name.startswith("lo"):
            return "LOOPBACK", False
        if any(k in combined for k in ["tap", "openvpn", "wireguard", "wintun", "nordlynx", "proton", "tunnel"]):
            return "VPN", False
        if any(k in combined for k in ["virtual", "vbox", "vmware", "hyper-v", "wsl", "vethernet"]) or "*" in name:
            return "VIRTUAL", False
        if any(k in combined for k in ["wi-fi", "wifi", "wireless", "802.11", "wlan"]):
            return "WIFI", True
        if any(k in combined for k in ["ethernet", "gbe", "pcie", "lan", "realtek", "intel"]):
            return "ETHERNET", True

        return "UNKNOWN", True

    def discover_all_interfaces(
        self,
        include_disconnected: bool = False,
        include_virtual: bool = True,
        include_ipv6: bool = False,
    ) -> List[NetworkInterfaceInfo]:
        """
        Discover, audit, and return all network interfaces matching the filter criteria.
        """
        route_info = self._get_windows_route_info()
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        results: List[NetworkInterfaceInfo] = []

        for iface_name, addr_list in addrs.items():
            iface_stat = stats.get(iface_name)
            is_up = bool(iface_stat.isup) if iface_stat else False
            speed_mbps = int(iface_stat.speed) if iface_stat else 0
            mtu = int(iface_stat.mtu) if iface_stat else 1500

            # Extract addresses
            ipv4_addr: Optional[str] = None
            ipv6_addr: Optional[str] = None
            netmask: Optional[str] = None
            broadcast: Optional[str] = None
            mac_addr: Optional[str] = None

            for a in addr_list:
                if a.family == socket.AF_INET:
                    ipv4_addr = a.address
                    netmask = a.netmask
                    broadcast = a.broadcast
                elif a.family == socket.AF_INET6:
                    ipv6_addr = a.address
                elif a.family in (-1, getattr(psutil, "AF_LINK", -1)):
                    if a.address and not mac_addr:
                        mac_addr = normalize_mac_address(a.address)

            # Match route details by MAC address
            desc: Optional[str] = None
            if_idx: Optional[int] = None
            if mac_addr and mac_addr in route_info["interfaces_by_mac"]:
                match_entry = route_info["interfaces_by_mac"][mac_addr]
                desc = match_entry["description"]
                if_idx = match_entry["index"]

            # Match default gateway and metric by IPv4
            gw: Optional[str] = None
            metric: Optional[int] = None
            if ipv4_addr and ipv4_addr in route_info["default_gateways"]:
                gw_info = route_info["default_gateways"][ipv4_addr]
                gw = gw_info["gateway"]
                metric = gw_info["metric"]

            adapter_type, is_physical = self.classify_adapter(iface_name, desc)
            op_status = "UP" if is_up else "DOWN"

            # Calculate CIDR
            cidr: Optional[str] = None
            if ipv4_addr and netmask:
                try:
                    cfg = SubnetAnalyzer.calculate_subnet(ipv4_addr, netmask, default_gateway=gw)
                    cidr = cfg.cidr
                    if not broadcast:
                        broadcast = cfg.broadcast_address
                except Exception:
                    pass

            # Filter checks
            if not include_disconnected and not is_up:
                continue
            if not include_virtual and not is_physical and adapter_type != "LOOPBACK":
                continue

            info = NetworkInterfaceInfo(
                name=iface_name,
                description=desc or f"{adapter_type} adapter",
                adapter_type=adapter_type,
                is_up=is_up,
                operational_status=op_status,
                is_physical=is_physical,
                ipv4_address=ipv4_addr,
                ipv6_address=ipv6_addr if include_ipv6 else None,
                subnet_mask=netmask,
                cidr=cidr,
                broadcast_address=broadcast,
                mac_address=mac_addr,
                speed_mbps=speed_mbps,
                mtu=mtu,
                default_gateway=gw,
                interface_index=if_idx,
                metric=metric,
            )
            results.append(info)

        return results

    def get_primary_interface(self) -> Optional[NetworkInterfaceInfo]:
        """
        Identify and return the active default interface used for internet / local routing.
        Selection criteria: is_up is True, has valid IPv4, default gateway present, lowest metric.
        """
        interfaces = self.discover_all_interfaces(include_disconnected=False, include_virtual=True)
        active_routed = [i for i in interfaces if i.is_up and i.ipv4_address and i.default_gateway and i.adapter_type != "LOOPBACK"]

        if active_routed:
            # Sort by lowest metric, prioritizing physical adapters if metric is tied
            active_routed.sort(key=lambda x: (x.metric or 999, 0 if x.is_physical else 1))
            return active_routed[0]

        # Fallback to any active non-loopback with IPv4
        active_with_ip = [i for i in interfaces if i.is_up and i.ipv4_address and i.adapter_type != "LOOPBACK"]
        if active_with_ip:
            active_with_ip.sort(key=lambda x: (0 if x.adapter_type == "WIFI" else (1 if x.adapter_type == "ETHERNET" else 2)))
            return active_with_ip[0]

        return interfaces[0] if interfaces else None

    def get_interface_by_name(self, name: str) -> Optional[NetworkInterfaceInfo]:
        """Retrieve interface by exact or case-insensitive name."""
        all_ifaces = self.discover_all_interfaces(include_disconnected=True, include_virtual=True, include_ipv6=True)
        for iface in all_ifaces:
            if iface.name.lower() == name.strip().lower():
                return iface
        return None
