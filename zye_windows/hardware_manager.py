"""
Unified Hardware Control Facade — Zye Day 16 & Day 18.
Consolidates master volume, screen brightness, battery health telemetry,
and system power management into a cohesive, verified facade.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from zye_windows.volume_manager import WindowsVolumeManager
from zye_windows.brightness_manager import WindowsBrightnessManager
from zye_windows.power_manager import WindowsPowerManager

logger = logging.getLogger("zye.windows.hardware")


class WindowsHardwareManager:
    """
    Unified facade managing volume, brightness, battery, and power controls.
    """

    def __init__(
        self,
        volume_mgr: Optional[WindowsVolumeManager] = None,
        brightness_mgr: Optional[WindowsBrightnessManager] = None,
        power_mgr: Optional[WindowsPowerManager] = None,
    ) -> None:
        self.volume_mgr = volume_mgr or WindowsVolumeManager()
        self.brightness_mgr = brightness_mgr or WindowsBrightnessManager()
        self.power_mgr = power_mgr or WindowsPowerManager()

    def control_volume(self, action: str, steps: int = 5) -> dict[str, Any]:
        """Adjust system volume ('up', 'down', 'mute', 'unmute')."""
        return self.volume_mgr.control_volume(action=action, steps=steps)

    def set_volume_percent(self, level: int) -> dict[str, Any]:
        """Set master system volume to an exact percentage (0..100)."""
        return self.volume_mgr.set_volume_percent(level=level)

    def set_brightness(self, level: int) -> dict[str, Any]:
        """Set primary display brightness to a percentage (0..100)."""
        return self.brightness_mgr.set_brightness(level=level)

    def get_battery_status(self) -> dict[str, Any]:
        """Query real-time battery charge, AC power status, and remaining runtime."""
        return self.power_mgr.get_battery_status()

    def power_action(self, action: str, confirmed: bool = False) -> dict[str, Any]:
        """Perform power action ('lock', 'sleep', 'shutdown', 'restart'). Requires confirmation for shutdown/restart."""
        return self.power_mgr.power_action(action=action, confirmed=confirmed)
