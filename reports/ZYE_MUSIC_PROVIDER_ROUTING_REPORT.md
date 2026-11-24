# ZYE AI — Music Provider Routing & Policy Gating Report

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Components:** `zye_music/provider_router.py`, `zye_music/music_authorization.py`  
**Compliance Framework:** Spotify Developer Terms of Service & Privacy Policy  
**Status:** FAIL-CLOSED POLICY GATING OPERATIONAL  

---

## 1. Compliance Architecture & Operational Modes

Under Section 03 & Section 14 of the Master Engineering Specification:

| Mode | Operation | Input Origin | Allowed Policy | Routing Target |
| :--- | :--- | :--- | :--- | :--- |
| **Mode A** | Manual Spotify MCP Control | Tools / Orchestrator / API | **ALLOWED** | `SpotifyMCPAdapter` |
| **Mode B** | Local Music Control | Voice / Speech | **ALLOWED** | `LocalMusicProvider` |
| **Mode C** | Spotify Voice Control | Voice / Speech | **RESTRICTED** (Blocked by default) | Requires explicit opt-in in `zye_config.toml` |

---

## 2. Fail-Closed Routing Logic

The previous implementation silently fell back to `local_provider` when Spotify failed or was requested via voice. This masked failures and caused the assistant to play local files unexpectedly.

### Repaired Fail-Closed Behavior
1. If the user explicitly requests Spotify (or default is Spotify) and Spotify is unavailable or unconfigured:
   - System raises `MusicAuthorizationError(code=SPOTIFY_CONFIG_MISSING)`.
   - Never falls back to local music.
2. If Spotify is requested via Voice without explicit experimental authorization:
   - System raises `MusicAuthorizationError(code=SPOTIFY_VOICE_NOT_AUTHORIZED)`.
   - Informs the user clearly without playing a substitute local track.
3. If an open-ended request is made via Voice:
   - System routes cleanly to `LocalMusicProvider` using `DiverseTrackSelector`.

---

## 3. Verified Diagnostic Output
Running `python doctor.py --music-provider-routing`:
```
============================================================
  ZYE AI — MUSIC PROVIDER ROUTING & FAIL-CLOSED DIAGNOSTICS
============================================================
  [1] Manual Tool Spotify Routing: PASS (resolved=spotify)
  [2] Voice Local Music Routing  : PASS (resolved=local)
  [3] Voice Spotify Policy Check  : PASS (Fail-Closed Blocked: SPOTIFY_VOICE_NOT_AUTHORIZED)
  [4] Default Voice Provider      : PASS (default=local)
============================================================
```
