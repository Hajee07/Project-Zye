# ZYE AI — Modular Personal AI Assistant

> **Day 08 Neural Hearing Engine v2.0 — v0.1.0**

Zye AI is a modular, voice-controlled, multimodal personal AI assistant designed for Windows 10/11. It combines cloud AI reasoning (Gemini), local AI inference (Ollama), and an extensible skill architecture built on the Model Context Protocol (MCP).

> [!IMPORTANT]
> **Zye Day 08 delivers the Neural Hearing Engine v2.0 (`zye_audio_ear.py`).** Features include Silero Neural VAD ONNX model inference on CPUExecutionProvider, sub-millisecond per-frame inference (<0.8 ms), strict 512-sample float32 16 kHz mono frame validation, dual-threshold hysteresis (0.52 start / 0.40 hold), consecutive frame confirmation, 0.64-second in-memory pre-roll ring buffer first-word preservation, upgraded 11-state capture lifecycle machine, automatic fail-safe fallback to Day 07 Adaptive RMS detection, recurrent state management, and complete health certification with `doctor.py`.

---

## 🎯 Long-Term Vision

Zye AI is designed to grow into a comprehensive personal AI assistant with:

| # | Capability | Status |
|---|-----------|--------|
| 1 | Gemini-powered reasoning | 🔲 Planned |
| 2 | Ollama local AI inference | 🔲 Planned |
| 3 | Intelligent cloud/local model routing | 🔲 Planned |
| 4 | MCP-based modular tool execution | 🟢 Active (Safety Guard, Self-Repair & Code Repair v1.0) |
| 5 | Windows desktop automation | 🔲 Planned |
| 6 | Microsoft Office automation | 🔲 Planned |
| 7 | Browser & multi-account management | 🔲 Planned |
| 8 | Voice recognition & speech synthesis | 🟢 Active Foundation (Silero Neural VAD ONNX, 0.64s Pre-Roll Ring Buffer & Adaptive RMS Fallback v2.0) |
| 9 | Tamil, English & Tanglish interaction | 🔲 Planned |
| 10 | Long-term semantic memory | 🔲 Planned |
| 11 | Autonomous planning | 🔲 Planned |
| 12 | Controlled self-repair & hot-reload | 🟢 Active (Autonomous Code Repair & Hot-Reload v1.0) |
| 13 | Computer vision & camera tracking | 🔲 Planned |
| 14 | Data analytics & scientific computing | 🔲 Planned |
| 15 | Defensive cybersecurity | 🔲 Planned |
| 16 | CAD & engineering calculations | 🔲 Planned |
| 17 | Smart-home integration | 🔲 Planned |
| 18 | Floating desktop HUD | 🔲 Planned |
| 19 | Multi-agent collaboration | 🔲 Planned |
| 20 | Extensible AI skills | 🔲 Planned |

---

## 📦 Progress Roadmap

### ✅ Day 01 — Project Foundation
- Project directory structure and directory placeholders
- Python virtual environment (`.venv`)
- TOML master configuration system (`zye_config.toml`)
- Environment variable separation (`.env` / `.env.example`)
- Security policies and Git ignore rules (`.gitignore`)
- Configuration validation utility (`scripts/validate_config.py`)
- Foundation automated test suite (`tests/test_day01_foundation.py` — 27 tests)
- Modular skills package initialization (`skills/__init__.py`)
- Planned dependency roadmap manifest (`requirements.txt`)

### ✅ Day 02 — Automated Environment Bootstrapper & Verification
- Automated Windows environment bootstrapper (`scripts/setup_env.ps1`)
  - Parameters: `-DryRun`, `-ApprovePackageDownloads`, `-SkipPyTorch`, `-SkipRequirements`, `-NoDoctor`
  - 23 modular functions covering platform, disk, RAM, Python version, manifest safety, and isolation
- Independent dependency verification engine (`scripts/verify_dependencies.py`)
  - Exact distribution-to-import mapping for all 33 planned dependencies
  - PyTorch CPU execution and tensor verification
  - JSON package inventory generator (`logs/day02_package_inventory.json`)
- Day 02 automated test suite (`tests/test_day02_environment.py` — 25 tests)
- Idempotent and fail-closed bootstrapper pipeline with detailed diagnostic logs (`logs/setup_env.log`)
- Structured installation report (`logs/day02_install_report.json`)

