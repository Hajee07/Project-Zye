# ZYE AI — Smart Music System Setup & Architecture Guide

## 1. System Overview
The **ZYE Smart Music System** integrates zero-foreground local audio playback and Spotify Connect control into the existing Zye AI assistant architecture on Windows 10/11.

It provides:
- **Mode A (Manual Spotify MCP Control)**: Compliant Web API tool execution via MCP stdio client.
- **Mode B (Local Music Voice Control)**: Zero-friction voice playback using headless Pygame mixer supporting `.mp3`, `.wav`, `.ogg`, `.flac`, and `.m4a` files.
- **Mode C (Spotify Voice Control Gate)**: Strictly enforces Spotify Developer Policy compliance in Development Mode; prevents unverified voice control while allowing local voice control.
- **Multilingual Alexa-Style Intent Routing**: Instant natural language parsing in Tamil, English, and Tanglish.
- **Speech-Aware Audio Ducking**: Seamlessly ramps down background audio to 20% volume during user speech and Gemini assistant responses, restoring volume smoothly on turn completion.

---

## 2. Directory Layout
```
d:\Zye\
├── zye_music\
│   ├── __init__.py
│   ├── music_models.py           # Typed track, state, and intent data models
│   ├── music_errors.py           # Structured error codes (Section 48)
│   ├── music_authorization.py    # Policy gate (Mode A vs Mode B vs Mode C)
│   ├── provider_interface.py     # Unified MusicProvider ABC
│   ├── local_music_provider.py   # Headless Pygame background player
│   ├── spotify_mcp_adapter.py    # Stdio JSON-RPC bridge to Node MCP server
│   ├── provider_router.py        # Gated router and intent dispatcher
│   ├── music_intent_router.py    # Tamil/Tanglish/English NL parser
│   ├── music_search.py           # NFC Unicode & token similarity search
│   ├── music_preferences.py      # Mood & time-of-day contextual resolver
│   ├── volume_manager.py         # Clamped volume [0-100] & mute memory
│   ├── audio_ducking.py          # Async-locked volume ducker & restorer
│   ├── audio_lifecycle_adapter.py# Gemini Live hook adapter
│   └── playback_verifier.py      # Bounded read-back polling engine
├── external_mcp\
│   └── spotify-mcp-server\       # TypeScript MCP Server build
└── C:\ZyeSecrets\
    └── spotify-config.json       # Protected credentials
```

---

## 3. Configuration in `zye_config.toml`
```toml
[music]
enabled = true
default_provider = "local"
allow_spotify_voice_experimental = false
default_volume = 80
auto_rescan_library_on_startup = true

[local_music]
music_directories = ["d:/Zye/data/music", "C:/Users/<User>/Music"]
supported_formats = [".mp3", ".wav", ".ogg", ".flac", ".m4a"]
enable_metadata_cache = true

[spotify]
mcp_server_script = "d:/Zye/external_mcp/spotify-mcp-server/build/index.js"
config_path = "C:/ZyeSecrets/spotify-config.json"
node_executable = "node"
device_activation_timeout_seconds = 5
max_reconnect_attempts = 3

[audio_ducking]
enabled = true
ducked_volume_percentage = 20
ramp_duration_ms = 150
restore_delay_ms = 200

[music_performance]
search_limit = 10
bounded_poll_interval_ms = 100
bounded_poll_timeout_ms = 2000

[music_privacy]
log_track_names = true
redact_spotify_tokens = true
```

---

## 4. Voice Commands (Tamil, English, Tanglish)

| Command Category | English | Tanglish | Tamil (Unicode) |
|---|---|---|---|
| **Play** | "Play Master song" | "Anirudh song podu" | "பாட்டு போடு" |
| **Pause** | "Pause music" | "Paata niruthu" / "Pause pannu" | "நிறுத்து" |
| **Resume** | "Resume music" | "Thodaru" / "Resume pannu" | "தொடரு" |
| **Next Track** | "Next track" | "Adutha paatu" / "Skip pannu" | "அடுத்த பாட்டு" |
| **Previous Track**| "Previous track" | "Munthaiya paatu" / "Back podu" | "முந்தைய பாட்டு" |
| **Volume Control**| "Set volume to 50%" | "Satham kootu" / "Satham kora" | "சத்தம் கூட்டு" |
| **Mute / Unmute** | "Mute music" | "Pesama iru" / "Unmute pannu" | "அமைதியா இரு" |
| **Now Playing** | "What song is this?" | "Enna paatu idhu?" | "என்ன பாட்டு இது?" |

---

## 5. Doctor Health Check Commands
```powershell
# Run overall Smart Music health diagnostic
python doctor.py --music-health

# Verify Spotify MCP Server build & configuration
python doctor.py --spotify-mcp-health

# Verify Local Music Player engine & library
python doctor.py --local-music-health

# Verify Audio Ducking & volume restoration
python doctor.py --audio-ducking-health

# Run full Pytest regression suite
python doctor.py --music-regression
```
