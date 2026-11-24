"""
Unit tests for ZYE Desktop WebSocket Bridge and Desktop HUD Overlay.
"""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType
from zye_desktop.ws_bridge import DesktopWebSocketBridge, WebSocketBridgeConfig
from zye_reliability.resource_governor import ResourceGovernor


def test_overlay_html_file_structure():
    overlay_path = "desktop/overlay.html"
    assert os.path.exists(overlay_path), f"Overlay file missing at {overlay_path}"
    with open(overlay_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify key architectural elements
    assert "ZYE AI" in content
    assert "Gemini Master Brain" in content
    assert "waveform-canvas" in content
    assert "ws://127.0.0.1:8765" in content
    assert "ram-val" in content
    assert "cpu-val" in content


def test_desktop_bridge_state_transitions_on_bus_events():
    bus = ZyeEventBus()
    governor = ResourceGovernor()
    bridge = DesktopWebSocketBridge(event_bus=bus, governor=governor)

    assert bridge._assistant_state == "IDLE"

    # User starts speech -> LISTENING
    bus.publish(event_type=ZyeEventType.USER_SPEECH_STARTED, source_module="test")
    assert bridge._assistant_state == "LISTENING"

    # Model request starts -> THINKING
    bus.publish(event_type=ZyeEventType.MODEL_REQUEST_STARTED, source_module="test")
    assert bridge._assistant_state == "THINKING"

    # Audio playback starts -> SPEAKING
    bus.publish(event_type=ZyeEventType.AUDIO_PLAYBACK_STARTED, source_module="test")
    assert bridge._assistant_state == "SPEAKING"

    # Audio drained -> IDLE
    bus.publish(event_type=ZyeEventType.AUDIO_PLAYBACK_DRAINED, source_module="test")
    assert bridge._assistant_state == "IDLE"

    # Tool execution started -> EXECUTING_TOOL
    bus.publish(event_type=ZyeEventType.TOOL_EXECUTION_STARTED, source_module="test")
    assert bridge._assistant_state == "EXECUTING_TOOL"


def test_desktop_bridge_handshake_and_commands():
    bus = ZyeEventBus()
    governor = ResourceGovernor()
    bridge = DesktopWebSocketBridge(event_bus=bus, governor=governor)

    # 1. Test initial handshake payload
    init_data = bridge.get_handshake_payload()
    assert init_data["type"] == "init"
    assert init_data["assistant"] == "ZYE AI"
    assert "Gemini" in init_data["brain"]
    assert "metrics" in init_data

    # 2. Test ping response
    pong_data = bridge.process_command("ping")
    assert pong_data is not None
    assert pong_data["type"] == "pong"
    assert "time" in pong_data

    # 3. Test get_status response
    status_data = bridge.process_command("get_status")
    assert status_data is not None
    assert status_data["type"] == "status"
    assert "metrics" in status_data
