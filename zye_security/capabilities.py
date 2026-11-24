"""
ZYE AI — RBAC Capability & Fine-Grained Permissions
===================================================

Implements Section 26 of Master Engineering Specification.
Defines fine-grained capabilities for tool dispatch and agent action gating.
Enforces:
1. Capability tokens (file:read, file:write, code:execute, tool:invoke, etc.)
2. Resource glob matching (e.g. "data/*", "*.json")
3. Explicit allow/deny rules
4. Event bus notifications on permission denial or elevation requirement
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.security.capabilities")


class Capability(str, Enum):
    """Fine-grained capability labels."""

    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    NETWORK_FETCH = "network:fetch"
    CODE_EXECUTE = "code:execute"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    TOOL_INVOKE = "tool:invoke"
    SCHEDULE_CREATE = "schedule:create"
    SYSTEM_ADMIN = "system:admin"


@dataclass(slots=True)
class CapabilityGrant:
    """A grant permitting a capability on matching resource patterns."""

    capability: Capability
    resource_pattern: str = "*"


class CapabilityPolicy:
    """
    Evaluates whether an agent, caller, or tool execution is authorized for a capability.
    """

    def __init__(
        self,
        default_deny: bool = False,
        event_bus: Optional[ZyeEventBus] = None,
    ) -> None:
        self.default_deny = default_deny
        self.event_bus = event_bus
        self._grants: Dict[str, List[CapabilityGrant]] = {}
        self._denials: Dict[str, Set[Capability]] = {}

    def grant(self, role_or_agent: str, capability: Capability, resource_pattern: str = "*") -> None:
        """Grant a capability on matching resources."""
        self._grants.setdefault(role_or_agent, []).append(
            CapabilityGrant(capability=capability, resource_pattern=resource_pattern)
        )

    def deny(self, role_or_agent: str, capability: Capability) -> None:
        """Explicitly deny a capability, overriding any grants."""
        self._denials.setdefault(role_or_agent, set()).add(capability)

    def check_permission(
        self,
        role_or_agent: str,
        capability: Capability,
        resource: str = "*",
    ) -> bool:
        """
        Verify whether role_or_agent has permission for capability on resource.
        """
        # 1. Explicit denial takes precedence
        if capability in self._denials.get(role_or_agent, set()):
            self._notify_denial(role_or_agent, capability, resource, "Explicitly denied by policy")
            return False

        # 2. Check explicit grants
        grants = self._grants.get(role_or_agent, [])
        for g in grants:
            if g.capability == capability:
                if fnmatch.fnmatch(resource, g.resource_pattern):
                    return True

        # 3. Default policy check
        if self.default_deny:
            self._notify_denial(role_or_agent, capability, resource, "Default-deny policy enforced")
            return False

        # Open by default for non-destructive operations; destructive requires grant if default_deny=False
        if capability in (Capability.CODE_EXECUTE, Capability.SYSTEM_ADMIN):
            # Code execute & system admin ALWAYS require explicit grant even if default_deny is False
            self._notify_denial(role_or_agent, capability, resource, "Privileged capability requires explicit grant")
            return False

        return True

    def _notify_denial(self, role: str, cap: Capability, resource: str, reason: str) -> None:
        logger.warning("Capability DENIED [%s]: role=%s, cap=%s, res=%s", reason, role, cap.value, resource)
        if self.event_bus:
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=ZyeEventType.SECURITY_ALERT,
                    source_module="zye.security.capabilities",
                    payload={
                        "role": role,
                        "capability": cap.value,
                        "resource": resource,
                        "reason": reason,
                    },
                )
            )


__all__ = [
    "Capability",
    "CapabilityGrant",
    "CapabilityPolicy",
]
