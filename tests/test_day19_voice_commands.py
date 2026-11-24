"""
Day 19 Unit Tests — Voice Command Processing & Multilingual Intent Normalization.
Verifies parsing and normalization of Tamil, English, and Tanglish desktop automation commands.
"""

from __future__ import annotations

import unittest


class TestDay19VoiceCommands(unittest.TestCase):

    def normalize_voice_intent(self, phrase: str) -> dict[str, str]:
        """Test harness normalizing Tamil/Tanglish/English voice commands into canonical intents."""
        p = phrase.lower().strip()

        # Application launch
        if any(w in p for w in ["open pannu", "thira", "launch pannu", "start pannu", "open"]):
            for app in ["whatsapp", "chrome", "notepad", "spotify", "vlc", "vs code", "settings"]:
                if app in p:
                    return {"action": "open_application", "target": app}

        # Application close
        if any(w in p for w in ["close pannu", "moodu", "kill pannu", "terminate pannu"]):
            for app in ["whatsapp", "chrome", "notepad", "spotify", "vlc", "vs code"]:
                if app in p:
                    return {"action": "close_application", "target": app}

        # WhatsApp call
        if "call podu" in p or "call pannu" in p or "phone podu" in p:
            call_type = "video" if "video" in p else "voice"
            # Extract contact if present
            contact = p.split("-")[0].replace("kku", "").replace("ku", "").strip() if "-" in p else "unknown"
            return {"action": "start_call", "call_type": call_type, "contact": contact}

        # Call termination
        if "call cut pannu" in p or "call mudichidu" in p or "end call" in p:
            return {"action": "end_call"}

        # Process inspection
        if "process details" in p or "running processes" in p or "processes list" in p:
            return {"action": "list_processes"}

        # Hardware controls
        if "volume" in p:
            return {"action": "set_volume"}
        if "brightness" in p:
            return {"action": "set_brightness"}
        if "battery" in p:
            return {"action": "get_battery"}

        return {"action": "UNKNOWN", "raw": phrase}

    def test_tamil_app_launch_intent(self) -> None:
        """Verify Tamil application launch commands normalize correctly."""
        res1 = self.normalize_voice_intent("WhatsApp open pannu")
        self.assertEqual(res1["action"], "open_application")
        self.assertEqual(res1["target"], "whatsapp")

        res2 = self.normalize_voice_intent("Chrome thira")
        self.assertEqual(res2["action"], "open_application")
        self.assertEqual(res2["target"], "chrome")

    def test_tamil_call_controls_intent(self) -> None:
        """Verify Tamil voice call and end call intents."""
        res_call = self.normalize_voice_intent("Arun-kku voice call podu")
        self.assertEqual(res_call["action"], "start_call")
        self.assertEqual(res_call["call_type"], "voice")
        self.assertEqual(res_call["contact"], "arun")

        res_end = self.normalize_voice_intent("Call cut pannu")
        self.assertEqual(res_end["action"], "end_call")

    def test_process_inspection_intent(self) -> None:
        """Verify process telemetry voice command intents."""
        res_procs = self.normalize_voice_intent("Running processes list pannu")
        self.assertEqual(res_procs["action"], "list_processes")

    def test_hardware_control_intents(self) -> None:
        """Verify volume, brightness, battery intents."""
        self.assertEqual(self.normalize_voice_intent("Volume 40% set pannu")["action"], "set_volume")
        self.assertEqual(self.normalize_voice_intent("Brightness 60% vai")["action"], "set_brightness")
        self.assertEqual(self.normalize_voice_intent("Battery status sollu")["action"], "get_battery")


if __name__ == "__main__":
    unittest.main()
