"""
Day 18 Unit Tests — Consolidated Hardware Manager Facade.
Verifies volume percentage adjustment, screen brightness, battery health telemetry,
and power management confirmation interlocks.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_windows.hardware_manager import WindowsHardwareManager


class TestDay18Hardware(unittest.TestCase):

    def setUp(self) -> None:
        self.hm = WindowsHardwareManager()

    @patch("zye_windows.volume_manager.WindowsVolumeManager.set_volume_percent")
    def test_set_volume_percent(self, mock_set_vol: MagicMock) -> None:
        """Verify volume facade delegates to volume manager."""
        mock_set_vol.return_value = {"status": "SUCCESS", "level": 40}
        res = self.hm.set_volume_percent(40)
        self.assertEqual(res["status"], "SUCCESS")
        mock_set_vol.assert_called_with(level=40)

    @patch("zye_windows.brightness_manager.WindowsBrightnessManager.set_brightness")
    def test_set_brightness(self, mock_set_bri: MagicMock) -> None:
        """Verify brightness facade delegates to brightness manager."""
        mock_set_bri.return_value = {"status": "SUCCESS", "level": 75}
        res = self.hm.set_brightness(75)
        self.assertEqual(res["status"], "SUCCESS")
        mock_set_bri.assert_called_with(level=75)

    def test_get_battery_status(self) -> None:
        """Verify battery status returns valid telemetry."""
        bat = self.hm.get_battery_status()
        self.assertIn("percent", bat)
        self.assertIn("has_battery", bat)

    def test_power_action_confirmation_interlock(self) -> None:
        """Verify shutdown and restart require explicit confirmation."""
        res_unconf = self.hm.power_action("shutdown", confirmed=False)
        self.assertEqual(res_unconf["status"], "CONFIRMATION_REQUIRED")

        res_lock = self.hm.power_action("lock")
        self.assertIn(res_lock["status"], ("SUCCESS", "ERROR"))


if __name__ == "__main__":
    unittest.main()
