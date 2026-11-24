"""
ZYE AI — Established Connection Inventory Engine (Day 39).
Audits active IPv4/IPv6 connections using psutil.net_connections,
extracts protocols, endpoints, connection states, and process identities,
with graceful fallbacks for Windows privilege limitations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger("zye.cybersecurity.connections")


class ConnectionInventoryEngine:
    """Collects and categorizes active socket connections on the host."""

    @staticmethod
    def get_active_connections(
        kind: str = "inet",
        filter_status: Optional[str] = None,
        max_connections: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve network connections.
        Handles Windows AccessDenied permissions gracefully by tagging
        process name as 'PROCESS_INFORMATION_UNAVAILABLE'.
        """
        connections: List[Dict[str, Any]] = []

        try:
            raw_conns = psutil.net_connections(kind=kind)
        except Exception as e:
            logger.warning("Could not query psutil.net_connections: %s", e)
            return []

        for conn in raw_conns:
            if filter_status and conn.status.upper() != filter_status.strip().upper():
                continue

            local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None
            remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None

            # Protocol
            proto = "TCP" if conn.type == 1 else ("UDP" if conn.type == 2 else "UNKNOWN")

            # Process Name Lookup with Permission Fallback
            proc_name: Optional[str] = None
            if conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    proc_name = proc.name()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    proc_name = "PROCESS_INFORMATION_UNAVAILABLE"
                except Exception:
                    proc_name = "UNKNOWN_PROCESS"
            else:
                proc_name = "SYSTEM_OR_UNAVAILABLE"

            entry = {
                "fd": conn.fd,
                "protocol": proto,
                "local_address": local_addr,
                "remote_address": remote_addr,
                "status": conn.status,
                "pid": conn.pid,
                "process_name": proc_name,
            }
            connections.append(entry)
            if len(connections) >= max_connections:
                break

        return connections

    @staticmethod
    def get_connection_summary() -> Dict[str, Any]:
        """Return counts by connection status (ESTABLISHED, LISTEN, TIME_WAIT, etc.)."""
        counts: Dict[str, int] = {
            "ESTABLISHED": 0,
            "LISTEN": 0,
            "TIME_WAIT": 0,
            "CLOSE_WAIT": 0,
            "SYN_SENT": 0,
            "SYN_RECV": 0,
            "FIN_WAIT1": 0,
            "FIN_WAIT2": 0,
            "LAST_ACK": 0,
            "CLOSING": 0,
            "NONE": 0,
            "TOTAL": 0,
        }

        try:
            for conn in psutil.net_connections(kind="inet"):
                status = conn.status.upper()
                counts["TOTAL"] += 1
                if status in counts:
                    counts[status] += 1
                else:
                    counts["NONE"] += 1
        except Exception as e:
            logger.warning("Error getting connection summary: %s", e)

        return counts