### ✅ Day 03 — Doctor Diagnostic Engine & Health Certification
- Standalone system diagnostic engine (`doctor.py` — 31 modular functions)
  - STAGE 1: Runtime & virtual environment isolation check
  - STAGE 2: Directory auto-initialization, permissions, and SQLite WAL database initialization (`data/zye_assistant_db.sqlite`)
  - STAGE 3: TOML configuration schema, .env validation, and Gemini API key placeholder detection
  - STAGE 4: 33-package dependency audit, CPU-only PyTorch validation, and Windows COM runtime verification
  - STAGE 5: Hardware audit (16 kHz mono microphone stream, speaker, RAM, disk, admin privileges, and future MCP registry)
  - STAGE 6: Health aggregation, ANSI terminal output, and structured report (`logs/doctor_report.json`)
- Telemetry & security alert logs (`logs/zye_errors.log`, `logs/zye_security_alerts.log`)
- Day 03 automated test suite (`tests/test_day03_doctor.py` — 50 tests)

### ✅ Day 04 — Universal MCP Safety Guard Engine (`zye_guard.py`)
- Universal `@zye_safe_skill(...)` decorator for all future MCP tools
- Function argument validation via `inspect.signature` & automatic binding
- Component-aware Windows path security & protected OS directory detection (`WINDIR`, `SystemRoot`, `ProgramFiles`, `ProgramData`)
- Strict path traversal (`..`), Alternate Data Streams (`:`), null byte (`\0`), and reserved device name blocking (`CON`, `PRN`, `AUX`, `NUL`, `COM1–9`, `LPT1–9`)
- Reversible file and directory boundary enforcement (`allowed_roots`, `require_files`)
- Synchronous and asynchronous coroutine execution support
- Exponential backoff automatic retry engine (`retry_safe=True`, default `False`)
- Structured JSON error responses (`GuardErrorResponse`) with unique 12-char `trace_id`
- Automatic sensitive credential redaction across error messages and tracebacks
- Traceback telemetry rotation (`logs/zye_errors.log`) and security alert audit log (`logs/zye_security_alerts.log`)
- Day 04 automated test suite (`tests/test_day04_guard.py` — 72 tests)

### ✅ Day 05 — Self-Repair MCP Engine Foundation (`self_repair_mcp.py`)
- FastMCP diagnostic server (`ZyeSelfRepair`) exposing 6 core MCP inspection tools
- Recent runtime error log reader (`read_recent_error_logs`) with bounded pagination (1–200 lines) and secret sanitization
- Project source code inspection (`read_own_source_code`) with exact 1-indexed line numbers and encoding detection
- Reversible project source discovery (`list_project_source_files`) excluding forbidden directories (`.venv`, `.git`, `profiles`, `data`, `backups`)
- Source file metadata and AST syntax validator (`inspect_source_file`) without code execution
- Atomic, timestamped source backup creation (`create_source_backup`) with fsync and pre/post SHA-256 comparison
- High-confidence embedded credential scanning prior to backup creation
- Backup listing and integrity verification (`list_source_backups`) via persistent `.meta.json` records
- Reusable Python traceback analysis engine (`parse_traceback_summary`, `classify_error_type`)
- Dedicated rotating audit logger (`logs/self_repair_audit.log`)
- Day 05 automated test suite (`tests/test_day05_self_repair.py` — 73 tests)
- Integration with `doctor.py` diagnostic engine (Stage 5 self-repair readiness certification)

