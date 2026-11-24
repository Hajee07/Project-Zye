# ZYE AI — DAY 31 GEMINI LIVE VOICE INTEGRATION SPECIFICATION

## 1. Natural Voice Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Mic as Windows Mic
    participant Live as Gemini Live API
    participant Brain as Gemini Master Brain
    participant Host as ZYE MCP Host
    participant MCP as Computer Intelligence MCP
    participant Duck as DuckDB Engine
    participant Speaker as Windows Audio

    User->>Mic: "Zye, indha periya CSV-la important correlations kandupidi."
    Mic->>Live: Streaming PCM Audio (16kHz)
    Live->>Brain: Speech-to-Intent Recognition
    Brain->>Host: Tool Call: calculate_dataset_correlations(file_path, method="PEARSON")
    Host->>MCP: Dispatch to computer_intelligence_mcp
    MCP->>Duck: Execute In-Memory Pearson Matrix Calculation
    Duck-->>MCP: Verified Coefficients & Ranking (r=0.9995)
    MCP-->>Host: Section 38 JSON + Voice Scripts
    Host-->>Brain: Tool Result Payload
    Brain-->>Live: Synthesize Grounded Explanation
    Live-->>Speaker: Stream Voice Response (24kHz PCM)
    Speaker->>User: "Dataset analysis complete. ad_spend and revenue have a strong positive correlation (r=0.9995)..."
```

---

## 2. Natural Voice Commands Supported

### Tamil & Tanglish:
- *"Zye, indha periya CSV file analyze pannu."*
- *"Indha dataset-la evvalavu rows irukku?"*
- *"Column names and data types sollu."*
- *"Missing values irukka check pannu."*
- *"Duplicate records evvalavu irukku?"*
- *"Sales data-la strongest correlations kandupidi."*
- *"Category-wise sales summary kudu."*
- *"Running analysis stop pannu."*

### English:
- *"Analyze this large CSV dataset."*
- *"What is the schema and row count of this file?"*
- *"Find the strongest correlations between numeric columns."*
- *"Detect any statistical outliers in revenue."*
- *"Calculate group totals by category."*
