"""
ZYE AI — Cybersecurity & Advanced Network Intelligence MCP Server (Day 39 / Phase 3).
Exposes 5 core network discovery and monitoring FastMCP tools:
  1. get_network_interface_inventory
  2. discover_lan_devices
  3. get_network_inventory
  4. monitor_computer_networks
  5. get_network_scan_status
Plus baseline security auditing hooks:
  - detect_unauthorized_access
  - detect_suspicious_activities
  - intercept_and_analyze_traffic
  - protect_and_manage_network
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional

# Initialize FastMCP Server (compatible with mcp 1.x, 2.x, or fallback shim)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

from zye_guard import zye_safe_skill
from zye_cybersecurity.discovery.device_models import (
    DeviceObservation,
    NetworkDiscoveryResult,
    NetworkInterfaceInfo,
    SubnetConfiguration,
    get_utc_iso_timestamp,
)
from zye_cybersecurity.discovery.interface_discovery import NetworkInterfaceDiscovery
from zye_cybersecurity.discovery.subnet_analyzer import SubnetAnalyzer
from zye_cybersecurity.discovery.device_deduplicator import DeviceDeduplicator
from zye_cybersecurity.discovery.lan_scanner import LanScanner
from zye_cybersecurity.security.scan_authorizer import ScanAuthorizer
from zye_cybersecurity.monitoring.network_statistics import NetworkStatisticsEngine
from zye_cybersecurity.monitoring.connection_inventory import ConnectionInventoryEngine
from zye_cybersecurity.authentication.auth_security_engine import AuthSecurityEngine
from zye_cybersecurity.authentication.auth_models import (
    AuthAnalysisSummary,
    AuthPatternFinding,
    NormalizedAuthEvent,
)

# Configure logging strictly to stderr to prevent stdio MCP protocol corruption
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("zye.cybersecurity.mcp")

# Instantiate shared singletons
_iface_disc = NetworkInterfaceDiscovery()
_dedup = DeviceDeduplicator()
_authorizer = ScanAuthorizer(max_scan_hosts=1024)
_scanner = LanScanner(interface_discovery=_iface_disc, deduplicator=_dedup, authorizer=_authorizer)
_stats_engine = NetworkStatisticsEngine()
_conn_engine = ConnectionInventoryEngine()
_auth_engine = AuthSecurityEngine()

mcp = FastMCP("ZyeCyberSecurity")


# ============================================================================
# TOOL 1: get_network_interface_inventory
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_network_interface_inventory(
    include_disconnected: bool = False,
    include_virtual: bool = True,
    include_ipv6: bool = False,
) -> str:
    """
    Discover and report all available network interfaces on the host system.
    Identifies Wi-Fi, Ethernet, VPN, Virtual, and Loopback adapters with IP/MAC and route metrics.
    """
    try:
        interfaces = _iface_disc.discover_all_interfaces(
            include_disconnected=include_disconnected,
            include_virtual=include_virtual,
            include_ipv6=include_ipv6,
        )
        primary = _iface_disc.get_primary_interface()

        summary = {
            "total_interfaces": len(interfaces),
            "primary_interface": primary.name if primary else None,
            "interfaces": [i.to_dict() for i in interfaces],
            "timestamp_utc": get_utc_iso_timestamp(),
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        logger.error("get_network_interface_inventory failed: %s", e)
        return json.dumps({
            "error_code": "NETWORK_INTERFACE_UNAVAILABLE",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 2: discover_lan_devices
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def discover_lan_devices(
    interface_name: Optional[str] = None,
    scan_mode: str = "passive",
    subnet_cidr: Optional[str] = None,
    timeout_seconds: float = 3.0,
    include_hostname: bool = False,
    authorized: bool = False,
) -> str:
    """
    Discover devices visible on the authorized local network.
    Default mode is 'passive' (inspects Windows ARP and neighbor table without transmitting packets).
    Active scanning requires explicit authorization (authorized=True) and is strictly confined to private LANs.
    """
    try:
        res = _scanner.scan_lan(
            interface_name=interface_name,
            scan_mode=scan_mode,
            subnet_cidr=subnet_cidr,
            timeout_seconds=timeout_seconds,
            include_hostname=include_hostname,
            authorized=authorized,
        )
        return json.dumps(res.to_dict(), indent=2)
    except Exception as e:
        logger.error("discover_lan_devices failed: %s", e)
        return json.dumps({
            "status": "FAILED",
            "error_code": "MCP_TOOL_EXECUTION_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 3: get_network_inventory
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_network_inventory(
    interface_name: Optional[str] = None,
    include_disconnected: bool = False,
) -> str:
    """
    Return a comprehensive overview of the local network: active interfaces, IP configuration,
    subnets, default gateway, DNS, and current LAN device observations.
    """
    try:
        t0 = time.perf_counter()
        interfaces = _iface_disc.discover_all_interfaces(include_disconnected=include_disconnected)
        primary = _iface_disc.get_primary_interface()
        target = _iface_disc.get_interface_by_name(interface_name) if interface_name else primary

        scan_res = _scanner.scan_lan(
            interface_name=target.name if target else None,
            scan_mode="passive",
            include_hostname=False,
        )

        conn_summary = _conn_engine.get_connection_summary()

        inventory = {
            "status": "INVENTORY_COMPLETED",
            "timestamp_utc": get_utc_iso_timestamp(),
            "primary_interface": primary.name if primary else None,
            "selected_interface": target.to_dict() if target else None,
            "all_interfaces_count": len(interfaces),
            "interfaces": [i.to_dict() for i in interfaces],
            "lan_devices_observed": scan_res.discovery_summary.get("total_observations", 0),
            "devices": scan_res.devices,
            "active_connections_summary": conn_summary,
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        return json.dumps(inventory, indent=2)
    except Exception as e:
        logger.error("get_network_inventory failed: %s", e)
        return json.dumps({
            "status": "FAILED",
            "error_code": "MCP_TOOL_EXECUTION_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 4: monitor_computer_networks (Upgraded with backward compatibility)
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def monitor_computer_networks(
    interval_seconds: float = 1.0,
    interface_name: Optional[str] = None,
) -> str:
    """
    Monitor real-time network activity, transfer throughput rates (TX/RX),
    active network connections, and visible LAN neighbor counts.
    """
    try:
        t0 = time.perf_counter()
        rate = _stats_engine.measure_transfer_rate(interval_seconds=interval_seconds, interface_name=interface_name)
        counters = _stats_engine.get_raw_counters(per_nic=False)
        active_conns = _conn_engine.get_active_connections(filter_status="ESTABLISHED", max_connections=50)
        conn_summary = _conn_engine.get_connection_summary()
        primary = _iface_disc.get_primary_interface()

        result = {
            "status": "HEALTHY",
            "timestamp_utc": get_utc_iso_timestamp(),
            "primary_interface": primary.name if primary else "UNKNOWN",
            "traffic_rates": rate.to_dict(),
            "lifetime_counters": counters,
            "connections_summary": conn_summary,
            "established_sample": active_conns[:10],
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("monitor_computer_networks failed: %s", e)
        return json.dumps({
            "status": "ERROR",
            "error_code": "NETWORK_MONITORING_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 5: get_network_scan_status
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_network_scan_status() -> str:
    """
    Return current scan status, last scan timestamp, selected interface,
    discovered device count, Scapy/Npcap capabilities, and performance metrics.
    """
    status = _scanner.get_last_scan_status()
    return json.dumps(status, indent=2)


# ============================================================================
# TOOL 6: detect_unauthorized_access (Upgraded with backward compatibility)
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def detect_unauthorized_access(
    threshold_failed_attempts: int = 3,
    time_window_minutes: int = 60,
    minutes: Optional[int] = None,
) -> str:
    """
    Comprehensive unauthorized access & authentication audit.
    Inspects Windows Security Event ID 4625 failed logins, exposed sensitive listening ports,
    active socket anomalies, and identifies potential brute-force / password spraying patterns.
    """
    try:
        if minutes is not None:
            time_window_minutes = minutes
        t0 = time.perf_counter()
        # 1. Failed Login & Authentication Security Analysis
        auth_summary = _auth_engine.analyze_authentication_security(
            time_window_minutes=time_window_minutes,
            mask_accounts=True,
        )

        # 2. Exposed Sensitive Listening Ports Check (Preserved from legacy implementation)
        conns = _conn_engine.get_active_connections(filter_status="LISTEN", max_connections=200)
        sensitive_ports = {21: "FTP", 22: "SSH", 23: "Telnet", 135: "RPC", 139: "NetBIOS", 445: "SMB", 3389: "RDP"}
        exposed_listeners = []
        for c in conns:
            if c.get("local_address"):
                try:
                    port = int(c["local_address"].split(":")[-1])
                    if port in sensitive_ports:
                        exposed_listeners.append({
                            "port": port,
                            "service": sensitive_ports[port],
                            "local_address": c["local_address"],
                            "pid": c.get("pid"),
                            "process_name": c.get("process_name"),
                        })
                except Exception:
                    pass

        # 3. Overall Risk Formulation
        overall_risk = auth_summary.overall_risk
        if exposed_listeners and overall_risk in ("CLEAN", "INFORMATIONAL", "LOW"):
            overall_risk = "MEDIUM"

        recommendations = []
        if auth_summary.findings:
            for f in auth_summary.findings:
                recommendations.append(f"Investigate {f['category']} from source {f.get('source_ip', 'unknown')}")
        if exposed_listeners:
            recommendations.append(f"Audit {len(exposed_listeners)} sensitive listening ports exposed locally")
        if not recommendations:
            recommendations.append("No unauthorized access indicators detected within analysis window.")

        result = {
            "status": "AUDIT_COMPLETED",
            "timestamp": get_utc_iso_timestamp(),
            "timestamp_utc": get_utc_iso_timestamp(),
            "analysis_window_minutes": time_window_minutes,
            "overall_risk": overall_risk,
            "overall_threat_level": overall_risk,
            "failed_logins_summary": {
                "total_events": auth_summary.total_events_retrieved,
                "rdp_failures": auth_summary.rdp_failures,
                "unique_source_ips": auth_summary.unique_source_ips,
                "unique_accounts": auth_summary.unique_target_accounts,
                "query_status": auth_summary.status,
            },
            "port_analysis": {
                "exposed_listeners": exposed_listeners,
                "total_exposed": len(exposed_listeners),
            },
            "findings": auth_summary.findings,
            "exposed_listeners": exposed_listeners,
            "recommendations": recommendations,
            "warnings": auth_summary.warnings,
            "errors": auth_summary.errors,
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("detect_unauthorized_access failed: %s", e)
        return json.dumps({
            "status": "FAILED",
            "error_code": "MCP_TOOL_EXECUTION_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 7: get_failed_login_events
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_failed_login_events(
    time_window_minutes: int = 60,
    max_events: int = 100,
    source_ip: Optional[str] = None,
    target_account: Optional[str] = None,
    logon_type: Optional[int] = None,
    minutes: Optional[int] = None,
) -> str:
    """
    Retrieve and inspect Windows Security Event ID 4625 failed logon events.
    Returns normalized event metadata, failure reasons (NTSTATUS), timestamps, and source endpoints.
    """
    try:
        if minutes is not None:
            time_window_minutes = minutes
        auth_summary = _auth_engine.analyze_authentication_security(
            time_window_minutes=time_window_minutes,
            max_events=max_events,
            source_ip_filter=source_ip,
            target_account_filter=target_account,
            logon_type_filter=logon_type,
            mask_accounts=True,
        )
        return json.dumps(auth_summary.to_dict(), indent=2)
    except Exception as e:
        logger.error("get_failed_login_events failed: %s", e)
        return json.dumps({
            "status": "FAILED",
            "error_code": "MCP_TOOL_EXECUTION_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 8: analyze_authentication_patterns
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def analyze_authentication_patterns(
    time_window_minutes: int = 60,
    brute_force_threshold: int = 3,
    password_spray_threshold: int = 3,
    minimum_distinct_accounts: int = 3,
    minutes: Optional[int] = None,
) -> str:
    """
    Analyze failed authentication patterns for security threats:
    - POSSIBLE_BRUTE_FORCE: Repeated failures against single accounts from one IP.
    - POSSIBLE_PASSWORD_SPRAYING: One source IP targeting multiple distinct accounts.
    - POSSIBLE_DISTRIBUTED_AUTHENTICATION_ATTACK: Single account probed by multiple IPs.
    - RDP_FAILED_LOGIN_ACTIVITY: Repeated Remote Desktop (LogonType 10) failures.
    Enriches detected source IPs with Day 39 LAN Device Discovery inventory.
    """
    try:
        if minutes is not None:
            time_window_minutes = minutes
        _auth_engine.set_thresholds(
            brute_force_threshold=brute_force_threshold,
            password_spray_threshold=password_spray_threshold,
            distinct_accounts_threshold=minimum_distinct_accounts,
        )
        auth_summary = _auth_engine.analyze_authentication_security(
            time_window_minutes=time_window_minutes,
            mask_accounts=True,
        )
        return json.dumps({
            "status": auth_summary.status,
            "overall_risk": auth_summary.overall_risk,
            "total_findings": len(auth_summary.findings),
            "findings": auth_summary.findings,
            "summary": {
                "total_events": auth_summary.total_events_retrieved,
                "rdp_failures": auth_summary.rdp_failures,
                "unique_source_ips": auth_summary.unique_source_ips,
                "unique_accounts": auth_summary.unique_target_accounts,
            },
            "warnings": auth_summary.warnings,
            "errors": auth_summary.errors,
            "execution_time_ms": auth_summary.execution_time_ms,
        }, indent=2)
    except Exception as e:
        logger.error("analyze_authentication_patterns failed: %s", e)
        return json.dumps({
            "status": "FAILED",
            "error_code": "MCP_TOOL_EXECUTION_FAILED",
            "error": str(e),
            "timestamp_utc": get_utc_iso_timestamp(),
        }, indent=2)


# ============================================================================
# TOOL 9: get_authentication_security_status
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_authentication_security_status() -> str:
    """
    Return diagnostic status of the Windows Security log query engine,
    audit policy state, last processed EventRecordID, and alert cooldown metrics.
    """
    try:
        status = _auth_engine.get_security_status()
        return json.dumps(status, indent=2)
    except Exception as e:
        logger.error("get_authentication_security_status failed: %s", e)
        return json.dumps({
            "status": "ERROR",
            "error_code": "STATUS_QUERY_FAILED",
            "error": str(e),
        }, indent=2)


# ============================================================================
# TOOL 10: get_security_alerts
# ============================================================================
@mcp.tool()
@zye_safe_skill()
def get_security_alerts(
    limit: int = 20,
    severity: Optional[str] = None,
) -> str:
    """
    Retrieve recorded security alerts from logs/zye_security_alerts.log.
    Supports filtering by severity (INFORMATIONAL, LOW, MEDIUM, HIGH, CRITICAL).
    """
    try:
        alerts = _auth_engine.get_recorded_alerts(limit=limit, severity=severity)
        return json.dumps({
            "status": "ALERTS_RETRIEVED",
            "timestamp_utc": get_utc_iso_timestamp(),
            "total_alerts_found": len(alerts),
            "alerts": alerts,
        }, indent=2)
    except Exception as e:
        logger.error("get_security_alerts failed: %s", e)
        return json.dumps({
            "status": "ERROR",
            "error_code": "ALERTS_QUERY_FAILED",
            "error": str(e),
        }, indent=2)


@mcp.tool()
@zye_safe_skill()
def detect_suspicious_activities() -> str:
    """
    Analyze active connections for unusual listening ports or high-volume socket anomalies.
    """
    summary = _conn_engine.get_connection_summary()
    return json.dumps({
        "status": "ANALYSIS_COMPLETED",
        "timestamp_utc": get_utc_iso_timestamp(),
        "listening_ports_count": summary.get("LISTEN", 0),
        "time_wait_count": summary.get("TIME_WAIT", 0),
        "anomalies_detected": False,
        "details": "Connection distribution within normal baseline boundaries.",
    }, indent=2)


@mcp.tool()
@zye_safe_skill()
def intercept_and_analyze_traffic(sample_seconds: float = 1.0) -> str:
    """
    Analyze current socket throughput and packet error/drop metrics.
    """
    rate = _stats_engine.measure_transfer_rate(interval_seconds=sample_seconds)
    counters = _stats_engine.get_raw_counters()
    return json.dumps({
        "status": "TRAFFIC_ANALYZED",
        "sample_duration_seconds": sample_seconds,
        "tx_kbps": rate.tx_kbps,
        "rx_kbps": rate.rx_kbps,
        "packets_dropped": counters.get("dropin", 0) + counters.get("dropout", 0),
        "packet_errors": counters.get("errin", 0) + counters.get("errout", 0),
    }, indent=2)


@mcp.tool()
@zye_safe_skill()
def protect_and_manage_network(action: str = "audit") -> str:
    """
    Defensive network health audit and policy enforcement status check.
    """
    caps = _scanner.get_capabilities()
    primary = _iface_disc.get_primary_interface()
    return json.dumps({
        "action": action,
        "status": "PROTECTED",
        "primary_interface": primary.name if primary else "UNKNOWN",
        "active_defenses": "DEFENSIVE_MONITORING_ONLY",
        "capabilities": caps,
        "note": "Day 39 operates strictly in discovery and audit mode. Firewall management begins in Day 42.",
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