### ✅ Day 06 — Autonomous Code Repair & MCP Hot-Reload Engine (`self_repair_mcp.py`, `main.py`)
- Two-phase patch approval workflow: `preview_code_patch` generates unified diff and candidate AST validation without modifying source files
- Cryptographically secure one-time approval token engine (`secrets.token_urlsafe(32)`) backed by SQLite (`repair_approvals` table) with SHA-256 token hashing
- Pre-save timestamped backup with SHA-256 integrity verification (`create_source_backup`) before every write
- Python AST syntax validation (`ast.parse`) reporting exact line numbers and syntax error diagnostics
- Compilation verification in clean isolated context (`compile(..., dont_inherit=True)`) without running code
- Atomic source file replacement preserving UTF-8 / UTF-8-BOM encoding and LF / CRLF line endings via staging files and `os.fsync`
- Automatic rollback (`automatic_rollback`) restoring verified pre-patch state if post-write verification fails
- Dedicated manual rollback MCP tool (`rollback_code_backup`) restoring any verified historical backup
- Central host agent orchestrator (`main.py` / `ZyeMasterAgent`) managing MCP sessions
- Zero-downtime MCP server hot-reloading (`hot_reload_server`) with in-flight call draining and tool registry updates
- Subprocess crash recovery (`call_mcp_with_recovery`) with strict safe-replay policy (non-idempotent operations return `OUTCOME_UNKNOWN`)
- Gemini API resilience layer (`call_gemini_with_retry`) with exponential backoff and jitter
- Complete repair transaction audit logging (`logs/code_repair_audit.log`) with secret redaction
- Day 06 automated test suite (`tests/test_day06_code_repair.py` — 92 tests)
- Full regression test suite: **339 automated unit tests passing across Days 01–06 (100% pass rate)**
- Integrated doctor certification (`doctor.py` Stage 5 code repair health checks & Stage 6 JSON report certification)

### ✅ Day 07 — Smart Audio Ear Foundation (`zye_audio_ear.py`)
- Real-time PortAudio microphone stream capture with non-blocking callback (`sounddevice`)
- Robust device discovery (`list_input_devices`, `get_default_input_device`, `validate_input_device`, `check_mic_health`)
- Sample rate negotiation and polyphase resampling to 16,000 Hz (`scipy.signal.resample_poly` with GCD reduction)
- Stereo-to-mono channel downmixing with clipping guards (`downmix_to_mono`)
- 0.64-second in-memory ring buffer (20 frames x 512 samples @ 16 kHz = 10,240 samples in RAM) preserving user's first word
- Thread-safe FIFO ring buffer (`PreRollBuffer`) with sub-microsecond snapshot creation
- Lightweight adaptive RMS baseline speech detector (`AdaptiveRMSDetector`) with noise-floor tracking EMA and hysteresis
- False trigger rejection (single-frame transient click rejection via consecutive frame confirmation)
- In-memory signed 16-bit PCM conversion and WAV byte serialization (`encode_wav_bytes` via `io.BytesIO`)
- Absolute privacy: 100% in-memory audio buffering; zero audio or transcript files written to disk or logs
- Hardware smoke test CLI utility (`scripts/check_audio_input.py` with interactive and `--auto` modes)
- Comprehensive doctor diagnostic integration (`doctor.py` Stage 5 audio checks & `"audio_input"` report section)
- Day 07 automated test suite (`tests/test_day07_audio_ear.py` — 71 tests)
- Full regression test suite: **410 automated unit tests passing across Days 01–07 (100% pass rate)**

### ✅ Day 08 — Neural Hearing Engine v2.0 (`zye_audio_ear.py`)
- Silero Neural Voice Activity Detection (VAD) ONNX model integration (`load_silero_vad(onnx=True)`)
- CPU-only execution provider (`CPUExecutionProvider`) with sub-millisecond inference (<0.8 ms per 32 ms frame; >40x faster than real-time)
- Strict 512-sample float32 16 kHz mono frame validation (`validate_vad_frame`, `prepare_vad_tensor`)
- Real-time speech probability calculation returning scalar confidence scores in `[0.0, 1.0]`
- Dual-threshold intelligence:
  - Speech-start trigger threshold: `0.52` (speech candidate filter)
  - Speech-hold threshold: `0.40` (syllable hysteresis preventing premature phrase cut-off)
- Consecutive frame confirmation (2 frames required to trigger speech state)
- Upgraded 11-state capture machine: `IDLE`, `BUFFERING`, `SPEECH_CANDIDATE`, `SPEECH_CONFIRMED`, `SPEECH_DETECTED`, `RECORDING`, `SHORT_PAUSE`, `SILENCE_DETECTED`, `FINALIZING`, `COMPLETED`, `CANCELLED`, `ERROR`
- Preserved Day 07 0.64s RAM ring buffer (20 frames x 512 samples @ 16 kHz = 10,240 samples in RAM) ensuring zero first-word or initial syllable loss
- Resilient automatic fallback engine: immediate fallback to Day 07 `AdaptiveRMSDetector` upon model load failure or consecutive inference errors (threshold: 3)
- Recurrent model state lifecycle management (`load_neural_vad`, `warmup_neural_vad`, `reset_vad_state`, `unload_neural_vad`, `get_vad_status`)
- Structured VAD telemetry reporting latencies (avg, p50, p95, max), errors, queue stats, and active backends
- Doctor diagnostic certification: `doctor.py` Stage 5 neural VAD validation
- Smoke test utility (`scripts/test_neural_vad.py` — 8-stage verification)
- Day 08 automated test suite (`tests/test_day08_neural_vad.py` — 75 tests)
- Full regression test suite: **485 automated unit tests passing across Days 01–08 (100% pass rate)**

