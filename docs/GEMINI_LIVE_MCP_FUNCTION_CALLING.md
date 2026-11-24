# GEMINI LIVE MCP FUNCTION CALLING & SAFETY BRIDGE

## 1. Tool Declaration Conversion
All 351 registered MCP tools from `zye_orchestrator` are automatically inspected and converted into `types.FunctionDeclaration` objects using `agent.tool_registry.build_gemini_declarations()`.
Tools are encapsulated in `types.Tool(function_declarations=...)` and supplied to `LiveConnectConfig.tools`.

## 2. Function Call Event Handling
When Gemini Live recognizes that user intent requires tool execution:
1. It pauses audio synthesis and transmits a `tool_call` event containing `function_calls: [types.FunctionCall(name=..., id=..., args=...)]`.
2. `ZyeGeminiLiveManager._handle_live_tool_call()` captures each unique call ID, tool name, and arguments.
3. The request is checked against `_operation_cache` to deduplicate identical calls within a 5-second window.

## 3. Safety Execution Gateway & Pre-Mortem Audit
Before execution:
- Irreversible operations (e.g. deletion, shutdown, external communications) undergo FMEA risk evaluation in `ZyeExecutionGate` / `ZyeNegativePreMortem`.
- Authorized tools execute via `agent.call_mcp_with_recovery(tool_name, tool_args)`.

## 4. Structured Response Transmission
Tool execution results are serialized into structured JSON dictionaries and returned to Gemini Live using `session.send_tool_response`:
```python
await session.send_tool_response(
    function_responses=[
        types.FunctionResponse(
            name=tool_name,
            id=call_id,
            response={"result": tool_result},
        )
    ]
)
```
Gemini Live receives the actual result, formulates a conversational summary, and speaks the confirmation via native 24kHz voice output.
