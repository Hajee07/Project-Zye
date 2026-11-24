"""
ZYE AI — Cybersecurity & Authentication Intelligence Architecture (Phase 3 / Day 40).
"""

from zye_cybersecurity.discovery import (
    ArpTableParser,
    DeviceDeduplicator,
    DeviceObservation,
    LanScanner,
    NetworkDiscoveryResult,
    NetworkInterfaceDiscovery,
    NetworkInterfaceInfo,
    SubnetAnalyzer,
    SubnetConfiguration,
    normalize_mac_address,
)
from zye_cybersecurity.monitoring import (
    ConnectionInventoryEngine,
    NetworkRate,
    NetworkStatisticsEngine,
)
from zye_cybersecurity.security import (
    ScanAuthorizationError,
    ScanAuthorizer,
)
from zye_cybersecurity.authentication import (
    AuthAnalysisSummary,
    AuthPatternFinding,
    AuthSecurityEngine,
    BruteForceDetector,
    DistributedAuthDetector,
    EventRetriever,
    EventXmlParser,
    EventXmlParserError,
    LogonTypeAnalyzer,
    NormalizedAuthEvent,
    PasswordSprayDetector,
    RdpAuthAnalyzer,
    StatusCodeAnalyzer,
    mask_identifier,
)

__version__ = "40.0.0"

__all__ = [
    "ArpTableParser",
    "AuthAnalysisSummary",
    "AuthPatternFinding",
    "AuthSecurityEngine",
    "BruteForceDetector",
    "ConnectionInventoryEngine",
    "DeviceDeduplicator",
    "DeviceObservation",
    "DistributedAuthDetector",
    "EventRetriever",
    "EventXmlParser",
    "EventXmlParserError",
    "LanScanner",
    "LogonTypeAnalyzer",
    "NetworkDiscoveryResult",
    "NetworkInterfaceDiscovery",
    "NetworkInterfaceInfo",
    "NetworkRate",
    "NetworkStatisticsEngine",
    "NormalizedAuthEvent",
    "PasswordSprayDetector",
    "RdpAuthAnalyzer",
    "ScanAuthorizationError",
    "ScanAuthorizer",
    "StatusCodeAnalyzer",
    "SubnetAnalyzer",
    "SubnetConfiguration",
    "mask_identifier",
    "normalize_mac_address",
]
