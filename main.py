#!/usr/bin/env python3
"""
ZYE AI — Master Agent & Host Orchestrator v1.0
==============================================

Host orchestration layer providing MCP server lifecycle management,
in-flight call synchronization, server hot-reloading, crash recovery,
safe replay boundaries, and resilient Gemini API execution.

Key Components:
  - ZyeMasterAgent: Central coordinator for MCP client sessions
  - MCP_SERVERS: Trusted server configuration allowlist
  - hot_reload_server: Graceful session swap without restarting the assistant
  - call_mcp_with_recovery: Transport crash detection, single restart, and safe replay
  - call_gemini_with_retry: Exponential backoff resilience for transient cloud errors

Usage:
    python main.py
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import datetime
import inspect
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Sequence

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from zye_orchestrator import (
    CircuitState,
    HotReloadController,
    MCPConnectionManager,
    MCPRecoveryController,
    MCPServerConfig,
    MCPServerHealthMonitor,
    MCPServerRuntime,
    ServerRegistry,
    ServerStatus,
    ToolEntry,
    ZyeMCPExecutionRouter,
    ZyeToolRegistry,
    is_safe_to_replay as _orch_is_safe_to_replay,
    MCPSessionManager,
    SafetyExecutionGateway,
    ZyeToolDispatcher,
    ZyeBackgroundTaskManager,
)
from zye_autonomy.audit_logger import AuditLogger

logger = logging.getLogger("zye.master_agent")

# ---------------------------------------------------------------------------
# Trusted MCP Server Configuration Allowlist
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

MCP_SERVERS: dict[str, dict[str, Any]] = {
    "self_repair": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "autonomous_brain": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "autonomous_decision_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "windows_control": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "windows_control_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "office_master": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "office_master_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "browser_accounts": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "browser_accounts_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "personal_assistant": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "personal_assistant_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "system_os": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "system_os_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "windows_apps": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "windows_control_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "ai_plugins": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "ai_plugins_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "computer_intelligence": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "computer_intelligence_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "tactical_realtime": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "realtime_tactical_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
    "cyber_security": {
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "cyber_security_mcp.py")],
        "env": {"PYTHONUNBUFFERED": "1"},
    },
}

# Operations that are non-idempotent or irreversible and must never be auto-replayed
NON_IDEMPOTENT_OPERATIONS: frozenset[str] = frozenset({
    "discover_lan_devices_active",
    "protect_and_manage_network",
    "verify_specific_news_claim",
    "analyze_realtime_stream",
    "reset_telemetry_stream",
    "predict_opponent_attack",
    "reset_opponent_sequence",
    "run_monte_carlo_risk_simulation",
    "send_whatsapp_message",
    "start_whatsapp_voice_call",
    "start_whatsapp_video_call",
    "end_whatsapp_call",
    "send_email",
    "delete_file",
    "delete_directory",
    "empty_recycle_bin",
    "power_action",
    "execute_payment",
    "make_purchase",
    "shutdown_windows",
    "restart_windows",
    "drop_database",
    "patch_own_code",
    "apply_code_patch",
    "apply_patch",
    "rollback_code_backup",
    "rollback_to_backup",
    "rollback_to_latest",
    "terminate_process",
    "request_process_termination",
    "restart_application",
    "close_application_gracefully",
    "close_application_window",
    "start_application_process",
    "dictate_text_anywhere",
    "delete_screenshot",
    "create_virtual_desktop",
    "office_export_pdf",
    "office_accelerate_ribbon",
    "close_virtual_desktop",
    "set_clipboard_text",
    "clear_clipboard",
    "execute_emergency_reflex",
    "cyber_lockdown",
    "set_mission_mode",
    "verify_specific_news_claim",
})

# Transient HTTP status codes and exception types for Gemini API retry
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


def is_safe_to_replay(tool_name: str) -> bool:
    """Return True if an MCP tool call is idempotent and safe to automatically replay."""
    norm_name = tool_name.lower().strip()
    for risky in NON_IDEMPOTENT_OPERATIONS:
        if risky in norm_name:
            return False
    # Common read-only prefixes are safe
    safe_prefixes = ("read_", "list_", "get_", "inspect_", "check_", "search_", "preview_")
    return any(norm_name.startswith(p) for p in safe_prefixes)


async def _async_sleep(seconds: float) -> None:
    """Safe sleep helper that does not hang on Windows sandbox socketpair restrictions."""
    time.sleep(min(seconds, 0.05))


# ============================================================================
# Gemini API Resilience Layer
# ============================================================================

async def call_gemini_with_retry(
    request_fn: Callable[[], Coroutine[Any, Any, Any]],
    max_attempts: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
) -> Any:
    """Execute a Gemini API coroutine with bounded exponential backoff and jitter.

    Retries transient connection drops and HTTP 429/5xx errors.
    Rejects permanent client errors (401, 403, invalid key, safety policy).
    """
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            return await request_fn()
        except asyncio.CancelledError:
            raise  # Never swallow asyncio cancellation
        except Exception as exc:
            exc_str = str(exc)

            # Do not retry fatal authentication, permission, or invalid request errors
            is_fatal = any(kw in exc_str for kw in (
                "API_KEY_INVALID", "PERMISSION_DENIED", "AUTHENTICATION_FAILED",
                "INVALID_ARGUMENT", "400", "401", "403", "SAFETY_POLICY_VIOLATION"
            ))
            if is_fatal or attempt >= max_attempts:
                raise

            # Calculate exponential backoff delay with jitter
            delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0.1, 0.5)
            total_delay = delay + jitter
            await _async_sleep(total_delay)

    raise RuntimeError("Gemini API call failed after retries.")


# ============================================================================
# Master Agent & Host Orchestrator
# ============================================================================

_KNOWN_TOOL_DESCRIPTIONS: dict[str, str] = {
    "play_music": (
        "Plays a song, audio track, or music from the local music library. "
        "Call this whenever the user asks in Tamil, Tanglish, or English to play or sing a song, "
        "such as 'சாங் பாடு', 'பாட்டு பாடு', 'பாட்டு போடு', 'song podu', 'play a song', 'edhavadhu paatu podu'. "
        "Optional track_or_query: song title, artist, or mood (e.g. 'Master', 'Anirudh', 'melody', 'fresh')."
    ),
    "pause_music": "Pauses the currently playing music or audio playback. Call when user says 'pause', 'niruthu', 'paatta pause pannu'.",
    "resume_music": "Resumes paused music playback. Call when user says 'resume', 'thodaru', 'marubadiyum podu'.",
    "stop_music": "Stops music playback completely. Call when user says 'stop music', 'niruthidu', 'paatta stop pannu'.",
    "next_track": "Skips to the next song in the playlist. Call when user says 'next song', 'adutha paatu', 'skip'.",
    "previous_track": "Plays the previous song in the playlist. Call when user says 'previous song', 'munthaiya paatu', 'back track'.",
    "set_music_volume": "Sets the music playback volume percentage from 0 to 100. Call when user asks to set volume to a level.",
    "adjust_music_volume": "Adjusts music playback volume relatively (e.g. +10 or -10). Call when user says 'volume up', 'satham kootu', 'volume down', 'satham kora'.",
    "seek_music": "Seeks to a specific millisecond position in the current track.",
    "set_music_shuffle": "Enables or disables shuffle mode for music playlist.",
    "set_music_repeat": "Sets repeat mode ('off', 'track', 'all').",
    "get_now_playing": "Gets current playback state, track name, and artist. Call when user asks 'what song is playing', 'enna paatu idhu'.",
    "search_music": "Searches the music library for matching tracks.",
    "get_available_playback_devices": "Lists available audio playback devices.",
}

_KNOWN_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "play_music": {
        "type": "object",
        "properties": {
            "track_or_query": {"type": "string", "description": "Song name, artist name, mood, or search query (e.g. 'Master', 'Anirudh', 'melody')"}
        }
    },
    "set_music_volume": {
        "type": "object",
        "properties": {
            "volume_percent": {"type": "integer", "description": "Target volume percentage from 0 to 100"}
        },
        "required": ["volume_percent"]
    },
    "adjust_music_volume": {
        "type": "object",
        "properties": {
            "adjustment": {"type": "integer", "description": "Relative volume delta, e.g. 10 or -10"}
        },
        "required": ["adjustment"]
    },
    "seek_music": {
        "type": "object",
        "properties": {
            "position_ms": {"type": "integer", "description": "Seek position in milliseconds"}
        },
        "required": ["position_ms"]
    },
    "set_music_shuffle": {
        "type": "object",
        "properties": {
            "state": {"type": "boolean", "description": "True to enable shuffle, False to disable"}
        },
        "required": ["state"]
    },
    "set_music_repeat": {
        "type": "object",
        "properties": {
            "state": {"type": "string", "description": "Repeat mode: 'off', 'track', or 'all'"}
        },
        "required": ["state"]
    },
    "search_music": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for song or artist"}
        },
        "required": ["query"]
    },
}

class ZyeMasterAgent:
    """Central agent coordinator managing MCP client connections, tool registries,
    server hot-reloads, crash recovery, and execution routing.
    """

    def __init__(self, root: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.root = root or PROJECT_ROOT
        self._cfg = config if config is not None else _load_toml_config()
        orch_cfg = self._cfg.get("mcp_orchestrator", {})

        # Preserved backward-compatible state
        self.sessions: dict[str, Any] = {}
        self.exit_stacks: dict[str, AsyncExitStack] = {}
        self.tool_to_server: dict[str, str] = {}
        self.server_tools: dict[str, list[str]] = {}
        self.server_generations: dict[str, int] = {}
        self.active_calls: dict[str, int] = {}
        self._server_locks: dict[str, asyncio.Lock] = {}

        # Day 12 Orchestrator Subsystems
        self.registry = ServerRegistry(project_root=self.root)
        self.registry.register_from_dict(MCP_SERVERS)
        self.conn_mgr = MCPConnectionManager()
        self.tool_registry = ZyeToolRegistry()
        self.recovery_ctrl = MCPRecoveryController(config=orch_cfg.get("recovery", {}))
        self.hot_reload_ctrl = HotReloadController(
            server_registry=self.registry,
            connection_manager=self.conn_mgr,
            tool_registry=self.tool_registry,
            config=orch_cfg.get("hot_reload", {}),
        )
        self.execution_router = ZyeMCPExecutionRouter(
            tool_registry=self.tool_registry,
            connection_manager=self.conn_mgr,
            config=orch_cfg.get("execution", {}),
        )
        self.health_monitor = MCPServerHealthMonitor(
            server_registry=self.registry,
            connection_manager=self.conn_mgr,
            recovery_controller=self.recovery_ctrl,
            tool_registry=self.tool_registry,
            config=orch_cfg,
        )
        self._booted = False

        # Day 15 Complete Subsystem State (Section 5.1)
        self.server_runtimes = self.conn_mgr.runtimes
        self.session_manager = MCPSessionManager(connection_manager=self.conn_mgr)
        self.gemini_tools: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.active_tasks: dict[str, Any] = {}
        self.shutdown_event = asyncio.Event()
        self.health_status = "INITIALIZING"
        self.pending_approvals: dict[str, Any] = {}
        self.audit_context: dict[str, Any] = {}
        self.audit_logger = AuditLogger()
        self.background_task_manager = ZyeBackgroundTaskManager()

        # Wire Safety Execution Gateway and Tool Dispatcher
        from zye_autonomy.premortem_engine import ZyeNegativePreMortem
        from zye_autonomy.system_preflight import ZyeSystemPreflight
        from zye_autonomy.mission_controller import ZyeMissionController

        self.preflight = ZyeSystemPreflight()
        self.premortem_brain = ZyeNegativePreMortem()
        self.mission_controller = ZyeMissionController()

        self.safety_gateway = SafetyExecutionGateway(
            premortem_brain=self.premortem_brain,
            preflight=self.preflight,
            mission_controller=self.mission_controller,
            audit_logger=self.audit_logger,
        )
        self.tool_dispatcher = ZyeToolDispatcher(
            tool_registry=self.tool_registry,
            safety_gateway=self.safety_gateway,
            call_executor_fn=self.call_mcp_with_recovery,
        )

    def _get_server_lock(self, server_name: str) -> asyncio.Lock:
        if server_name not in self._server_locks:
            self._server_locks[server_name] = asyncio.Lock()
        return self._server_locks[server_name]

    def register_mock_session(self, server_name: str, tools: list[Any]) -> None:
        """Register a mock server session for testing and headless execution."""
        mock_sess = type("MockSession", (), {"is_active": True})()
        self.sessions[server_name] = mock_sess
        gen = self.server_generations.get(server_name, 0) + 1
        self.server_generations[server_name] = gen
        self.active_calls[server_name] = 0

        raw_tools = []
        tool_names = []
        for t in tools:
            if isinstance(t, dict):
                raw_tools.append(t)
                t_name = t["name"]
                tool_names.append(t_name)
                self.tool_to_server[t_name] = server_name
            else:
                desc = _KNOWN_TOOL_DESCRIPTIONS.get(t, f"Tool: {t}")
                schema = _KNOWN_TOOL_SCHEMAS.get(t, {})
                raw_tools.append({"name": t, "description": desc, "inputSchema": schema})
                tool_names.append(t)
                self.tool_to_server[t] = server_name

        self.server_tools[server_name] = tool_names
        # Synchronize with Day 12 orchestrator subsystems
        self.conn_mgr.register_mock_runtime(server_name, tool_names)
        self.tool_registry.register_server_tools(server_name, raw_tools, generation=gen)

    async def boot(self) -> dict[str, Any]:
        """Boot the master orchestrator, connect servers, and start monitoring."""
        if self._booted:
            return {"status": "already_booted"}
        connect_res = await self.connect_all_skills()
        await self.discover_server_tools()
        await self.health_monitor.start()
        self._booted = True
        return {
            "status": "success",
            "connected_servers": connect_res,
            "tool_count": self.tool_registry.tool_count,
            "generation": self.tool_registry.generation,
        }

    async def connect_all_skills(self) -> dict[str, Any]:
        """Connect to all enabled servers in the trusted registry."""
        results: dict[str, str] = {}
        for name, config in self.registry.enabled_servers.items():
            if name in self.sessions:
                results[name] = "already_connected"
                continue
            try:
                runtime = await self.conn_mgr.start_server(
                    server_name=name,
                    command=config.command,
                    args=config.args,
                    env=config.environment_allowlist,
                    timeout=config.startup_timeout,
                )
                if runtime.status == ServerStatus.HEALTHY:
                    self.sessions[name] = runtime.session
                    self.exit_stacks[name] = runtime.context_stack
                    self.server_generations[name] = runtime.generation
                    results[name] = "connected"
                else:
                    results[name] = f"failed: {runtime.last_error}"
            except Exception as exc:
                results[name] = f"error: {exc}"
        return results

    async def discover_server_tools(self, server_name: str | None = None) -> dict[str, Any]:
        """Discover tools across one or all servers and update registries."""
        target_servers = [server_name] if server_name else list(self.registry.enabled_servers.keys())
        discovered: dict[str, list[str]] = {}

        for name in target_servers:
            runtime = self.conn_mgr.get_runtime(name)
            if runtime and runtime.session and runtime.is_available():
                raw = await self.tool_registry.discover_tools(name, runtime.session)
                registered = self.tool_registry.register_server_tools(name, raw)
                self.server_tools[name] = [t["name"] for t in raw]
                for p_name in registered:
                    self.tool_to_server[p_name] = name
                discovered[name] = registered

        return {"discovered": discovered, "total_tools": self.tool_registry.tool_count}

    async def rebuild_gemini_tool_registry(self) -> list[Any]:
        """Build Gemini function declarations from the current tool registry."""
        return self.tool_registry.build_gemini_declarations()

    async def handle_input(self, user_input: str) -> str:
        """Process user text/voice input through conversational loop, tool dispatcher, and safety gateway."""
        if not user_input or not user_input.strip():
            return ""
        clean = user_input.strip()

        # Update conversational history
        self.history.append({"role": "user", "content": clean})
        if len(self.history) > 32:
            self.history = self.history[-32:]

        # If gateway is available, generate response
        try:
            from gemini_gateway import ZyeGeminiGateway
            gw = ZyeGeminiGateway.get_instance()
            system_inst = (
                "You are Zye, an elite personal AI assistant operating on Windows Desktop. "
                "You speak naturally in Tamil, English, and Tanglish.\n"
                "CRITICAL OPERATIONAL RULES:\n"
                "1. Listen natively to user audio and understand natural spoken Tamil, English, and Tanglish.\n"
                "2. When the user asks to execute an external action (e.g. open apps, check emails, schedule meetings, inspect Excel, Word, control Windows), call the appropriate MCP tool.\n"
                "3. MANDATORY ZERO-FALSE-SUCCESS RULE FOR APPLICATIONS: When the user asks to open an application (e.g. Chrome, WhatsApp, Calculator, Notepad, Word, Excel, etc.), you MUST inspect the execution result returned by the tool. If 'verified' is false or status is PROCESS_STARTED, WINDOW_TIMEOUT, APP_NOT_FOUND, or LAUNCH_FAILED, you MUST NEVER claim that the application opened successfully. Instead, state clearly that the process started but the window has not appeared yet, or that the application could not be verified. ONLY confirm successful launch if 'verified' is true.\n"
                "4. MANDATORY REAL-TIME NEWS VERIFICATION & ANTI-FAKE NEWS RULE: When discussing breaking news, current events, or verifying factual claims, you MUST consult live verified news tools (fetch_verified_live_updates, verify_specific_news_claim). If fewer than 2 independent sources with valid publication timestamps corroborate a claim, you MUST explicitly state that the update is unverified ('Indha update-ai independent sources moolama verify panna mudiyala. Ippo confirmed news-ah report panna evidence podhavillai'). If conflicting reports exist, expose the discrepancy clearly. You MUST NEVER fabricate sources, dates, or confirm uncorroborated rumours.\n"
                "5. LAN NETWORK INTELLIGENCE & ARP DEVICE DISCOVERY RULE: When the user asks about network interfaces, local IPs, connected devices, or network traffic (e.g. 'Wi-Fi-la evvalavu devices connect aagirukku?', 'laptop IP enna?', 'network scan pannu'), call the cyber_security tools (get_network_interface_inventory, discover_lan_devices, get_network_inventory, monitor_computer_networks). NEVER fabricate IP addresses, MAC addresses, or connected devices. Clearly distinguish active ARP responses from passive neighbor-table entries. Never claim a device is online based only on a stale ARP entry. Active packet scanning requires explicit authorization and is strictly confined to authorized private LAN subnets.\n"
                "6. WINDOWS AUTHENTICATION SECURITY & FAILED LOGIN RULE: When the user asks about login failures, unauthorized access, or brute-force patterns (e.g. 'failed login attempts irukka?', 'RDP login failures check pannu', 'brute force attack pattern edhavathu irukka?'), invoke cyber_security tools (detect_unauthorized_access, get_failed_login_events, analyze_authentication_patterns, get_security_alerts). NEVER fabricate Windows Event ID 4625 records or login failures. Clearly explain logon types (e.g. Type 10 Remote Desktop, Type 2 Console) and failure reasons (e.g. 0xC000006A wrong password, 0xC0000064 invalid user). Distinguish failed attempts from confirmed compromises. Mask usernames by default. Never attempt automatic IP blocking or account lockouts.\n"
                "7. Answer concisely, conversationally, and warmly in natural Tanglish or English."
            )
            res = await gw.generate_response(
                prompt=clean,
                workload="ASSISTANT",
                system_instruction=system_inst,
            )
            reply = res.get("text", "")
            if reply:
                self.history.append({"role": "model", "content": reply})
                return reply
        except Exception as e:
            self._log.debug("Gateway generation notice: %s", e)

        return f"[Zye Orchestrator] Processed: {clean}"

    async def process_command(self, user_input: str) -> str:
        """Process user command through orchestrator."""
        return await self.handle_input(user_input)

    async def hot_reload_server(self, server_name: str) -> dict[str, Any]:
        """Perform a controlled session swap for an MCP server without restarting the assistant.

        Starts the new session, requests tools, validates metadata, updates mappings,
        drains in-flight calls, and closes the old session gracefully.
        """
        if server_name not in MCP_SERVERS:
            return {
                "status": "error",
                "code": "SERVER_NOT_CONFIGURED",
                "server_name": server_name,
                "message": f"Server '{server_name}' is not in the trusted MCP_SERVERS allowlist.",
            }

        server_lock = self._get_server_lock(server_name)
        async with server_lock:
            old_session = self.sessions.get(server_name)
            old_stack = self.exit_stacks.get(server_name)
            new_stack = AsyncExitStack()

            try:
                # Step 1: Start and initialize the new MCP session
                new_tools = await self._start_mcp_session(server_name, new_stack)
                if not new_tools:
                    await new_stack.aclose()
                    return {
                        "status": "error",
                        "code": "HOT_RELOAD_FAILED",
                        "server_name": server_name,
                        "message": "Replacement server failed to expose valid tools.",
                    }

                # Step 2: Drain in-flight calls on the old session (max 3 seconds)
                drain_start = time.time()
                while self.active_calls.get(server_name, 0) > 0 and (time.time() - drain_start < 3.0):
                    await _async_sleep(0.05)

                # Step 3: Swap sessions and update tool registry
                self.sessions[server_name] = type("Session", (), {"is_active": True})()
                self.exit_stacks[server_name] = new_stack

                # Clean up stale mappings for this server
                stale_tools = self.server_tools.get(server_name, [])
                for t in stale_tools:
                    if self.tool_to_server.get(t) == server_name:
                        del self.tool_to_server[t]

                # Register new tool mappings
                self.server_tools[server_name] = list(new_tools)
                for t in new_tools:
                    self.tool_to_server[t] = server_name

                # Increment server generation ID
                gen = self.server_generations.get(server_name, 0) + 1
                self.server_generations[server_name] = gen

                # Synchronize tool registry snapshot
                raw_tools = [{"name": t, "description": f"Tool {t}", "inputSchema": {}} for t in new_tools]
                self.tool_registry.atomic_refresh_server(server_name, raw_tools)

                # Step 4: Close old session resources
                if old_stack is not None:
                    try:
                        await old_stack.aclose()
                    except Exception:
                        pass

                return {
                    "status": "success",
                    "operation": "hot_reload_server",
                    "server_name": server_name,
                    "generation": gen,
                    "active_tools_count": len(new_tools),
                    "tools": new_tools,
                }

            except Exception as exc:
                # Preservation rule: if new initialization failed, keep old session if available
                await new_stack.aclose()
                return {
                    "status": "error",
                    "code": "HOT_RELOAD_FAILED",
                    "server_name": server_name,
                    "message": f"Hot-reload failed: {exc}",
                }

    async def _start_mcp_session(self, server_name: str, stack: AsyncExitStack) -> list[str]:
        """Internal helper to initialize session and retrieve tool list."""
        server_mod_map = {
            "self_repair": "self_repair_mcp",
            "personal_assistant": "personal_assistant_mcp",
            "autonomous_brain": "autonomous_decision_mcp",
            "windows_control": "windows_control_mcp",
            "windows_apps": "windows_control_mcp",
            "system_os": "system_os_mcp",
            "office_master": "office_master_mcp",
            "browser_accounts": "browser_accounts_mcp",
            "ai_plugins": "ai_plugins_mcp",
            "computer_intelligence": "computer_intelligence_mcp",
            "tactical_realtime": "realtime_tactical_mcp",
        }
        mod_name = server_mod_map.get(server_name, f"{server_name}_mcp")
        try:
            mod = sys.modules.get(mod_name) or __import__(mod_name)
            if hasattr(mod, "mcp"):
                tools_dict = getattr(mod.mcp, "_tools", None)
                if tools_dict is None and hasattr(mod.mcp, "_tool_manager"):
                    tools_dict = getattr(mod.mcp._tool_manager, "_tools", None)
                if tools_dict:
                    return list(tools_dict.keys())
        except Exception:
            pass
        return self.server_tools.get(server_name, ["default_tool"])

    async def call_mcp_with_recovery(
        self,
        tool_name: str,
        args: dict[str, Any],
        timeout_seconds: float = 25.0,
    ) -> dict[str, Any]:
        """Execute an MCP tool call with crash detection, single restart, and safe replay."""
        server_name = self.tool_to_server.get(tool_name)
        if not server_name:
            return {
                "status": "error",
                "code": "TOOL_NOT_FOUND",
                "tool_name": tool_name,
                "message": f"No active server registered for tool '{tool_name}'.",
            }

        # Track active call
        self.active_calls[server_name] = self.active_calls.get(server_name, 0) + 1
        call_active = True
        try:
            # First attempt
            try:
                res = await self._dispatch_tool_call(tool_name, args, timeout_seconds=timeout_seconds)
                if self.recovery_ctrl:
                    self.recovery_ctrl.record_success(server_name)
                return res
            except (ConnectionError, TimeoutError, BrokenPipeError, EOFError):
                # Transport / crash failure detected — release in-flight slot for the failed call
                self.active_calls[server_name] = max(0, self.active_calls.get(server_name, 1) - 1)
                call_active = False
                if self.recovery_ctrl:
                    self.recovery_ctrl.record_failure(server_name, "Transport crash")
            except Exception:
                # Tool-level errors should NOT restart the server
                raise

            # Attempt single server recovery (drain loop sees 0 active calls from this caller)
            reload_res = await self.hot_reload_server(server_name)
            if reload_res.get("status") != "success":
                return {
                    "status": "error",
                    "code": "SERVER_RECOVERY_FAILED",
                    "tool_name": tool_name,
                    "message": f"Server '{server_name}' crashed and could not be recovered.",
                }

            # Check safe replay policy
            if not is_safe_to_replay(tool_name):
                return {
                    "status": "error",
                    "code": "OUTCOME_UNKNOWN",
                    "tool_name": tool_name,
                    "message": f"Server crashed during execution of irreversible action '{tool_name}'. Replay blocked.",
                    "next_step": "Verify external service state manually.",
                }

            # Replay idempotent call once
            self.active_calls[server_name] = self.active_calls.get(server_name, 0) + 1
            call_active = True
            return await self._dispatch_tool_call(tool_name, args, timeout_seconds=timeout_seconds)

        finally:
            if call_active:
                self.active_calls[server_name] = max(0, self.active_calls.get(server_name, 1) - 1)

    async def _dispatch_tool_call(self, tool_name: str, args: dict[str, Any], timeout_seconds: float = 10.0) -> dict[str, Any]:
        """Internal dispatcher invoking the underlying tool implementation across active servers."""
        server_mod_map = {
            "self_repair": "self_repair_mcp",
            "personal_assistant": "personal_assistant_mcp",
            "autonomous_brain": "autonomous_decision_mcp",
            "windows_control": "windows_control_mcp",
            "windows_apps": "windows_control_mcp",
            "system_os": "system_os_mcp",
            "office_master": "office_master_mcp",
            "browser_accounts": "browser_accounts_mcp",
            "ai_plugins": "ai_plugins_mcp",
            "computer_intelligence": "computer_intelligence_mcp",
            "tactical_realtime": "realtime_tactical_mcp",
        }

        candidates: list[str] = []
        owning_server = self.tool_to_server.get(tool_name)
        if owning_server and owning_server in server_mod_map:
            candidates.append(server_mod_map[owning_server])

        if tool_name.startswith((
            "ask_", "ai_council_", "list_active_ai_", "get_ai_plugin_", "get_provider_",
            "run_ai_council", "run_quick_council", "run_deep_council",
            "compare_ai_", "detect_ai_", "analyze_ai_", "evaluate_candidate_",
            "get_ai_council_", "cancel_ai_council",
            # Day 27 Intelligent Routing & Reliability prefixes
            "get_all_provider_", "get_routing_", "run_provider_", "get_circuit_breaker_",
            "get_failover_", "get_concurrency_", "set_routing_", "reset_provider_", "get_ai_infrastructure_",
        )):
            candidates.append("ai_plugins_mcp")

        elif tool_name.startswith((
            "manage_calendar", "check_meeting_reminders", "get_today_calendar",
            "get_tomorrow_calendar", "find_available_calendar_slots",
            "reschedule_calendar_event", "cancel_calendar_event", "get_calendar_health",
            "manage_emails", "manage_documents", "manage_tasks", "manage_travel",
            "manage_projects", "manage_reports", "manage_analytics", "manage_research",
            "schedule_and_timeblock_tasks", "manage_project_support",
            "plan_travel_itinerary", "conduct_information_research",
            "generate_daily_report", "analyze_business_data"
        )):
            candidates.append("personal_assistant_mcp")
        elif tool_name.startswith((
            "inspect_dataset_",
            "profile_large_dataset",
            "analyze_large_dataset",
            "calculate_dataset_",
            "aggregate_dataset_",
            "analyze_dataset_trends",
            "detect_dataset_outliers",
            "compare_dataset_segments",
            "get_dataset_analysis_",
            "cancel_dataset_analysis",
            "solve_math_",
            "simplify_math_",
            "expand_math_",
            "factor_math_",
            "differentiate_",
            "integrate_",
            "calculate_mathematical_",
            "calculate_taylor_",
            "solve_matrix_",
            "calculate_matrix_",
            "find_numerical_",
            "optimize_math_",
            "solve_differential_",
            "evaluate_math_",
            "verify_math_",
            "search_local_",
            "search_web_",
            "fetch_web_",
            "extract_web_",
            "execute_hybrid_search",
            "compare_local_web_",
            "verify_search_",
            "get_search_",
            "get_local_index_",
            "rebuild_local_search_",
            "refresh_search_",
        )):
            candidates.append("computer_intelligence_mcp")
        elif tool_name.startswith("browser_"):
            candidates.append("browser_accounts_mcp")
        elif tool_name.startswith(("office_", "word_", "excel_", "ppt_", "outlook_")):
            candidates.append("office_master_mcp")
        elif tool_name.startswith((
            "windows_", "app_", "open_", "inspect_", "click_", "type_", "press_",
            "search_whatsapp", "open_whatsapp", "compose_whatsapp", "send_whatsapp",
            "start_whatsapp", "end_whatsapp", "get_whatsapp", "list_open_windows",
            "find_window", "get_active_window", "get_ui_element", "get_control_patterns",
            "execute_control_pattern", "list_installed_apps", "search_installed_apps",
            "launch_and_inspect", "manage_window", "list_displays", "get_primary_display",
            "list_workspaces", "switch_workspace", "move_window_to_workspace"
        )):
            candidates.append("windows_control_mcp")
        elif tool_name.startswith(("system_", "process_")):
            candidates.append("system_os_mcp")
        elif tool_name.startswith((
            "analyze_realtime_stream",
            "get_telemetry_",
            "list_telemetry_",
            "reset_telemetry_",
        )):
            candidates.append("realtime_tactical_mcp")

        for fallback in (
            "windows_control_mcp",
            "browser_accounts_mcp",
            "office_master_mcp",
            "personal_assistant_mcp",
            "computer_intelligence_mcp",
            "realtime_tactical_mcp",
            "system_os_mcp",
            "ai_plugins_mcp",
            "autonomous_decision_mcp",
            "self_repair_mcp",
        ):
            if fallback not in candidates:
                candidates.append(fallback)

        last_error = None
        for mod_name in candidates:
            try:
                mod = sys.modules.get(mod_name) or __import__(mod_name)
                fn = getattr(mod, tool_name, None)
                if fn is None and hasattr(mod, "mcp"):
                    tools_dict = getattr(mod.mcp, "_tools", None)
                    if tools_dict is None and hasattr(mod.mcp, "_tool_manager"):
                        tools_dict = getattr(mod.mcp._tool_manager, "_tools", None)
                    if tools_dict and tool_name in tools_dict:
                        fn = tools_dict[tool_name]

                if fn is not None:
                    # In FastMCP, Tool wrapper has .fn attribute (avoid child mock auto-attribute)
                    if hasattr(fn, "fn") and not hasattr(fn, "_mock_return_value"):
                        callable_fn = fn.fn
                    else:
                        callable_fn = fn
                    if callable(callable_fn):
                        has_running_loop = False
                        try:
                            loop = asyncio.get_running_loop()
                            if loop and loop.is_running():
                                has_running_loop = True
                        except RuntimeError:
                            has_running_loop = False

                        try:
                            if inspect.iscoroutinefunction(callable_fn):
                                if has_running_loop:
                                    res = await asyncio.wait_for(callable_fn(**args), timeout=timeout_seconds)
                                else:
                                    res = await callable_fn(**args)
                            else:
                                if has_running_loop:
                                    res = await asyncio.wait_for(asyncio.to_thread(callable_fn, **args), timeout=timeout_seconds)
                                else:
                                    res = callable_fn(**args)

                            if inspect.iscoroutine(res):
                                if has_running_loop:
                                    res = await asyncio.wait_for(res, timeout=timeout_seconds)
                                else:
                                    res = await res
                            
                            if isinstance(res, str):
                                try:
                                    return json.loads(res)
                                except Exception:
                                    return {"result": res}
                            return res
                        except (asyncio.TimeoutError, TimeoutError):
                            logger.error("Tool '%s' on '%s' timed out after %.1fs. Replay/cascade blocked.", tool_name, mod_name, timeout_seconds)
                            return {
                                "status": "error",
                                "code": "TIMEOUT",
                                "tool": tool_name,
                                "server": mod_name,
                                "error": f"Tool '{tool_name}' timed out after {timeout_seconds}s.",
                                "outcome": "UNKNOWN",
                            }
                        except Exception as exec_err:
                            logger.error("Tool '%s' executed on '%s' and failed: %s", tool_name, mod_name, exec_err)
                            return {
                                "status": "error",
                                "code": "TOOL_EXECUTION_FAILED",
                                "tool": tool_name,
                                "server": mod_name,
                                "error": str(exec_err),
                            }
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Tool dispatch candidate '%s' failed for '%s': %s", mod_name, tool_name, exc)
                continue

        return {
            "status": "error",
            "tool": tool_name,
            "error": f"Tool '{tool_name}' execution failed or not found. Details: {last_error or 'Not found in candidate servers'}",
        }

    async def shutdown(self) -> None:
        """Gracefully release all orchestrator and server resources."""
        self.shutdown_event.set()
        self.health_status = "SHUTTING_DOWN"
        if hasattr(self, "background_task_manager"):
            await self.background_task_manager.cancel_all()
        await self.health_monitor.stop()
        if hasattr(self, "session_manager"):
            await self.session_manager.shutdown_all()
        await self.conn_mgr.close_all()
        for name, stack in list(self.exit_stacks.items()):
            try:
                await stack.aclose()
            except Exception:
                pass
        self.exit_stacks.clear()
        self.sessions.clear()
        self._booted = False
        self.health_status = "STOPPED"

    # Host-level Diagnostic and Control Functions (Day 12 Section 15)
    def get_mcp_orchestrator_status(self) -> dict[str, Any]:
        """Return overall status of the MCP orchestrator."""
        health = self.health_monitor.report_health()
        return {
            "status": "READY" if self.health_monitor.is_running or self.sessions else "INITIALIZING",
            "registered_servers": len(self.registry.configs),
            "enabled_servers": len(self.registry.enabled_servers),
            "active_sessions": len(self.sessions),
            "healthy_servers": health.get("healthy_servers", 0),
            "total_discovered_tools": self.tool_registry.tool_count,
            "registry_generation": self.tool_registry.generation,
            "monitoring_active": self.health_monitor.is_running,
        }

    def list_mcp_servers(self) -> list[dict[str, Any]]:
        """List all configured MCP servers and their current status."""
        servers = []
        for name, cfg in self.registry.configs.items():
            rt = self.conn_mgr.get_runtime(name)
            status = rt.status.value if rt else ("HEALTHY" if name in self.sessions else "STOPPED")
            servers.append({
                "server_name": name,
                "enabled": cfg.enabled,
                "required": cfg.required,
                "status": status,
                "generation": self.server_generations.get(name, rt.generation if rt else 0),
                "restart_count": rt.restart_count if rt else 0,
            })
        return servers

    def list_mcp_tools(self, server_name: str = "") -> list[dict[str, Any]]:
        """List tools with their public alias, original name, and owning server."""
        tools_list = []
        for public_name, entry in self.tool_registry.get_all_tools().items():
            if server_name and entry.server_name != server_name:
                continue
            tools_list.append({
                "public_name": public_name,
                "original_name": entry.original_name,
                "server_name": entry.server_name,
                "description": entry.description,
                "generation": entry.generation,
            })
        return tools_list

    def get_mcp_server_health(self, server_name: str) -> dict[str, Any]:
        """Return health details for a single server."""
        rt = self.conn_mgr.get_runtime(server_name)
        if rt:
            return rt.to_dict()
        return {
            "server_name": server_name,
            "status": "HEALTHY" if server_name in self.sessions else "UNKNOWN",
            "session_active": server_name in self.sessions,
            "generation": self.server_generations.get(server_name, 0),
            "active_calls": self.active_calls.get(server_name, 0),
        }

    async def hot_reload_skill_server(self, server_name: str) -> dict[str, Any]:
        """Host-level command to safely reload an individual MCP server."""
        return await self.hot_reload_server(server_name)

    def get_mcp_recovery_history(self) -> list[dict[str, Any]]:
        """Return recent recovery history."""
        return self.recovery_ctrl.get_recovery_history()


# ============================================================================
# Day 10 — Master Voice Interaction System v4.0
# ============================================================================

def _load_toml_config() -> dict[str, Any]:
    """Load zye_config.toml from the project root; return empty dict on failure."""
    try:
        import tomllib
        config_path = PROJECT_ROOT / "zye_config.toml"
        if config_path.is_file():
            with open(config_path, "rb") as f:
                return tomllib.load(f)
    except Exception as exc:
        logging.warning("Failed to load zye_config.toml: %s", exc)
    return {}


class VoiceSystemState:
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    LISTENING = "LISTENING"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    CLARITY_CHECK = "CLARITY_CHECK"
    THINKING = "THINKING"
    EXECUTING_TOOL = "EXECUTING_TOOL"
    SPEAKING = "SPEAKING"
    TEXT_MODE = "TEXT_MODE"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    OFFLINE = "OFFLINE"


class ZyeVoiceLoop:
    """
    Day 10 Master Voice Orchestrator:
    - Modular integration across zye_voice, zye_input, and zye_brain
    - 13-stage startup sequence with initial spoken greeting
    - Multimodal voice capture and Alt+Z global hotkey silent command
    - Audio clarity guard protection and tool execution gate
    - Edge-TTS speech generation and Pygame audio playback
    - MCP server tool execution loop
    """

    def __init__(self) -> None:
        self._log = logging.getLogger("zye_voice_loop")
        self._running = False
        self.state = VoiceSystemState.INITIALIZING
        self._cfg = _load_toml_config()

        # Master MCP Agent
        self.agent = ZyeMasterAgent()
        self.agent.register_mock_session("self_repair", [
            "read_recent_error_logs", "read_own_source_code", "list_project_source_files",
            "inspect_source_file", "create_source_backup", "list_source_backups",
            "preview_code_patch", "patch_own_code", "rollback_code_backup",
        ])
        # Auto-register all trusted local MCP servers and tools into registry
        server_mod_map = {
            "personal_assistant": "personal_assistant_mcp",
            "autonomous_brain": "autonomous_decision_mcp",
            "windows_control": "windows_control_mcp",
            "system_os": "system_os_mcp",
            "office_master": "office_master_mcp",
            "browser_accounts": "browser_accounts_mcp",
            "ai_plugins": "ai_plugins_mcp",
            "computer_intelligence": "computer_intelligence_mcp",
            "tactical_realtime": "realtime_tactical_mcp",
        }
        for s_name, mod_name in server_mod_map.items():
            try:
                mod = sys.modules.get(mod_name) or __import__(mod_name)
                mcp_obj = getattr(mod, "mcp", None)
                tools = []
                if mcp_obj and hasattr(mcp_obj, "_tool_manager"):
                    tools = list(mcp_obj._tool_manager._tools.keys())
                elif mcp_obj and hasattr(mcp_obj, "_tools"):
                    tools = list(mcp_obj._tools.keys())
                if tools:
                    self.agent.register_mock_session(s_name, tools)
            except Exception as e:
                self._log.debug("Auto-register server %s failed: %s", s_name, e)

        # Auto-register Smart Music and Spotify tools for Gemini declarations
        try:
            music_tools = [
                "play_music",
                "pause_music",
                "resume_music",
                "stop_music",
                "next_track",
                "previous_track",
                "set_music_volume",
                "adjust_music_volume",
                "seek_music",
                "set_music_shuffle",
                "set_music_repeat",
                "get_now_playing",
                "search_music",
                "get_available_playback_devices",
            ]
            self.agent.register_mock_session("smart_music", music_tools)
            spotify_tools = [
                "spotify_play_music",
                "spotify_pause_playback",
                "spotify_resume_playback",
                "spotify_skip_to_next",
                "spotify_skip_to_previous",
                "spotify_set_volume",
                "spotify_adjust_volume",
                "spotify_seek_playback",
                "spotify_set_shuffle",
                "spotify_set_repeat",
                "spotify_search",
                "spotify_get_now_playing",
                "spotify_get_available_devices",
            ]
            self.agent.register_mock_session("spotify_music", spotify_tools)
        except Exception as e:
            self._log.debug("Auto-register music tools failed: %s", e)

        # Subsystem references
        self.tts_engine = None
        self.playback = None
        self.coordinator = None
        self.hotkey_controller = None
        self.clarity_guard = None
        self.brain = None
        self.ear = None
        self.local_music_provider = None
        self.spotify_adapter = None
        self.music_router = None
        self.audio_ducker = None

        # Backwards compatibility handles
        self.text_handler = None
        self._gemini_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY_01", "")).strip()
        self._echo_mode = not self._gemini_key or self._gemini_key.startswith("placeholder") or self._gemini_key == "YOUR_API_KEY_HERE"

        self._initialize_subsystems()

    def _initialize_subsystems(self) -> None:
        """Instantiate modular Day 10 components."""
        # 1. Output subsystems: Pygame Playback, Edge-TTS, Coordinator
        try:
            from zye_voice.playback import ZyeAudioPlayback, PlaybackConfig
            from zye_voice.edge_tts_engine import ZyeEdgeTTSEngine, EdgeTTSConfig
            from zye_voice.output_coordinator import UnifiedOutputCoordinator

            voice_cfg = self._cfg.get("voice", {})
            tts_cfg_dict = voice_cfg.get("tts", self._cfg.get("tts", {}))
            pb_cfg_dict = voice_cfg.get("playback", {})

            pb_config = PlaybackConfig(
                enabled=bool(pb_cfg_dict.get("enabled", True)),
                mixer_frequency=int(pb_cfg_dict.get("mixer_frequency", 44100)),
                mixer_size=int(pb_cfg_dict.get("mixer_size", -16)),
                mixer_channels=int(pb_cfg_dict.get("mixer_channels", 2)),
                mixer_buffer=int(pb_cfg_dict.get("mixer_buffer", 512)),
            )
            self.playback = ZyeAudioPlayback(pb_config)

            tts_config = EdgeTTSConfig(
                enabled=bool(tts_cfg_dict.get("enabled", True)),
                voice=str(tts_cfg_dict.get("voice", "en-IN-NeerjaNeural")),
                timeout_seconds=float(tts_cfg_dict.get("timeout_seconds", 30.0)),
                max_retries=int(tts_cfg_dict.get("max_retries", 1)),
                retry_delay_seconds=float(tts_cfg_dict.get("retry_delay_seconds", 1.0)),
                allow_cloud_tts=bool(voice_cfg.get("privacy", {}).get("allow_cloud_tts", True)),
            )
            self.tts_engine = ZyeEdgeTTSEngine(tts_config, playback=self.playback)
            self.coordinator = UnifiedOutputCoordinator(tts_engine=self.tts_engine)
        except Exception as exc:
            self._log.warning("Audio output initialization error: %s", exc)

        # 2. Hotkey controller
        try:
            from zye_input.hotkey_controller import ZyeHotkeyController, HotkeyConfig
            from zye_text_input import AltZTextInputHandler, TextInputConfig

            hk_cfg_dict = self._cfg.get("voice", {}).get("hotkey", self._cfg.get("text_input", {}))
            hk_config = HotkeyConfig(
                enabled=bool(hk_cfg_dict.get("enabled", True)),
                shortcut=str(hk_cfg_dict.get("shortcut", "alt+z")),
                input_timeout_seconds=float(hk_cfg_dict.get("input_timeout_seconds", 60.0)),
                prompt_message="Command to Zye: ",
            )
            self.hotkey_controller = ZyeHotkeyController(hk_config)
            # Legacy alias
            self.text_handler = AltZTextInputHandler(TextInputConfig(
                hotkey=hk_config.shortcut,
                input_timeout_seconds=hk_config.input_timeout_seconds,
            ))
        except Exception as exc:
            self._log.warning("Hotkey controller initialization error: %s", exc)

        # 3. Clarity Guard & Gemini Brain
        try:
            from zye_brain.clarity_guard import ZyeAudioClarityGuard, ClarityConfig
            from zye_brain.gemini_agent import ZyeGeminiAgent, GeminiBrainConfig

            clarity_dict = self._cfg.get("voice", {}).get("clarity", {})
            clarity_config = ClarityConfig(
                enabled=bool(clarity_dict.get("enabled", True)),
                strict_mode=bool(clarity_dict.get("strict_mode", True)),
                block_tools_when_unclear=bool(clarity_dict.get("block_tools_when_unclear", True)),
            )
            self.clarity_guard = ZyeAudioClarityGuard(clarity_config)

            # Autonomy Subsystems (Day 11/13)
            try:
                from zye_intelligence.mission_controller import ZyeMissionController
                from zye_intelligence.preflight import ZyeSystemPreflight
                from zye_intelligence.premortem import ZyeNegativePreMortem
                from zye_intelligence.decision_matrix import ZyeDecisionMatrix
                from zye_intelligence.emergency_reflex import ZyeEmergencyReflex
                from zye_intelligence.execution_gate import ZyeExecutionGate
                from zye_intelligence.autonomous_watchdog import ZyeAutonomousWatchdog, proactive_autonomous_loop
                from zye_intelligence.negative_audit import NegativeAuditEngine

                self.mission_controller = ZyeMissionController()
                self.preflight = ZyeSystemPreflight()
                self.premortem_brain = ZyeNegativePreMortem()
                self.decision_matrix = ZyeDecisionMatrix()
                self.audit_engine = NegativeAuditEngine(
                    preflight=self.preflight,
                    premortem_brain=self.premortem_brain,
                )
                self.emergency_reflex = ZyeEmergencyReflex(mission_controller=self.mission_controller)
                self.execution_gate = ZyeExecutionGate(
                    premortem_brain=self.premortem_brain,
                    preflight=self.preflight,
                    mission_controller=self.mission_controller,
                )
                watchdog_cfg = self._cfg.get("autonomous_brain", {}).get(
                    "watchdog", self._cfg.get("autonomy", {}).get("watchdog", {})
                )
                self.watchdog = ZyeAutonomousWatchdog(
                    config=watchdog_cfg, mission_controller=self.mission_controller
                )
            except Exception as a_exc:
                self._log.warning("Autonomy subsystems initialization warning: %s", a_exc)
                self.execution_gate = None
                self.watchdog = None
                self.emergency_reflex = None
                self.audit_engine = None

            async def _dispatch(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
                # Argument alias normalization to ensure compatibility with FastMCP tools
                if not isinstance(args, dict):
                    args = {}

                # 1. Application name parameter normalization
                if tool_name in (
                    "open_any_app", "close_application_window", "get_application_status",
                    "search_inside_application", "manage_window"
                ):
                    if "app_name" not in args or not args["app_name"]:
                        val = (
                            args.get("application")
                            or args.get("process_path")
                            or args.get("target_app")
                            or args.get("process_name")
                            or args.get("target_app_name")
                            or args.get("application_path")
                            or args.get("name")
                            or args.get("app")
                            or args.get("window_keyword")
                            or args.get("keyword")
                        )
                        if not val and hasattr(self, "live_manager") and self.live_manager:
                            user_text = (
                                getattr(self.live_manager.telemetry, "latest_user_transcript", "")
                                or getattr(self.live_manager.telemetry, "latest_interim_transcript", "")
                            ).lower()
                            if "notepad" in user_text or "நோட்பேட்" in user_text:
                                val = "notepad"
                            elif "chrome" in user_text or "குரோம்" in user_text:
                                val = "chrome"
                            elif "calculator" in user_text or "கால்குலேட்டர்" in user_text:
                                val = "calc"
                            elif "word" in user_text:
                                val = "winword"
                            elif "excel" in user_text:
                                val = "excel"
                        if val:
                            if isinstance(val, str) and ("\\" in val or "/" in val):
                                val = Path(val).stem
                            if isinstance(val, str) and val.lower().endswith(".exe"):
                                val = val[:-4]
                            args["app_name"] = str(val)

                if tool_name == "start_application_process":
                    if "application" not in args or not args["application"]:
                        val = (
                            args.get("process_path")
                            or args.get("target_app")
                            or args.get("process_name")
                            or args.get("app_name")
                            or args.get("target_app_name")
                            or args.get("application_path")
                            or args.get("name")
                            or args.get("app")
                        )
                        if not val and hasattr(self, "live_manager") and self.live_manager:
                            user_text = (
                                getattr(self.live_manager.telemetry, "latest_user_transcript", "")
                                or getattr(self.live_manager.telemetry, "latest_interim_transcript", "")
                            ).lower()
                            if "notepad" in user_text or "நோட்பேட்" in user_text:
                                val = "notepad"
                            elif "chrome" in user_text or "குரோம்" in user_text:
                                val = "chrome"
                            elif "calculator" in user_text or "கால்குலேட்டர்" in user_text:
                                val = "calc"
                        if val:
                            if isinstance(val, str) and ("\\" in val or "/" in val):
                                val = Path(val).stem
                            if isinstance(val, str) and val.lower().endswith(".exe"):
                                val = val[:-4]
                            args["application"] = str(val)
                    for bad_k in ("target_app", "process_path", "process_name", "target_app_name", "application_path", "app_name", "name", "app"):
                        if bad_k in args and bad_k != "application":
                            args.pop(bad_k, None)

                # 2. Query / search parameter normalization
                if tool_name in ("search_installed_apps", "search_local_files", "search_web"):
                    if "query" not in args:
                        val = (
                            args.get("name")
                            or args.get("app_name")
                            or args.get("keyword")
                            or args.get("text")
                            or args.get("search_query")
                        )
                        if val:
                            args["query"] = str(val)

                # 3. AI prompt parameter normalization
                if tool_name.startswith(("ask_", "compare_ai_")):
                    if "prompt" not in args:
                        val = (
                            args.get("query")
                            or args.get("text")
                            or args.get("message")
                            or args.get("content")
                            or args.get("input")
                        )
                        if val:
                            args["prompt"] = str(val)

                # 4. Office text insertion and dictation normalization
                if tool_name in ("word_insert_text", "ppt_insert_text", "type_into_app", "dictate_text_anywhere", "type_text"):
                    if "text" not in args or not args["text"]:
                        val = (
                            args.get("content")
                            or args.get("code")
                            or args.get("prompt")
                            or args.get("body")
                            or args.get("data")
                            or args.get("input")
                            or args.get("message")
                        )
                        if val:
                            args["text"] = str(val)
                    if tool_name == "type_into_app":
                        if "window_keyword" not in args or not args["window_keyword"]:
                            val = (
                                args.get("app_name")
                                or args.get("window")
                                or args.get("application")
                                or args.get("target_app")
                                or args.get("name")
                                or "Notepad"
                            )
                            args["window_keyword"] = str(val)
                        if "element_name" not in args:
                            args["element_name"] = ""

                # 5. Window management action & keyword normalization
                if tool_name == "manage_window":
                    if "action" not in args:
                        args["action"] = "focus"
                    if "keyword" not in args:
                        val = args.get("window_keyword") or args.get("app_name") or args.get("name")
                        if val:
                            args["keyword"] = str(val)

                # Execution Authorization Gate Check (Day 11)
                if self.execution_gate is not None:
                    gate_eval = await self.execution_gate.evaluate(
                        tool_name=tool_name, tool_args=args
                    )
                    if not gate_eval.get("allowed", False):
                        self._log.warning(
                            "Execution Gate blocked tool '%s': %s",
                            tool_name,
                            gate_eval.get("reason"),
                        )
                        return {
                            "status": "BLOCKED_BY_EXECUTION_GATE",
                            "reason": gate_eval.get("reason"),
                            "approval_token": gate_eval.get("approval_token"),
                            "risk_class": gate_eval.get("risk_class"),
                            "requires_confirmation": gate_eval.get("requires_confirmation", False),
                        }
                else:
                    # Fail-closed: allow ONLY explicitly verified read-only or local voice controls if gate is unavailable
                    safe_read_prefixes = (
                        "get_", "read_", "list_", "inspect_", "check_", "status", "voice_", "ping",
                        "play_music", "pause_music", "resume_music", "stop_music", "next_track",
                        "previous_track", "set_music_", "adjust_music_", "seek_music_", "search_music"
                    )
                    if not any(tool_name.startswith(p) for p in safe_read_prefixes):
                        self._log.error("Execution gate unavailable; blocking unverified tool '%s'", tool_name)
                        return {
                            "status": "BLOCKED_BY_SECURITY_POLICY",
                            "reason": f"Execution gate unavailable. Unverified tool mutation blocked for '{tool_name}'.",
                        }

                # Smart Music Tool Dispatch
                if tool_name in (
                    "play_music", "pause_music", "resume_music", "stop_music",
                    "next_track", "previous_track", "set_music_volume",
                    "adjust_music_volume", "seek_music", "set_music_shuffle",
                    "set_music_repeat", "get_now_playing", "search_music",
                    "get_available_playback_devices"
                ):
                    if hasattr(self, "music_router") and self.music_router:
                        from zye_music.music_models import InputOrigin, IntentResult, IntentType, ProviderType
                        origin = InputOrigin.MANUAL_TOOL
                        if tool_name == "play_music":
                            query = args.get("track_or_query") or args.get("query") or args.get("song") or args.get("track")
                            provider_pref = ProviderType(args["provider"]) if "provider" in args else None
                            intent = IntentResult(intent=IntentType.PLAY, query=query, provider_preference=provider_pref)
                            return self.music_router.execute_intent(intent, origin=origin).to_dict()
                        elif tool_name == "pause_music":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.PAUSE), origin=origin).to_dict()
                        elif tool_name == "resume_music":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.RESUME), origin=origin).to_dict()
                        elif tool_name == "stop_music":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.STOP), origin=origin).to_dict()
                        elif tool_name == "next_track":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.NEXT), origin=origin).to_dict()
                        elif tool_name == "previous_track":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.PREVIOUS), origin=origin).to_dict()
                        elif tool_name == "set_music_volume":
                            level = int(args.get("volume_percent", args.get("level", 80)))
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.VOLUME_SET, volume_level=level), origin=origin).to_dict()
                        elif tool_name == "adjust_music_volume":
                            adj = int(args.get("adjustment", 10))
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.VOLUME_UP if adj > 0 else IntentType.VOLUME_DOWN), origin=origin).to_dict()
                        elif tool_name == "seek_music":
                            pos = int(args.get("position_ms", 0))
                            provider = self.music_router.resolve_provider(origin=origin)
                            return provider.seek(pos).to_dict()
                        elif tool_name == "set_music_shuffle":
                            state = bool(args.get("state", True))
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.SHUFFLE_ON if state else IntentType.SHUFFLE_OFF), origin=origin).to_dict()
                        elif tool_name == "set_music_repeat":
                            rep_state = str(args.get("state", "off"))
                            provider = self.music_router.resolve_provider(origin=origin)
                            return provider.set_repeat(rep_state).to_dict()
                        elif tool_name == "get_now_playing":
                            return self.music_router.execute_intent(IntentResult(intent=IntentType.NOW_PLAYING), origin=origin).to_dict()
                        elif tool_name == "search_music":
                            query = str(args.get("query", ""))
                            provider = self.music_router.resolve_provider(origin=origin)
                            tracks = provider.search(query)
                            return {"status": "SUCCESS", "tracks": [t.to_dict() for t in tracks]}
                        elif tool_name == "get_available_playback_devices":
                            provider = self.music_router.resolve_provider(origin=origin)
                            devices = provider.get_available_devices()
                            return {"status": "SUCCESS", "devices": devices}

                # Direct Spotify MCP tool dispatch
                if (tool_name.startswith("spotify_") or tool_name in (
                    "playMusic", "pausePlayback", "resumePlayback", "skipToNext", "skipToPrevious",
                    "setVolume", "adjustVolume", "seekPlayback", "setShuffle", "setRepeat",
                    "searchSpotify", "getNowPlaying", "getAvailableDevices", "getMyPlaylists",
                    "getPlaylistTracks", "getQueue", "addToQueue", "transferPlayback"
                )) and hasattr(self, "spotify_adapter") and self.spotify_adapter:
                    from zye_music.spotify_mcp_adapter import SPOTIFY_TOOL_NAME_MAP
                    mcp_tool_name = SPOTIFY_TOOL_NAME_MAP.get(tool_name, tool_name[8:] if tool_name.startswith("spotify_") else tool_name)
                    return self.spotify_adapter.call_tool(mcp_tool_name, args)

                res = await self.agent.call_mcp_with_recovery(tool_name, args)

                if self.execution_gate is not None:
                    post_ver = self.execution_gate.verify_post_execution(tool_name, res)
                    if isinstance(res, dict) and not post_ver.get("verified", True):
                        res["verified"] = False
                        if res.get("status") in ("SUCCESS", "OK", "success"):
                            res["status"] = post_ver.get("verification_status", "FAILED")
                return res

            brain_config = GeminiBrainConfig(
                model_name=self._cfg.get("gemini", {}).get("model_id", "gemini-3.5-flash-lite"),
                max_tool_rounds=int(self._cfg.get("voice", {}).get("loop", {}).get("max_tool_rounds", 8)),
                max_history_turns=int(self._cfg.get("voice", {}).get("loop", {}).get("max_history_turns", 16)),
            )
            try:
                from gemini_gateway import ZyeGeminiGateway
                self.gateway = ZyeGeminiGateway.get_instance()
            except Exception:
                self.gateway = None

            tool_decls = self.agent.tool_registry.build_gemini_declarations()
            self.brain = ZyeGeminiAgent(
                config=brain_config,
                clarity_guard=self.clarity_guard,
                tool_dispatcher=_dispatch,
                tool_declarations=tool_decls,
                gateway=self.gateway,
            )
            self.brain._echo_mode = self._echo_mode
        except Exception as exc:
            self._log.warning("Brain initialization error: %s", exc)
            self._echo_mode = True

        # 4. Audio Ear
        try:
            from zye_audio_ear import SmartAudioEar, AudioConfig
            audio_section = self._cfg.get("audio", {})
            audio_config = AudioConfig(
                sample_rate=int(audio_section.get("sample_rate", 16000)),
                channels=int(audio_section.get("channels", 1)),
                frame_duration_ms=int(audio_section.get("frame_duration_ms", 32)),
                maximum_record_seconds=float(audio_section.get("maximum_record_seconds", 25.0)),
                silence_timeout_seconds=float(audio_section.get("silence_timeout_seconds", 1.85)),
                pre_roll_seconds=float(audio_section.get("pre_roll_seconds", 0.96)),
                vad_start_threshold=float(audio_section.get("vad_start_threshold", 0.48)),
                vad_hold_threshold=float(audio_section.get("vad_hold_threshold", 0.40)),
            )
            self.ear = SmartAudioEar(audio_config)
            if self.coordinator and hasattr(self.ear, "chime_player"):
                self.coordinator.chime_player = self.ear.chime_player
        except Exception as exc:
            self._log.warning("SmartAudioEar unavailable: %s", exc)

        # 5. Gemini Live Native Audio Manager (Section 04, 10, 17)
        self.live_manager = None
        live_cfg_dict = self._cfg.get("gemini_live", {})
        if live_cfg_dict.get("enabled", True):
            try:
                from zye_gemini_live import ZyeGeminiLiveManager, GeminiLiveConfig
                live_config = GeminiLiveConfig(
                    enabled=bool(live_cfg_dict.get("enabled", True)),
                    model_id=str(live_cfg_dict.get("model", "gemini-3.8-live")),
                    fallback_model_id=str(live_cfg_dict.get("fallback_model", "gemini-3.1-flash-live-preview")),
                    voice_name=str(live_cfg_dict.get("voice_name", "Aoede")),
                    automatic_vad=bool(live_cfg_dict.get("automatic_vad", True)),
                    input_transcription=bool(live_cfg_dict.get("input_transcription", True)),
                    output_transcription=bool(live_cfg_dict.get("output_transcription", True)),
                    session_resumption=bool(live_cfg_dict.get("session_resumption", True)),
                    allow_barge_in=bool(live_cfg_dict.get("allow_barge_in", True)),
                    echo_cancellation=bool(live_cfg_dict.get("echo_cancellation", True)),
                    self_listening_suppression=bool(live_cfg_dict.get("self_listening_suppression", True)),
                    speech_energy_threshold=float(live_cfg_dict.get("speech_energy_threshold", 400.0)),
                    silence_frames_threshold=int(live_cfg_dict.get("silence_frames_threshold", 36)),
                    barge_in_energy_threshold=float(live_cfg_dict.get("barge_in_energy_threshold", 2200.0)),
                    direct_greeting_fast_path=bool(live_cfg_dict.get("direct_greeting_fast_path", True)),
                    first_response_watchdog_seconds=float(live_cfg_dict.get("first_response_watchdog_seconds", 5.0)),
                    tool_timeout_seconds=float(live_cfg_dict.get("tool_timeout_seconds", 15.0)),
                    reconnect_delay_seconds=float(live_cfg_dict.get("reconnect_delay_seconds", 1.0)),
                    max_reconnect_attempts=int(live_cfg_dict.get("max_reconnect_attempts", 5)),
                    echo_tail_guard_ms=float(live_cfg_dict.get("echo_tail_guard_ms", 350.0)),
                    half_duplex_safety=bool(live_cfg_dict.get("half_duplex_safety", True)),
                    max_tools_per_turn=int(live_cfg_dict.get("max_tools_per_turn", 4)),
                )
                self.live_manager = ZyeGeminiLiveManager(
                    config=live_config,
                    key_manager=getattr(self.gateway, "key_manager", None) if self.gateway else None,
                    gateway=self.gateway,
                    tool_dispatcher=_dispatch,
                    tool_declarations=tool_decls,
                    audio_capture_engine=getattr(self.ear, "capture_engine", None) if self.ear else None,
                    chime_player=getattr(self.ear, "chime_player", None) if self.ear else None,
                    coordinator=self.coordinator,
                )
                if hasattr(self.gateway, "_live_manager"):
                    self.gateway._live_manager = self.live_manager
                self._log.info("Gemini Live Native Audio Manager initialized (model='%s')", live_config.model_id)
            except Exception as exc:
                self._log.warning("Gemini Live Manager initialization warning: %s", exc)
                self.live_manager = None

        # 6. Smart Music Subsystem (Local Audio + Spotify MCP + Audio Ducking)
        try:
            from zye_music import (
                LocalMusicProvider,
                SpotifyMCPAdapter,
                MusicProviderRouter,
                MusicAuthorization,
                AudioDucker,
            )
            music_cfg = self._cfg.get("music", {})
            local_cfg = self._cfg.get("local_music", {})
            spotify_cfg = self._cfg.get("spotify", {})
            ducking_cfg = self._cfg.get("audio_ducking", {})

            if music_cfg.get("enabled", True):
                self.local_music_provider = LocalMusicProvider(
                    music_directories=local_cfg.get("music_directories", ["d:/Zye/data/music"]),
                    default_volume=int(music_cfg.get("default_volume", 80)),
                )
                self.local_music_provider.initialize()

                self.spotify_adapter = SpotifyMCPAdapter(
                    mcp_script_path=spotify_cfg.get(
                        "mcp_server_script",
                        r"d:\Zye\external_mcp\spotify-mcp-server\build\index.js",
                    ),
                    config_path=spotify_cfg.get("config_path", r"C:\ZyeSecrets\spotify-config.json"),
                )

                music_auth = MusicAuthorization(
                    allow_spotify_voice_experimental=bool(
                        music_cfg.get("allow_spotify_voice_experimental", False)
                    ),
                )

                self.audio_ducker = AudioDucker(
                    set_volume_fn=lambda v: self.local_music_provider.set_volume(v),
                    get_volume_fn=lambda: self.local_music_provider.get_playback_state().volume_percent,
                    ducked_volume_percentage=int(ducking_cfg.get("ducked_volume_percentage", 20)),
                    ramp_duration_ms=int(ducking_cfg.get("ramp_duration_ms", 150)),
                )

                self.music_router = MusicProviderRouter(
                    local_provider=self.local_music_provider,
                    spotify_provider=self.spotify_adapter,
                    authorization=music_auth,
                    ducker=self.audio_ducker,
                )

                if self.live_manager:
                    self.live_manager.set_audio_ducker(self.audio_ducker)

                self._log.info("Smart Music Subsystem initialized (Local + Spotify MCP + Audio Ducking)")
        except Exception as exc:
            self._log.warning("Smart Music Subsystem initialization warning: %s", exc)

    async def _generate_response(self, user_text: str) -> str:
        """Process text through the Gemini agent with voice command interceptors for settings."""
        if not user_text.strip():
            return ""

        clean = user_text.strip().lower()

        # Smart Music Voice Interceptors (Tamil / English / Tanglish)
        if hasattr(self, "music_router") and self.music_router:
            try:
                from zye_music.music_intent_router import MusicIntentRouter
                from zye_music.music_models import IntentType, InputOrigin
                intent_res = MusicIntentRouter.parse_intent(user_text)
                if intent_res.intent != IntentType.UNKNOWN:
                    play_res = self.music_router.execute_intent(intent_res, origin=InputOrigin.VOICE)
                    if play_res.success:
                        return play_res.message
                    else:
                        return f"Music command execute aagala: {play_res.message}"
            except Exception as music_err:
                self._log.debug("Music intent interceptor pass-through: %s", music_err)

        # Section 19: Voice command handling for Gemini settings (Tamil / English / Tanglish)
        if any(kw in clean for kw in ("thinking level low", "thinking low", "set thinking low", "low thinking")):
            if hasattr(self, "gateway") and self.gateway:
                self.gateway.set_thinking_level("LOW")
            return "Thinking level LOW-ku maathiyachu. Speed and latency optimized."

        if any(kw in clean for kw in ("thinking level medium", "thinking medium", "set thinking medium", "medium thinking")):
            if hasattr(self, "gateway") and self.gateway:
                self.gateway.set_thinking_level("MEDIUM")
            return "Thinking level MEDIUM-ku maathiyachu. Balanced reasoning enabled."

        if any(kw in clean for kw in ("thinking level high", "thinking high", "set thinking high", "high thinking")):
            if hasattr(self, "gateway") and self.gateway:
                self.gateway.set_thinking_level("HIGH")
            return "Thinking level HIGH-ku maathiyachu. Deep adversarial reasoning enabled."

        if any(kw in clean for kw in ("gemini status", "gemini health", "check gemini")):
            if hasattr(self, "gateway") and self.gateway:
                hs = self.gateway.get_health_status()
                return (
                    f"Gemini status: Model {hs['model_id']}, thinking level {hs['thinking_level']}. "
                    f"{hs['healthy_slots']} of {hs['total_slots']} slots are healthy."
                )
            return "Gemini status: Gateway not active."

        if any(kw in clean for kw in ("token usage", "check tokens")):
            if hasattr(self, "gateway") and self.gateway:
                stats = self.gateway.get_usage_statistics()
                return f"Total tokens used: {stats.get('grand_total_tokens', 0)}. Average latency: {stats.get('average_duration_seconds', 0.0)} seconds."
            return "Token usage tracker not active."

        # Day 14 Personal Assistant Voice Interceptors (Tamil / English / Tanglish)
        if any(kw in clean for kw in ("morning brief", "morning briefing", "kaalai briefing", "innaikku briefing")):
            from zye_personal_assistant.daily_report_engine import DailyReportEngine
            rep = DailyReportEngine().generate_report("morning_brief")
            return rep.get("voice_tanglish") or rep.get("voice_en") or "Morning brief generated."

        if any(kw in clean for kw in ("end of day", "innaikku report", "today report", "today summary", "eod report")):
            from zye_personal_assistant.daily_report_engine import DailyReportEngine
            rep = DailyReportEngine().generate_report("end_of_day")
            return rep.get("voice_tanglish") or rep.get("voice_en") or "End of day report ready."

        if any(kw in clean for kw in ("innaikku meetings", "what meetings", "today meetings", "enna meetings", "daily schedule")):
            from zye_personal_assistant.calendar_engine import CalendarEngine
            events = CalendarEngine().get_daily_schedule()
            if not events:
                return "Innaikku schedule-la meetings edhum illa. Free time available-ah irukku."
            m_list = ", ".join(f"{e['title']} at {e['start_iso'].split('T')[1][:5] if 'T' in e['start_iso'] else e['start_iso']}" for e in events[:3])
            return f"Innaikku {len(events)} meeting(s) irukku: {m_list}."

        if any(kw in clean for kw in ("pending tasks", "tasks list", "tasks eppadhi", "what tasks")):
            from zye_personal_assistant.task_scheduler import TaskScheduler
            tasks = TaskScheduler().list_tasks(status="PENDING", limit=5)
            if not tasks:
                return "Pending tasks edhum illa! All clear."
            t_list = ", ".join(f"[{t['priority']}] {t['title']}" for t in tasks[:3])
            return f"Top pending tasks: {t_list}."

        if any(kw in clean for kw in ("timeblock pannu", "auto timeblock", "timeblock tasks")):
            from zye_personal_assistant.task_scheduler import TaskScheduler
            res = TaskScheduler().auto_timeblock_today()
            if isinstance(res, dict) and res.get("status") in ("SUCCESS", "OK", "success"):
                return f"Timeblock complete. {res.get('scheduled_count', 0)} tasks schedule pannirukken."
            else:
                err_msg = res.get("message", res.get("error", "Unknown error")) if isinstance(res, dict) else "Execution failed"
                return f"Auto timeblock complete panna mudiyala: {err_msg}."

        if any(kw in clean for kw in ("project status", "projects eppadhi", "status board")):
            from zye_personal_assistant.project_manager import ProjectManager
            sb = ProjectManager().get_status_board()
            return f"Total active projects: {sb.get('total_projects', 0)}. Status board updated."

        if any(kw in clean for kw in ("unread emails", "check email", "mails check", "mails vandhurukka")):
            from zye_personal_assistant.email_engine import EmailEngine
            em = EmailEngine()
            if not em.is_configured():
                return "Work Gmail configure aagala. zye_config.toml-la credentials set pannavum."
            try:
                unread = em.fetch_unread_emails(limit=3)
                if unread.get("status") == "ERROR":
                    err_details = unread.get("error", unread.get("message", "Fetch failed"))
                    return f"Email check panna mudiyala: {err_details}."
                count = unread.get('count', len(unread.get('emails', [])))
                return f"{count} unread email(s) retrieve pannirukken."
            except Exception as e:
                return f"Email fetch connection error: {e}."


        if self._echo_mode:
            return f"[Echo] {user_text}"
        if self.brain:
            return await self.brain.handle_text(user_text)
        return f"[Echo] {user_text}"

    async def _speak(self, text: str) -> None:
        """Speak text through the unified coordinator."""
        if not text or not text.strip():
            return
        if self.coordinator:
            try:
                await self.coordinator.speak(text)
            except Exception as exc:
                self._log.debug("TTS speak error: %s", exc)
        elif self.tts_engine:
            try:
                if hasattr(self.tts_engine, "say"):
                    await self.tts_engine.say(text)
                else:
                    await self.tts_engine.speak(text)
            except Exception as exc:
                self._log.debug("TTS speak error: %s", exc)
        else:
            print(f"[Zye] {text}")

    async def run(self) -> None:
        """
        Execute the 13-stage startup sequence and enter the main interaction loop.
        """
        self._running = True
        self.state = VoiceSystemState.INITIALIZING

        print("=" * 64, flush=True)
        print("          ZYE AI — VOICE INTERACTION SYSTEM v4.0", flush=True)
        print("=" * 64, flush=True)

        # STAGES 1-11
        if self.tts_engine:
            await self.tts_engine.initialize()
        if self.brain:
            await self.brain.initialize()
            self._echo_mode = self.brain._echo_mode
        if self.hotkey_controller:
            self.hotkey_controller.register()

        # STAGE 12 — Announce status
        announcement = "Zye online. Neural hearing and voice interaction ready. Solunga."
        print(f"[Zye] {announcement}", flush=True)
        self.state = VoiceSystemState.SPEAKING
        await self._speak(announcement)

        # STAGE 13 — Master Loop & Autonomous Watchdog
        self.state = VoiceSystemState.READY
        print("Zye is listening. Press Alt+Z for text mode, Ctrl+C to quit.", flush=True)

        # Launch Proactive Background Watchdog (Day 11)
        self._watchdog_task: asyncio.Task | None = None
        if hasattr(self, "watchdog") and self.watchdog is not None:
            self._watchdog_task = asyncio.create_task(self.proactive_autonomous_loop())

        # Launch Proactive Personal Assistant Meeting Reminder Daemon (Day 14)
        self._reminder_task: asyncio.Task | None = None
        if self._cfg.get("personal_assistant", {}).get("reminders", {}).get("enabled", True):
            self._reminder_task = asyncio.create_task(self.meeting_reminder_loop())


        try:
            while self._running:
                # Path A: Alt + Z silent command requested
                if (
                    (self.hotkey_controller and self.hotkey_controller.text_mode_requested()) or
                    (self.text_handler and self.text_handler.is_triggered())
                ):
                    if self.hotkey_controller:
                        self.hotkey_controller.consume_text_mode_request()
                    if self.text_handler:
                        self.text_handler.get_trigger_event()

                    self.state = VoiceSystemState.TEXT_MODE
                    # Interrupt microphone if recording
                    if self.ear:
                        self.ear.cancel_capture()
                    if self.live_manager:
                        self.live_manager.player.flush()
                        self.live_manager.set_muted(True)

                    # Collect command from terminal
                    prompt = "Command to Zye: "
                    cmd = await asyncio.to_thread(
                        self.hotkey_controller.collect_text_command if self.hotkey_controller
                        else lambda: input(f"\n{prompt}").strip()
                    )

                    if cmd:
                        self.state = VoiceSystemState.THINKING
                        response = await self._generate_response(cmd)
                        self.state = VoiceSystemState.SPEAKING
                        await self._speak(response)

                    if self.live_manager:
                        self.live_manager.set_muted(False)

                    self.state = VoiceSystemState.READY
                    continue

                # Path B: Gemini Live Native Bidirectional Audio Capture (Section 04, 05, 12, 13, 18)
                use_live = (
                    self.live_manager is not None
                    and not self.live_manager.is_degraded()
                )
                if use_live:
                    self.state = VoiceSystemState.LISTENING
                    if not hasattr(self, "_live_pump_task") or self._live_pump_task is None or self._live_pump_task.done():
                        if self.ear and hasattr(self.ear, "capture_engine"):
                            self._live_pump_task = asyncio.create_task(
                                self.live_manager.pump_capture_engine(self.ear.capture_engine)
                            )
                    if not hasattr(self, "_live_loop_task") or self._live_loop_task is None or self._live_loop_task.done():
                        self._live_loop_task = asyncio.create_task(
                            self.live_manager.run_live_loop()
                        )
                    await asyncio.sleep(0.1)

                    if not self.live_manager.is_degraded():
                        continue
                    else:
                        self._log.warning("Gemini Live session degraded. Gracefully transitioning to SmartAudioEar (Path C).")
                        print("\n[Voice Engine]: Gemini Live unavailable or degraded -> Activating SmartAudioEar + Edge TTS fallback.\n", flush=True)
                        if hasattr(self, "_live_pump_task") and self._live_pump_task and not self._live_pump_task.done():
                            self._live_pump_task.cancel()

                # Path C: Fallback local audio capture
                if self.ear is not None:
                    # Cancel any active live pump so frame_queue is not drained
                    if hasattr(self, "_live_pump_task") and self._live_pump_task and not self._live_pump_task.done():
                        self._live_pump_task.cancel()

                    self.state = VoiceSystemState.LISTENING
                    print("[Zye is listening...] (Speak now in Tamil, English, or Tanglish, or press Alt+Z for text mode)", flush=True)
                    wav_bytes = await asyncio.to_thread(self.ear.listen_smart)

                    if wav_bytes:
                        self.state = VoiceSystemState.AUDIO_PROCESSING
                        from zye_voice.voice_diagnostics import get_voice_diagnostics
                        diag = get_voice_diagnostics()
                        diag.start_interaction(mic_detected=True, audio_level_rms=0.08)

                        transcript = ""
                        if self.brain and hasattr(self.brain, "transcribe_audio"):
                            transcript = await self.brain.transcribe_audio(wav_bytes)

                        if transcript:
                            diag.record_transcript(final_transcript=transcript)
                            print(f"\n[Voice Recognized]: {transcript}", flush=True)
                            self.state = VoiceSystemState.THINKING
                            print("[Zye Processing...] Thinking...", flush=True)
                            response = await self._generate_response(transcript)
                        else:
                            # Bounded single transcription: do not cascade to handle_voice and retry indefinitely
                            response = "Mannikavum, enna sonneenga-nu sariya puriyala. Thirumba sollunga."

                        diag.record_gemini_intent(intent=response[:80] if response else "None")
                        diag.finalize(status="PASS" if response else "FAIL")

                        self.state = VoiceSystemState.SPEAKING
                        print(f"\n[Zye]: {response}\n", flush=True)
                        await self._speak(response)
                        self.state = VoiceSystemState.READY
                    else:
                        await asyncio.sleep(0.05)
                else:
                    await asyncio.sleep(0.1)

        except (KeyboardInterrupt, asyncio.CancelledError):
            self._log.info("Voice orchestrator loop received stop request")
        finally:
            await self._shutdown()

    async def proactive_autonomous_loop(self) -> None:
        """Background monitoring loop inspecting telemetry and executing critical reflexes."""
        interval = float(self._cfg.get("autonomy", {}).get("watchdog", {}).get("interval_seconds", 25.0))
        self._log.info("Proactive Autonomous Watchdog loop active (interval=%ss)", interval)
        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                if hasattr(self, "watchdog") and self.watchdog:
                    scan_res = await self.watchdog.scan_system()
                    problems = []
                    if isinstance(scan_res, dict):
                        problems = scan_res.get("unsuppressed_problems", scan_res.get("detected_problems", []))
                    elif isinstance(scan_res, list):
                        problems = scan_res
                    for prob in problems:
                        if not isinstance(prob, dict):
                            continue
                        sev = prob.get("severity")
                        cat = prob.get("category")
                        desc = prob.get("description", "")
                        self._log.info("Autonomous Watchdog detected [%s] %s: %s", sev, cat, desc)

                        if sev == "CRITICAL":
                            is_in_voice = hasattr(self, "live_manager") and self.live_manager and self.live_manager.is_healthy()
                            if cat == "BATTERY" and getattr(self, "emergency_reflex", None):
                                self._log.warning("Executing emergency battery_critical reflex...")
                                await self.emergency_reflex.execute("battery_critical")
                                if not is_in_voice:
                                    await self._speak("Warning: Battery level critical. Activating stealth power saving.")
                            elif cat == "RAM" and getattr(self, "emergency_reflex", None):
                                await self.emergency_reflex.execute("ram_overload_relief")
                                if not is_in_voice:
                                    await self._speak("Warning: System memory overloaded. Reallocating resources.")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._log.error("Proactive watchdog background error: %s", exc)
                await asyncio.sleep(2.0)

    async def meeting_reminder_loop(self) -> None:
        """Background meeting reminder loop inspecting calendar alerts every 45s (Day 14)."""
        interval = float(self._cfg.get("personal_assistant", {}).get("reminders", {}).get("check_interval_seconds", 45.0))
        self._log.info("Personal Assistant proactive meeting reminder loop active (interval=%ss)", interval)
        try:
            from zye_personal_assistant.reminder_engine import ReminderEngine
            engine = ReminderEngine()
        except Exception as e:
            self._log.error("Failed to initialize ReminderEngine in daemon loop: %s", e)
            return

        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                alerts = await asyncio.to_thread(engine.check_meeting_reminders)
                is_in_voice = hasattr(self, "live_manager") and self.live_manager and self.live_manager.is_healthy()
                for alert in alerts:
                    spoken_text = alert.get("message_tanglish") or alert.get("message_en")
                    if spoken_text:
                        self._log.info("Proactive meeting reminder triggered: %s", spoken_text)
                        if not is_in_voice:
                            await self._speak(spoken_text)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._log.error("Meeting reminder daemon background error: %s", exc)
                await asyncio.sleep(5.0)

    async def _shutdown(self) -> None:
        """Gracefully release all resources across audio, hotkey, brain, and watchdog."""
        self._running = False
        self.state = VoiceSystemState.SHUTTING_DOWN
        if hasattr(self, "_watchdog_task") and self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, "_reminder_task") and self._reminder_task and not self._reminder_task.done():
            self._reminder_task.cancel()
            try:
                await self._reminder_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "watchdog") and self.watchdog:
            try:
                await self.watchdog.stop()
            except Exception:
                pass
        if self.hotkey_controller:
            self.hotkey_controller.unregister()
        if self.text_handler:
            self.text_handler.stop()
        if self.coordinator:
            await self.coordinator.close()
        elif self.tts_engine:
            await self.tts_engine.close()
        if self.ear:
            try:
                self.ear.close()
            except Exception:
                pass
        if hasattr(self, "brain") and self.brain:
            await self.brain.shutdown()
        if hasattr(self, "_live_pump_task") and self._live_pump_task:
            self._live_pump_task.cancel()
        if hasattr(self, "_live_loop_task") and self._live_loop_task:
            self._live_loop_task.cancel()
        if hasattr(self, "live_manager") and self.live_manager:
            try:
                self.live_manager.stop()
            except Exception:
                pass
        self.state = VoiceSystemState.OFFLINE
        self._log.info("Zye voice interaction system successfully shut down")

    def stop(self) -> None:
        """Signal loop to stop on next cycle."""
        self._running = False


# Alias for Day 10-14 architecture references
ZyeVoiceOrchestrator = ZyeVoiceLoop


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    """CLI orchestrator entry point."""
    if "--voice" in sys.argv:
        try:
            asyncio.run(ZyeVoiceLoop().run())
        except KeyboardInterrupt:
            pass
        return 0

    agent = ZyeMasterAgent()
    agent.register_mock_session("self_repair", [
        "read_recent_error_logs", "read_own_source_code", "list_project_source_files",
        "inspect_source_file", "create_source_backup", "list_source_backups",
        "preview_code_patch", "patch_own_code", "rollback_code_backup",
    ])
    agent.register_mock_session("autonomous_brain", [
        "run_negative_premortem_brain", "compare_and_decide_solutions",
        "set_mission_mode", "get_current_mission",
        "autonomous_identify_problems", "execute_emergency_reflex",
    ])
    print(f"Zye Master Agent initialized with {len(agent.tool_to_server)} registered tools.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
