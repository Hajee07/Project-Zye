# ZYE AI — Day 39 Network Intelligence & LAN Discovery Documentation

## Overview
The ZYE Advanced Network Intelligence & LAN Discovery Engine provides defensive, authorized network reconnaissance, interface analysis, and real-time traffic monitoring for ZYE AI.

## Architecture & Subsystems
- `zye_cybersecurity/discovery/interface_discovery.py`: Discovers physical (Wi-Fi, Ethernet) and virtual (VPN, Direct) interfaces and resolves route metrics.
- `zye_cybersecurity/discovery/subnet_analyzer.py`: Validates IPv4 subnets, derives usable host ranges, and enforces private RFC 1918/3927 boundaries.
- `zye_cybersecurity/discovery/arp_table_parser.py`: Parses Windows `arp -a` and `Get-NetNeighbor`, normalizes MAC addresses, and maps neighbor states.
- `zye_cybersecurity/discovery/device_deduplicator.py`: Combines observations, promotes active responses, and tracks device history.
- `zye_cybersecurity/security/scan_authorizer.py`: Defensive scope gate enforcing private subnet containment and explicit authorization.
- `zye_cybersecurity/discovery/lan_scanner.py`: Master coordinator supporting passive ARP discovery and authorized active Scapy probes with Npcap fallback.
- `zye_cybersecurity/monitoring/network_statistics.py`: Measures interval-based TX/RX transfer rates and lifetime counters.
- `zye_cybersecurity/monitoring/connection_inventory.py`: Audits active socket connections and process identities.

## FastMCP Tools in `cyber_security_mcp.py`
1. `get_network_interface_inventory(include_disconnected=False, include_virtual=True, include_ipv6=False)`
2. `discover_lan_devices(interface_name=None, scan_mode="passive", subnet_cidr=None, timeout_seconds=3.0, include_hostname=False, authorized=False)`
3. `get_network_inventory(interface_name=None, include_disconnected=False)`
4. `monitor_computer_networks(interval_seconds=1.0, interface_name=None)`
5. `get_network_scan_status()`

## Voice Interaction Examples (Tamil / Tanglish / English)
- **"Zye, ennoda Wi-Fi-la evvalavu devices connect aagirukku nu check pannu."**  
  *Invokes `discover_lan_devices(scan_mode="passive")` and reports observed neighbor counts.*
- **"Zye, ennoda laptop-oda IP address and gateway enna?"**  
  *Invokes `get_network_interface_inventory()` and reports primary IP and gateway.*
- **"Network traffic and transfer speed check pannu."**  
  *Invokes `monitor_computer_networks()` and reports real-time TX/RX throughput.*
