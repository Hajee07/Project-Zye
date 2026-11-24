"""
ZYE AI — Device Deduplication & Observation Tracker (Day 39).
Deduplicates network devices across passive ARP observations and active scans,
tracks observation counts, detects IP changes, and manages device history.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from zye_cybersecurity.discovery.device_models import DeviceObservation, normalize_mac_address

logger = logging.getLogger("zye.cybersecurity.deduplicator")


class DeviceDeduplicator:
    """Manages device deduplication and persistent in-memory observation tracking."""

    def __init__(self) -> None:
        # device_id -> DeviceObservation
        self._device_registry: Dict[str, DeviceObservation] = {}
        # mac -> set of observed IPs
        self._mac_to_ips: Dict[str, set[str]] = {}

    def clear(self) -> None:
        """Clear all stored observation history."""
        self._device_registry.clear()
        self._mac_to_ips.clear()

    def deduplicate(
        self,
        new_observations: List[DeviceObservation],
        track_history: bool = True,
    ) -> List[DeviceObservation]:
        """
        Deduplicate a list of new observations against each other and against history.
        Promotes status when active responses arrive and detects multi-IP or IP changes.
        """
        batch_map: Dict[str, DeviceObservation] = {}

        for obs in new_observations:
            norm_mac = normalize_mac_address(obs.mac_address)
            # Composite key: (mac, ip)
            key = f"{norm_mac}|{obs.ip_address}"

            if key in batch_map:
                existing = batch_map[key]
                # Merge observations
                existing.observation_count += 1
                existing.last_seen = obs.last_seen

                # Upgrade status if active probe confirms online state
                if obs.observation_status == "ACTIVE_RESPONSE_OBSERVED":
                    existing.observation_status = "ACTIVE_RESPONSE_OBSERVED"
                    existing.confidence = max(existing.confidence, 1.0)
                    existing.discovery_method = obs.discovery_method
                elif obs.confidence > existing.confidence:
                    existing.confidence = obs.confidence

                if obs.hostname and not existing.hostname:
                    existing.hostname = obs.hostname
                if obs.vendor and obs.vendor != "UNKNOWN_VENDOR" and existing.vendor == "UNKNOWN_VENDOR":
                    existing.vendor = obs.vendor
            else:
                batch_map[key] = obs

        # Merge with in-memory historical registry if tracking enabled
        result: List[DeviceObservation] = []
        for key, obs in batch_map.items():
            norm_mac = obs.mac_address

            if track_history:
                # Track IP history for this MAC
                if norm_mac not in self._mac_to_ips:
                    self._mac_to_ips[norm_mac] = set()
                elif obs.ip_address not in self._mac_to_ips[norm_mac] and norm_mac != "UNKNOWN_MAC":
                    obs.warnings.append(f"IP address change detected: MAC was previously observed on {list(self._mac_to_ips[norm_mac])}")
                self._mac_to_ips[norm_mac].add(obs.ip_address)

                if obs.device_id in self._device_registry:
                    hist = self._device_registry[obs.device_id]
                    obs.first_seen = hist.first_seen
                    obs.observation_count += hist.observation_count
                    if hist.hostname and not obs.hostname:
                        obs.hostname = hist.hostname
                    if hist.vendor and hist.vendor != "UNKNOWN_VENDOR" and obs.vendor == "UNKNOWN_VENDOR":
                        obs.vendor = hist.vendor

                self._device_registry[obs.device_id] = obs

            result.append(obs)

        return result

    def get_tracked_devices(self) -> List[DeviceObservation]:
        """Return all tracked devices in history."""
        return list(self._device_registry.values())