---

## 🔧 Zye Self-Repair & Code Repair MCP Engine (`self_repair_mcp.py`)

The Self-Repair & Code Repair MCP Engine provides a secure diagnostic, automated code repairing, and recovery system for Zye AI. All tools are registered on FastMCP and secured with `@zye_safe_skill(...)`.

### Registered MCP Tools (9 Tools)

| # | Tool Name | Parameters | Purpose |
|---|---|---|---|
| 01 | `read_recent_error_logs` | `lines: int = 60` | Reads recent entries from `logs/zye_errors.log` with credential redaction |
| 02 | `read_own_source_code` | `filename: str, start_line: int, end_line: int` | Reads source code lines (max 300) with 1-based line numbering |
| 03 | `list_project_source_files` | `directory: str = ".", recursive: bool = False` | Lists project Python source files while filtering protected directories |
| 04 | `inspect_source_file` | `filename: str` | Retrieves file size, timestamp, SHA-256 digest, and AST syntax status |
| 05 | `create_source_backup` | `filename: str, reason: str` | Atomically creates a SHA-256 verified backup in `backups/` with `.meta.json` |
| 06 | `list_source_backups` | `filename: str = ""` | Lists previous backups and verifies file integrity against recorded hashes |
| 07 | `preview_code_patch` | `filename, old_snippet, new_snippet, reason` | Previews unified diff, checks AST syntax and compile without writing |
| 08 | `patch_own_code` | `filename, old_snippet, new_snippet, reason, patch_id, token, orig_hash` | Validates approval token, creates pre-save backup, replaces file atomically |
| 09 | `rollback_code_backup` | `filename, backup_id, approval_token` | Restores a specific verified historical backup atomically with approval |

### Python API Usage Examples

```python
import self_repair_mcp

# 1. Preview a code patch (non-destructive)
preview = self_repair_mcp.preview_code_patch(
    filename="skills/weather_skill.py",
    old_code_snippet="return temp - offset",
    new_code_snippet="return temp + offset",
    reason="Fix incorrect temperature offset subtraction",
)
print("Diff preview:\n", preview["data"]["diff"])
patch_id = preview["data"]["patch_id"]
orig_hash = preview["data"]["original_sha256"]
proposed_hash = preview["data"]["proposed_sha256"]

# 2. Request user approval token
app_id, token = self_repair_mcp.request_patch_approval(
    patch_id=patch_id,
    filename="skills/weather_skill.py",
    original_sha256=orig_hash,
    proposed_sha256=proposed_hash,
    operation="patch",
)

# 3. Apply approved patch atomically
result = self_repair_mcp.patch_own_code(
    filename="skills/weather_skill.py",
    old_code_snippet="return temp - offset",
    new_code_snippet="return temp + offset",
    reason="Fix incorrect temperature offset subtraction",
    patch_id=patch_id,
    approval_token=token,
    expected_original_sha256=orig_hash,
)
print("Patch status:", result["data"]["status"])
print("Backup created:", result["data"]["backup_file"])
```

---

## 🤖 Host Orchestration & MCP Hot-Reload (`main.py`)

The `ZyeMasterAgent` class provides client management, session lifecycle orchestration, crash recovery, and Gemini API resilience:

```python
from main import ZyeMasterAgent

agent = ZyeMasterAgent()

# 1. Zero-downtime hot-reload of an MCP server after patching
reload_result = await agent.hot_reload_server("self_repair")
print("Hot reload generation:", reload_result["generation"])

# 2. Safe execution with crash recovery
# If the MCP subprocess crashes, it restarts once and safely replays idempotent calls
result = await agent.call_mcp_with_recovery("read_recent_error_logs", {"lines": 30})

# 3. Non-idempotent operations (email, payment, delete) are NEVER replayed on crash:
# Returns OUTCOME_UNKNOWN to prevent duplicate external actions
```

