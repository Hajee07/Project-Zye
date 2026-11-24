"""
ZYE AI — Desktop Loopback WebSocket Event Bridge
================================================

Implements Section 30 of Master Engineering Specification.
Hosts a local loopback WebSocket server (ws://127.0.0.1:8765) to stream:
1. Real-time assistant state (LISTENING, THINKING, SPEAKING, TOOL_EXECUTION).
2. Resource governor telemetry (RAM %, CPU %, ResourceState).
3. Sanitized ZyeEventBus stream for Desktop HUD overlay.
4. Bidirectional control messages (ping, get_status).
Strictly bound to 127.0.0.1 for local isolation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

import websockets
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ZyeEvent, ZyeEventType
from zye_reliability.resource_governor import ResourceGovernor

logger = logging.getLogger("zye.desktop.ws_bridge")


@dataclass(slots=True)
class WebSocketBridgeConfig:
    """Configuration for Desktop WebSocket Bridge."""

    host: str = "127.0.0.1"
    port: int = 8765
    broadcast_interval: float = 1.0


class DesktopWebSocketBridge:
    """
    WebSocket server streaming assistant state and telemetry to the Desktop HUD overlay.
    """

    def __init__(
        self,
        config: Optional[WebSocketBridgeConfig] = None,
        event_bus: Optional[ZyeEventBus] = None,
        governor: Optional[ResourceGovernor] = None,
    ) -> None:
        self.config = config or WebSocketBridgeConfig()
        self.event_bus = event_bus
        self.governor = governor or ResourceGovernor()
        self._clients: Set[Any] = set()
        self._server: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._assistant_state = "IDLE"
        self._lock = threading.Lock()

        if self.event_bus:
            self.event_bus.subscribe_all(self._on_bus_event)

    def _on_bus_event(self, event: ZyeEvent) -> None:
        """Handle event from Unified Event Bus and forward to HUD clients."""
        # Update assistant state according to event type
        if event.event_type == ZyeEventType.USER_SPEECH_STARTED:
            self._assistant_state = "LISTENING"
        elif event.event_type == ZyeEventType.MODEL_REQUEST_STARTED:
            self._assistant_state = "THINKING"
        elif event.event_type == ZyeEventType.AUDIO_PLAYBACK_STARTED:
            self._assistant_state = "SPEAKING"
        elif event.event_type in (ZyeEventType.AUDIO_PLAYBACK_DRAINED, ZyeEventType.USER_SPEECH_COMPLETED):
            self._assistant_state = "IDLE"
        elif event.event_type == ZyeEventType.TOOL_EXECUTION_STARTED:
            self._assistant_state = "EXECUTING_TOOL"

        # Broadcast event to HUD clients
        payload = {
            "type": "event",
            "event_type": event.event_type.value,
            "source": event.source_module,
            "data": event.payload,
            "timestamp": event.timestamp,
        }
        self.broadcast_sync(payload)

    def broadcast_sync(self, message: Dict[str, Any]) -> None:
        """Thread-safe synchronous broadcast to all active WebSocket clients."""
        if not self._clients or not self._loop or not self._loop.is_running():
            return

        msg_str = json.dumps(message)
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is self._loop:
            asyncio.create_task(self._broadcast(msg_str))
        else:
            asyncio.run_coroutine_threadsafe(self._broadcast(msg_str), self._loop)

    async def _broadcast(self, msg_str: str) -> None:
        """Async broadcast helper."""
        if not self._clients:
            return
        dead_clients = set()
        for client in list(self._clients):
            try:
                await client.send(msg_str)
            except Exception:
                dead_clients.add(client)
        self._clients.difference_update(dead_clients)

    def get_handshake_payload(self) -> Dict[str, Any]:
        """Construct initial handshake payload for HUD client."""
        metrics = self.governor.sample_metrics()
        return {
            "type": "init",
            "assistant": "ZYE AI",
            "brain": "Gemini Master Brain (gemini-2.5-pro / live)",
            "state": self._assistant_state,
            "metrics": {
                "ram_percent": metrics.ram_percent,
                "ram_available_mb": metrics.ram_available_mb,
                "cpu_percent": metrics.cpu_percent,
                "resource_state": metrics.state.value,
            },
        }

    def process_command(self, cmd: str) -> Optional[Dict[str, Any]]:
        """Process inbound HUD command deterministically."""
        if cmd == "ping":
            return {"type": "pong", "time": time.time()}
        elif cmd == "get_status":
            m = self.governor.sample_metrics()
            return {
                "type": "status",
                "state": self._assistant_state,
                "metrics": {
                    "ram_percent": m.ram_percent,
                    "cpu_percent": m.cpu_percent,
                    "resource_state": m.state.value,
                },
            }
        return None

    async def _handler(self, websocket: Any) -> None:
        """Handle individual WebSocket client connection."""
        self._clients.add(websocket)
        logger.info("Desktop HUD client connected")

        # Send initial handshake state
        init_payload = self.get_handshake_payload()
        await websocket.send(json.dumps(init_payload))

        try:
            async for raw_msg in websocket:
                try:
                    data = json.loads(raw_msg)
                    cmd = data.get("cmd") or data.get("type")
                    resp = self.process_command(cmd)
                    if resp:
                        await websocket.send(json.dumps(resp))
                except Exception as exc:
                    logger.warning("Error processing client message: %s", exc)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info("Desktop HUD client disconnected")

    async def start(self) -> None:
        """Start the WebSocket server on 127.0.0.1."""
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._server = await websockets.serve(
            self._handler,
            self.config.host,
            self.config.port,
        )
        logger.info("Desktop WebSocket Bridge listening on ws://%s:%d", self.config.host, self.config.port)

    async def stop(self) -> None:
        """Stop server and disconnect clients."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for client in list(self._clients):
            await client.close()
        self._clients.clear()
        logger.info("Desktop WebSocket Bridge stopped.")


__all__ = ["WebSocketBridgeConfig", "DesktopWebSocketBridge"]
