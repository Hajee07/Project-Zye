# ZYE AI — Gemini Live MCP Function Calling Loop

## 1. End-to-End Real-Time Loop

Gemini Live connects bidirectional streaming native audio with real-time MCP function calling:

```
[User Natural Speech] (Tamil / English / Tanglish)
       |
       v (16kHz PCM Audio Stream)
[SmartAudioEar & Capture Engine]
       |
       v (WebSocket Stream)
[Google Gemini Live API]
       |
       +---> Greeting / Chit-Chat ---> Native 24kHz Audio Response (613ms)
       |
       +---> Action Command
                 |
                 v
       [tool_call Event: e.g. open_any_app({"app_name": "chrome"})]
                 |
                 v
       [ZYE Master Agent Tool Dispatcher]
                 |
                 v
       [Target MCP Server Execution: windows_control_mcp.open_any_app]
                 |
                 v (Real Windows Action: Chrome Launches)
       [Structured Return Result: {"status": "LAUNCHED", "hwnd": 12345}]
                 |
                 v
       [session.send_tool_response(function_responses=[FunctionResponse])]
                 |
                 v
       [Gemini Live Synthesizes Voice Confirmation: "Chrome open panniten!"]
                 |
                 v (24kHz Native Audio Output)
       [LiveAudioPlayer -> Speakers]
```

---

## 2. Low-Latency Instrumentation

Latency metrics (T0–T13) track the entire function calling timeline:
- **M0**: Tool requested by Gemini Live.
- **M1**: Tool arguments validated by Negative Pre-Mortem Brain.
- **M2**: Orchestrator invokes MCP server.
- **M3**: Execution starts on Windows OS.
- **M4**: Execution completes and return value captured.
- **M5**: Structured `FunctionResponse` transmitted to Gemini Live WebSocket.
All tool executions are isolated to background threads to prevent audio buffer starvation.