---

## 🛡️ Zye Safety Guard Engine (`zye_guard.py`)

Every tool in the Zye MCP ecosystem is wrapped with `@zye_safe_skill(...)` to enforce deterministic safety boundaries, input validation, and execution sandboxing.

### 5 Production Usage Patterns:

#### 1. Safe File Creation (Boundary & Path Validation)
```python
from pathlib import Path
from zye_guard import zye_safe_skill

@zye_safe_skill(path_params=["dest_path"], allowed_roots=["data", "backups"])
def create_text_file(dest_path: str, content: str) -> dict:
    target = Path(dest_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"status": "success", "path": str(target), "bytes": len(content)}
```

#### 2. File Reading with Existence Pre-Checks (`require_files`)
```python
from pathlib import Path
from zye_guard import zye_safe_skill

@zye_safe_skill(require_files=["data/zye_assistant_db.sqlite"])
def read_system_database() -> dict:
    return {"status": "success", "message": "Database is verified and ready."}
```

#### 3. Asynchronous Safe Network Retrieval with Automatic Retry
```python
from zye_guard import zye_safe_skill

@zye_safe_skill(
    retry_safe=True,
    max_retries=3,
    retry_base_delay=0.8,
    retryable_exceptions=(ConnectionError, TimeoutError),
)
async def fetch_remote_intel(endpoint_url: str) -> dict:
    ...
```

#### 4. Non-Retryable Action (Explicit `retry_safe=False` Default)
```python
from zye_guard import zye_safe_skill

@zye_safe_skill()  # retry_safe is False by default
def send_user_notification(message: str) -> dict:
    return {"status": "sent", "message": message}
```

#### 5. Protected Windows Path & Traversal Rejection
```python
from zye_guard import zye_safe_skill

@zye_safe_skill(path_params=["filepath"])
def inspect_system_file(filepath: str) -> dict:
    return {"status": "ok"}
```

---

## 🎙️ Zye Smart Audio Ear Engine (`zye_audio_ear.py`)

The Smart Audio Ear Engine provides the real-time acoustic input foundation for Zye AI. It handles microphone detection, streaming capture, non-blocking buffering, channel downmixing, polyphase resampling, adaptive RMS baseline detection, and in-memory WAV generation.

### Key Architectural Components

```
Microphone Hardware (PortAudio)
       │
       ▼
Non-Blocking Stream Callback ──► Pre-Roll Ring Buffer (20 frames = 0.64s in RAM)
       │
       ▼
Bounded Frame Queue (100 frames max, drops oldest on overflow)
       │
       ▼
Consumer Loop (`listen_smart`)
       │
  ┌────┴──────────────────────────┐
  │  Adaptive RMS Detection       │
  │  - Noise-floor tracking EMA   │
  │  - Trigger multiplier (2.4x)  │
  │  - Hold multiplier (1.8x)     │
  │  - 2-frame click rejection    │
  └────┬──────────────────────────┘
       │
  [Speech Detected]
       │
  Capture Pre-Roll Snapshot + Live Speech Frames
       │
  ┌────┴──────────────────────────┐
  │  Format Standardization       │
  │  - Stereo-to-mono downmixing  │
  │  - Polyphase resample to 16kHz│
  │  - Float32 -> Int16 PCM conv  │
  │  - In-memory WAV serialization│
  └────┬──────────────────────────┘
       │
       ▼
WAV Bytes (Signed 16-bit PCM, 16,000 Hz, Mono) — 100% In-Memory
```

### Python API Usage Examples

