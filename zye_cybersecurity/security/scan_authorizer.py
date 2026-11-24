"""
ZYE AI — Active Network Scan Authorizer & Scope Gate (Day 39).
Defensive security validator enforcing private subnet scopes, interface containment,
host limits, and mandatory explicit authorization for active network probes.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Optional, Tuple

from zye_cybersecurity.discovery.device_models import NetworkInterfaceInfo
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer

logger = logging.getLogger("zye.cybersecurity.authorizer")


class ScanAuthorizationError(PermissionError):
    """Raised when an active scan violates safety boundaries or lacks authorization."""
    pass


class ScanAuthorizer:
    """Enforces safety, scope boundaries, and explicit consent for active scans."""

    def __init__(self, max_scan_hosts: int = 1024) -> None:
        self.max_scan_hosts = max_scan_hosts

    def authorize_active_scan(
        self,
        target_cidr: str,
        interface: NetworkInterfaceInfo,
        authorized: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate whether an active scan is permitted against target_cidr on interface.
        Enforces:
          1. Explicit user authorization (authorized=True)
          2. Target scope must be private IPv4 (RFC 1918 / RFC 3927)
          3. Subnet host count <= max_scan_hosts
          4. Subnet containment: target CIDR must belong to interface's network
        Returns (is_authorized, error_message).
        """
        # 1. Check explicit authorization
        if not authorized:
            return False, "ACTIVE_SCAN_NOT_AUTHORIZED: Active ARP scanning requires explicit user authorization (set authorized=True)"

        # 2. Parse target CIDR
        try:
            target_net = ipaddress.IPv4Network(target_cidr.strip(), strict=False)
        except Exception as e:
            return False, f"INVALID_SUBNET: Invalid CIDR notation '{target_cidr}': {e}"

        # 3. Verify private address space (defense against scanning public internet)
        if not (target_net.is_private or target_net.is_link_local or target_net.is_loopback):
            return False, f"UNAUTHORIZED_NETWORK_SCOPE: Target {target_cidr} is a public internet address. Active scanning is strictly restricted to private LANs."

        # 4. Enforce host limit
        if target_net.num_addresses > self.max_scan_hosts:
            return False, f"SUBNET_HOST_LIMIT_EXCEEDED: Subnet size ({target_net.num_addresses} hosts) exceeds maximum allowed scope of {self.max_scan_hosts} hosts."

        # 5. Interface containment verification
        if interface.ipv4_address and interface.subnet_mask:
            try:
                iface_net = ipaddress.IPv4Network(f"{interface.ipv4_address}/{interface.subnet_mask}", strict=False)
                # Check if target_net is a subnet or identical to iface_net
                if not (target_net.subnet_of(iface_net) or target_net == iface_net or iface_net.subnet_of(target_net)):
                    return False, f"SUBNET_OUTSIDE_SELECTED_INTERFACE: Target subnet {target_cidr} does not belong to interface '{interface.name}' network ({iface_net})."
            except Exception as e:
                logger.warning("Could not verify interface containment: %s", e)

        logger.info(
            "Active network scan authorized for interface '%s' against target subnet %s (hosts: %d)",
            interface.name,
            target_cidr,
            target_net.num_addresses,
        )
        return True, None
