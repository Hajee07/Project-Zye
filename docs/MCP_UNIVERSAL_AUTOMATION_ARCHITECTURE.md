# ZYE AI — Universal MCP Automation Architecture

## 1. Architectural Overview

ZYE AI integrates a multi-layered automation and reasoning architecture running on the Windows Desktop. At the top level, **Google Gemini 3.5 / Gemini Live** acts as the supreme reasoning authority and natural voice conversation partner. System operations, local application control, browser tasks, and desktop automation are delegated to a decentralized network of **8 Model Context Protocol (MCP) servers** housing **363 tools**.

```
+-----------------------------------------------------------------------------------+
|                        Google Gemini Master Brain / Gemini Live                   |
|                   (Natural Voice, Intent Processing, Reasoning Arbiter)           |
+-----------------------------------------------------------------------------------+
                                         |
                                         | Function Call / Tool Request
                                         v
+-----------------------------------------------------------------------------------+
|                      ZYE Master Agent & Execution Gateway (main.py)               |
|            - Dynamic Tool Dispatcher (_dispatch_tool_call)                        |
|            - Negative Pre-Mortem Brain & Safety Gateway (FMEA Auditing)           |
|            - Session Manager & Hot Reload Controller                              |
+-----------------------------------------------------------------------------------+
                                         |
     +-----------------+-----------------+-----------------+-----------------+
     |                 |                 |                 |                 |
     v                 v                 v                 v                 v
+------------+   +------------+   +------------+   +------------+   +------------+
|  Windows   |   |  Browser   |   | MS Office  |   | System OS  |   |  Personal  |
|  Control   |   |  Accounts  |   |   Master   |   |    MCP     |   | Assistant  |
| (31 Tools) |   | (39 Tools) |   |(183 Tools) |   | (36 Tools) |   | (16 Tools) |
+------------+   +------------+   +------------+   +------------+   +------------+
     |                 |                 |                 |                 |
     v                 v                 v                 v                 v
+------------+   +------------+   +------------+   +------------+   +------------+
|  Autonomous|   | AI Plugins |   |Self-Repair |   |            |   |            |
|   Brain    |   |    Hub     |   |    MCP     |   |            |   |            |
| (6 Tools)  |   | (40 Tools) |   | (12 Tools) |   |            |   |            |
+------------+   +------------+   +------------+   +------------+   +------------+
```

---

## 2. FastMCP Tool Dispatch Engine

Tool dispatching is orchestrated by `_dispatch_tool_call` inside `main.py`:
1. **Target Server Resolution**: Tool names are mapped directly to their owning MCP server via tool-prefix matching and server registration mappings.
2. **FastMCP Invocation Unwrapping**: The dispatcher unwraps FastMCP `Tool` wrapper objects to extract `.fn`, avoiding `TypeError: 'Tool' object is not callable` exceptions.
3. **Execution Context Awareness**: Detects whether an active asyncio event loop is running. For synchronous functions, runs via `asyncio.to_thread` when in an event loop or directly when executed synchronously.
4. **Structured JSON Normalization**: Unpacks stringified JSON responses into native dictionaries, allowing Gemini Live to ingest clean `FunctionResponse` payloads.

---

## 3. Communication Protocols & Interlocks

- **Standard I/O & In-Memory FastMCP**: Standardized IPC with sub-millisecond dispatch latency.
- **Strict Execution Gating**: Destructive or irreversible actions (`send_whatsapp_message`, `start_whatsapp_voice_call`, `delete_file`, `terminate_process`) require explicit confirmation parameters.
- **Acoustic & Hardware Isolation**: Tool execution occurs asynchronously and does not block the real-time audio pipeline of Gemini Live.