```python
from zye_audio_ear import SmartAudioEar, AudioConfig, list_input_devices

# 1. Inspect available input hardware
devices = list_input_devices()
print(f"Found {len(devices)} microphone(s)")

# 2. Initialize ear with customized configuration
config = AudioConfig(
    sample_rate=16000,
    channels=1,
    pre_roll_duration=0.64,
    silence_timeout_seconds=0.75,
    max_record_seconds=15.0,
)
ear = SmartAudioEar(config=config)

# 3. Listen for speech with first-word preservation
print("Listening... speak to Zye!")
wav_bytes = ear.listen_smart(silence_timeout=0.8, max_record_sec=10.0)

if wav_bytes:
    print(f"Captured speech utterance: {len(wav_bytes)} bytes WAV")
else:
    print("No speech detected (timed out)")

# 4. Retrieve structured diagnostics
diag = ear.get_audio_diagnostics()
print(f"Noise floor: {diag['noise_floor_rms']:.5f}, Stream state: {diag['state']}")

ear.close()
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 / 3.12 |
| OS | Windows 10 x64 / Windows 11 x64 |
| Audio Input Ear | `zye_audio_ear.py` (sounddevice, PortAudio, scipy, numpy) |
| Audio Diagnostics | `scripts/check_audio_input.py` |
| Autonomous Code Repair | `self_repair_mcp.py`, `main.py` (ast, compile, difflib, sqlite3) |
| Self-Repair MCP | `self_repair_mcp.py` (FastMCP, tokenize, ast, hashlib) |
| Tool Safety | `zye_guard.py` (Universal `@zye_safe_skill` decorator) |
| Diagnostics | `doctor.py` (psutil, sounddevice, ctypes, sqlite3, tomllib) |
| Database | SQLite 3 (WAL journal mode verified) |
| Configuration | TOML (tomllib) & Environment variables (.env) |
| Automation | PowerShell 5.1 / 7+ |
| AI Runtime | Google GenAI SDK, Ollama, CPU-only PyTorch |
| Testing | Python unittest (410 automated tests passing, 100% pass rate) |
| Version Control | Git |
| Environment | Standard Python venv |

---

## 📁 Project Structure

```
Zye_Assistant/
├── .venv/                              # Python virtual environment
├── scripts/
│   ├── setup_env.ps1                   # Automated environment bootstrapper
│   ├── validate_config.py              # Configuration validation utility
│   ├── verify_dependencies.py          # Dependency verification engine
│   └── check_audio_input.py            # Audio input hardware smoke test script
├── skills/
│   └── __init__.py                     # Modular skills package
├── data/
│   ├── zye_assistant_db.sqlite         # SQLite database (WAL mode verified)
│   └── cad_models/
│       └── .gitkeep                    # Future CAD/engineering outputs
├── logs/
│   ├── .gitkeep                        # Logs directory placeholder
│   ├── doctor_report.json              # Doctor diagnostic report
│   ├── zye_errors.log                  # Structured error diagnostic log
│   ├── zye_security_alerts.log         # Security alert events log
│   ├── self_repair_audit.log           # Self-repair operations audit log
│   ├── code_repair_audit.log           # Code repair operations audit log
│   ├── setup_env.log                   # Bootstrapper execution log
│   ├── day02_install_report.json       # Structured install report
│   └── day02_package_inventory.json    # Verified package inventory
├── backups/
│   └── .gitkeep                        # Canonical backup storage (.py.bak & .meta.json)
├── profiles/
│   └── .gitkeep                        # Future browser profiles
├── tests/
│   ├── test_day01_foundation.py        # Day 01 foundation tests (27 tests)
│   ├── test_day02_environment.py       # Day 02 environment tests (25 tests)
│   ├── test_day03_doctor.py            # Day 03 doctor diagnostic tests (50 tests)
│   ├── test_day04_guard.py             # Day 04 guard engine tests (72 tests)
│   ├── test_day05_self_repair.py       # Day 05 self-repair tests (73 tests)
│   ├── test_day06_code_repair.py       # Day 06 code repair tests (92 tests)
│   └── test_day07_audio_ear.py         # Day 07 smart audio ear tests (71 tests)
├── .env                                # Local credentials (git-ignored)
├── .env.example                        # Credential template
├── .gitignore                          # Git exclusion rules
├── zye_config.toml                     # Master configuration
├── requirements.txt                    # Planned dependency manifest
├── requirements-lock.txt               # Installed package lockfile (post-install)
├── README.md                           # Master project documentation
├── doctor.py                           # Master health diagnostic engine
├── zye_guard.py                        # Universal MCP safety guard engine
├── self_repair_mcp.py                  # Self-repair & code repair MCP server
├── zye_audio_ear.py                    # Smart audio ear input engine
└── main.py                             # Master agent orchestrator & hot-reload host
```

---

## 🚀 Execution & Verification Commands

### 1. Run Complete Automated Test Suite (410 Tests Across Days 01–07)
Run all unit tests across all seven days:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 2. Run Day 07 Smart Audio Ear Tests Specifically (71 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_day07_audio_ear -v
```

