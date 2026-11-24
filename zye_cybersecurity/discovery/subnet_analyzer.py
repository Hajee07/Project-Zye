"""
ZYE AI — Subnet Analyzer & Network Scope Validation (Day 39).
Performs exact mathematical subnet calculations using ipaddress,
validates private scopes, checks CIDR constraints, and enforces host limits.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Optional, Tuple

from zye_cybersecurity.discovery.device_models import SubnetConfiguration

logger = logging.getLogger("zye.cybersecurity.subnet")

# Default security limit: maximum number of hosts permissible for single scan
MAX_SCAN_HOSTS_DEFAULT = 1024


class SubnetValidationError(ValueError):
    """Raised when an IP address, netmask, or CIDR fails validation."""
    pass


class SubnetAnalyzer:
    """Provides validated IPv4 subnet calculations and scope checking."""

    @staticmethod
    def calculate_subnet(
        ip_str: str,
        netmask_str: str,
        default_gateway: Optional[str] = None,
        dns_servers: Optional[list[str]] = None,
        interface_mac: Optional[str] = None,
    ) -> SubnetConfiguration:
        """
        Calculate complete subnet configuration from IP address and netmask.
        Validates values strictly using standard library ipaddress.
        """
        try:
            ip = ipaddress.IPv4Address(ip_str.strip())
        except Exception as e:
            raise SubnetValidationError(f"Invalid IPv4 address '{ip_str}': {e}") from e

        try:
            # Parse netmask
            mask = ipaddress.IPv4Address(netmask_str.strip())
            # Form network with strict host bits set to False
            network = ipaddress.IPv4Network(f"{ip_str}/{netmask_str}", strict=False)
        except Exception as e:
            raise SubnetValidationError(f"Invalid subnet mask '{netmask_str}': {e}") from e

        # Usable host range calculation in O(1) arithmetic without materializing generator
        num = network.num_addresses
        if num > 2:
            usable_range = (str(network.network_address + 1), str(network.broadcast_address - 1))
            total_usable = num - 2
        elif num == 2:
            usable_range = (str(network.network_address), str(network.broadcast_address))
            total_usable = 2
        else:
            usable_range = (str(network.network_address), str(network.network_address))
            total_usable = 1

        is_private = ip.is_private or ip.is_link_local or ip.is_loopback

        return SubnetConfiguration(
            local_ip=str(ip),
            subnet_mask=str(mask),
            cidr=str(network),
            network_address=str(network.network_address),
            broadcast_address=str(network.broadcast_address),
            default_gateway=default_gateway,
            dns_servers=dns_servers or [],
            interface_mac=interface_mac,
            total_hosts=total_usable,
            usable_hosts_range=usable_range,
            is_private=is_private,
        )

    @staticmethod
    def parse_cidr(cidr_str: str) -> ipaddress.IPv4Network:
        """
        Parse and validate a CIDR notation string (e.g. '192.168.1.0/24').
        Raises SubnetValidationError on malformed input.
        """
        try:
            network = ipaddress.IPv4Network(cidr_str.strip(), strict=False)
            return network
        except Exception as e:
            raise SubnetValidationError(f"Invalid CIDR notation '{cidr_str}': {e}") from e

    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """Check if an IPv4 address belongs to RFC 1918 or RFC 3927 private ranges."""
        try:
            ip = ipaddress.IPv4Address(ip_str.strip())
            return ip.is_private or ip.is_link_local or ip.is_loopback
        except Exception:
            return False

    @staticmethod
    def is_multicast_or_broadcast(ip_str: str) -> bool:
        """Check if an IP address is multicast (224.0.0.0/4) or broadcast (255.255.255.255)."""
        try:
            ip = ipaddress.IPv4Address(ip_str.strip())
            return ip.is_multicast or ip.is_reserved or str(ip) == "255.255.255.255"
        except Exception:
            return False

    @staticmethod
    def validate_scan_scope(
        target_cidr: str,
        max_hosts: int = MAX_SCAN_HOSTS_DEFAULT,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that target CIDR is strictly private and within max host limit.
        Returns (is_valid, error_code_or_message).
        """
        try:
            net = SubnetAnalyzer.parse_cidr(target_cidr)
        except SubnetValidationError as e:
            return False, f"INVALID_SUBNET: {e}"

        if not (net.is_private or net.is_link_local or net.is_loopback):
            return False, "UNAUTHORIZED_NETWORK_SCOPE: Target subnet is not a private IP range (RFC 1918 / RFC 3927)"

        if net.num_addresses > max_hosts:
            return False, f"SUBNET_HOST_LIMIT_EXCEEDED: Subnet size {net.num_addresses} exceeds configured maximum limit of {max_hosts} hosts"

        return True, None
