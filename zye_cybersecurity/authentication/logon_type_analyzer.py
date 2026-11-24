"""
ZYE AI — Windows Logon Type Analysis Engine (Day 40).
Provides documented interpretation of Windows authentication logon types,
their operational descriptions, and security significance.
"""

from __future__ import annotations

from typing import Dict, NamedTuple, Optional, Tuple


class LogonTypeInfo(NamedTuple):
    type_id: int
    name: str
    description: str
    security_context: str
    is_remote: bool


# Official Microsoft Windows Logon Types:
# https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4625
LOGON_TYPES: Dict[int, Tuple[str, str, str]] = {
    0: (
        "System",
        "Used only by the System account at system startup.",
        "Internal operating system context.",
    ),
    2: (
        "Interactive",
        "A user logged on to this computer locally (physical console / keyboard).",
        "Direct physical console or local logon attempt.",
    ),
    3: (
        "Network",
        "A user or computer logged on to this computer from the network (e.g., SMB share, IIS).",
        "Network service, shared folder, or HTTP authentication attempt.",
    ),
    4: (
        "Batch",
        "Batch logon type is used by batch servers, where processes may execute on behalf of a user.",
        "Scheduled task or automated script batch execution.",
    ),
    5: (
        "Service",
        "A service was started by the Service Control Manager.",
        "Windows background service credential validation.",
    ),
    7: (
        "Unlock",
        "This workstation was unlocked.",
        "Workstation screen unlock attempt.",
    ),
    8: (
        "NetworkCleartext",
        "A user logged on to this computer from the network with credentials sent in plaintext.",
        "Unencrypted network authentication attempt (e.g., basic authentication).",
    ),
    9: (
        "NewCredentials",
        "A caller cloned its current token and specified new credentials for outbound connections.",
        "RunAs / alternate credentials impersonation attempt.",
    ),
    10: (
        "RemoteInteractive",
        "A user logged on to this computer remotely using Terminal Services or Remote Desktop (RDP).",
        "Remote Desktop (RDP) login attempt.",
    ),
    11: (
        "CachedInteractive",
        "A user logged on to this computer with logon credentials that were stored locally.",
        "Offline domain workstation logon using cached credentials.",
    ),
    12: (
        "CachedRemoteInteractive",
        "A user logged on remotely using cached credentials.",
        "Cached Remote Desktop connection attempt.",
    ),
    13: (
        "CachedUnlock",
        "Workstation unlock using cached credentials.",
        "Cached workstation unlock attempt.",
    ),
}


class LogonTypeAnalyzer:
    """Interprets and explains Windows logon type integers."""

    @staticmethod
    def get_logon_type_info(logon_type: Optional[int]) -> LogonTypeInfo:
        """
        Return LogonTypeInfo(type_id, name, description, security_context, is_remote).
        Can be accessed as named tuple (.name, .type_id, .is_remote) or unpacked as tuple.
        """
        if logon_type is None:
            return LogonTypeInfo(
                type_id=-1,
                name="UNKNOWN_LOGON_TYPE",
                description="Logon type not provided in event record.",
                security_context="Unknown authentication context.",
                is_remote=False,
            )

        is_remote = logon_type in (10, 12)
        if logon_type in LOGON_TYPES:
            name, desc, ctx = LOGON_TYPES[logon_type]
            return LogonTypeInfo(
                type_id=logon_type,
                name=name,
                description=desc,
                security_context=ctx,
                is_remote=is_remote,
            )

        return LogonTypeInfo(
            type_id=logon_type,
            name=f"Unknown ({logon_type})",
            description=f"Undocumented logon type {logon_type}.",
            security_context="Non-standard authentication context.",
            is_remote=is_remote,
        )

    @staticmethod
    def is_remote_desktop(logon_type: Optional[int]) -> bool:
        """Check whether logon type represents Remote Desktop (RDP / Terminal Services)."""
        return logon_type in (10, 12)

    @staticmethod
    def is_network_logon(logon_type: Optional[int]) -> bool:
        """Check whether logon type represents network-based authentication."""
        return logon_type in (3, 8)

    @staticmethod
    def is_local_interactive(logon_type: Optional[int]) -> bool:
        """Check whether logon type represents local console interaction."""
        return logon_type in (2, 7, 11, 13)

    @staticmethod
    def is_interactive(logon_type: Optional[int]) -> bool:
        """Check whether logon type represents console interactive logon."""
        return logon_type in (2, 7, 11, 13)