### 3. Run Audio Hardware Smoke Test Utility
Automated non-interactive hardware verification:
```powershell
.\.venv\Scripts\python.exe scripts\check_audio_input.py --auto
```
Interactive hardware diagnostic:
```powershell
.\.venv\Scripts\python.exe scripts\check_audio_input.py
```

### 4. Run Day 06 Code Repair Tests Specifically (92 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_day06_code_repair -v
```

### 5. Run Day 05 Self-Repair Tests (73 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_day05_self_repair -v
```

### 6. Run Day 04 Safety Guard Tests (72 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_day04_guard -v
```

### 7. Run Doctor Diagnostic Engine
Execute complete health diagnostic:
```powershell
.\.venv\Scripts\python.exe doctor.py
```
For machine-readable JSON output:
```powershell
.\.venv\Scripts\python.exe doctor.py --json
```

### 8. Verify SQLite Database & WAL Mode
```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/zye_assistant_db.sqlite'); print('WAL:', c.execute('PRAGMA journal_mode').fetchone()[0]); print('Integrity:', c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
```

### 9. Inspect Audit Trails
```powershell
Get-Content .\logs\code_repair_audit.log -Tail 20
Get-Content .\logs\self_repair_audit.log -Tail 20
```

---

## 🔒 Security Rules & Defenses

1. **Acoustic Privacy by Design:** 100% in-memory audio buffering; raw microphone audio is never written to disk, temporary folders, or logs.
2. **Offline Audio Processing:** `zye_audio_ear.py` contains zero network calls or cloud uploads. All DSP, resampling, and format conversions execute locally.
3. **Bounded Memory Footprint:** Frame queues and pre-roll ring buffers are strictly bounded in RAM (20 frames = ~40 KB) to prevent memory exhaustion.
4. **Two-Phase Code Approval Gate:** Patches cannot be applied directly. A preview must first generate unified diffs and token requests; the user must grant an explicit one-time cryptographically secure token (`secrets.token_urlsafe(32)`).
5. **Pre-Save Verified Backup:** Before any source file is modified, a full pre-save backup is written to `backups/` and verified with SHA-256 byte comparison.
6. **AST Syntax & Compilation Verification:** Candidate patches are parsed with `ast.parse` and compiled with `compile(..., dont_inherit=True)` in an isolated context without running code.
7. **Atomic Replacement & Automatic Rollback:** Updates are written to a temporary staging file with `os.fsync` and atomically replaced via `os.replace`. If post-write verification fails, automatic rollback immediately restores the verified pre-patch state.
8. **Critical Framework File Immunity:** Automated patching is strictly prohibited on `zye_guard.py`, `self_repair_mcp.py`, `zye_audio_ear.py`, `doctor.py`, and `.env`.
9. **Zero Replay for Non-Idempotent Actions:** On transport failure or subprocess crash, non-idempotent operations are NEVER replayed; `OUTCOME_UNKNOWN` is returned.
10. **Audit Trail Accountability:** Every preview, token generation, token consumption, AST check, compilation check, patch, and rollback is logged with credential redaction.

---

## 🗺️ Next Steps

### Day 08 — Silero Neural Voice Activity Detection (VAD) & Speech Boundary Engine
- Offline Silero VAD ONNX model loading and CPU inference
- Neural speech probability scoring (>0.5 probability threshold)
- Hybrid RMS + Neural VAD boundary detection with smooth speech transitions
- Automatic speech endpointing and background noise suppression

### Day 09 — Dynamic Speech Normalization (AGC) & Synthesized Jarvis Earcons
- Real-time Automatic Gain Control (AGC) with peak limiting
- Synthesized listening start/stop earcons via NumPy sine wave generation (zero external audio files)
- Pygame sound cue playback integration

### Day 10 — Edge-TTS Neural Voice Engine, System Tray & Voice-Driven Main Loop
- Edge-TTS streaming speech synthesis with neural voices (Tamil & English support)
- Global hotkey listener (Alt + Z text input fallback)
- Integration of `SmartAudioEar` into `main.py` autonomous listening loop

---

*Built with precision. Designed for growth. Secured by default.*
