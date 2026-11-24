# ZYE AI — Smart Music System Forensic Root-Cause Audit (P0)

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Classification:** Critical P0 Root-Cause Forensic Audit  
**Target Platform:** Windows 10 / Windows 11  
**Audited Modules:** `zye_music/`, `main.py`, `zye_gemini_live.py`, `external_mcp/spotify-mcp-server/`  
**Status:** ALL 5 DEFECTS DIAGNOSED AT ROOT CAUSE  

---

## 1. Executive Summary

A forensic audit of the ZYE AI music subsystem was conducted to investigate:
1. Inability to determine whether music is actually streaming from Spotify.
2. Repeated playback of the same melody (`AR Rahman Style - Pure Melody.wav`) regardless of requested song.
3. Song selection insensitivity (different song queries producing identical audio output).
4. Unintended mixing of Spotify, local audio playback, and Gemini responses.
5. Missing search arguments (`q` vs `query`), empty tool calls (`search_music({})`), and silent local fallback.

Every defect was traced to specific lines of code in the existing repository.

---

## 2. Forensic Breakdown of Diagnosed Defects

### Defect 1: The "Repeated Melody" Root Cause
- **Evidence:**
  `zye_music/local_music_provider.py` lines 231–239:
  ```python
  else:
      # Pick first track in playlist or library
      if self._playlist:
          target_track = self._playlist[0]
          self._current_index = 0
      elif self._tracks:
          target_track = self._tracks[0]  # <--- ALWAYS AR Rahman Style - Pure Melody.wav!
          self._playlist = list(self._tracks)
          self._current_index = 0
  ```
  `zye_gemini_live.py` line 806:
  ```python
  "- When asked for any random or ambient song (e.g. 'ஏதாச்சும் ஒரு சாங் பாடு', 'edhavadhu oru paatu', 'oru song podu'), call play_music() with empty string or 'melody'.\n"
  ```
  `zye_music/music_preferences.py` lines 88–94:
  All contextual fallbacks returned `"morning melody fresh"`, `"relaxing evening melody"`, or `"soft midnight melody"`.
- **Mechanism:**
  Whenever Gemini Live handled an open-ended song request (or fell back after a failed search), it invoked `play_music()` with empty string or `"melody"`.
  The local music library in `d:/Zye/data/music/` contains 5 files. Because `_tracks[0]` was hardcoded and search for `"melody"` matched `AR Rahman Style - Pure Melody.wav`, the exact same audio file was loaded into `pygame.mixer.music` on every single song request!

### Defect 2: Broken Spotify MCP Tool Dispatch in `main.py`
- **Evidence:**
  `main.py` lines 1111–1126 registered Spotify tools with the prefix `spotify_`:
  ```python
  "spotify_search", "spotify_play_music", "spotify_pause_playback", ...
  ```
  `main.py` line 1491:
  ```python
  mcp_tool_name = tool_name[8:] if tool_name.startswith("spotify_") else tool_name
  return self.spotify_adapter.call_tool(mcp_tool_name, args)
  ```
- **Mechanism:**
  When Gemini Live invoked `spotify_search`, `tool_name[8:]` evaluated to `"search"`.
  However, in `external_mcp/spotify-mcp-server/src/read.ts`, the actual tool name is `searchSpotify`!
  Likewise:
  - `spotify_play_music` became `"play_music"`, but the MCP tool is `playMusic`.
  - `spotify_get_now_playing` became `"get_now_playing"`, but the MCP tool is `getNowPlaying`.
  - `spotify_get_available_devices` became `"get_available_devices"`, but the MCP tool is `getAvailableDevices`.
  Consequently, every Spotify MCP tool call failed with `"Tool not found"`.

### Defect 3: Missing Search Argument Mapping (`q` vs `query`)
- **Evidence:**
  `spotify_search` was called by Gemini with `{"q": "Kannana Kanne"}`.
  `external_mcp/spotify-mcp-server/src/read.ts` schema:
  ```typescript
  schema: {
    query: z.string(),
    type: z.enum(SEARCH_TYPES),
    limit: z.number().optional(),
    offset: z.number().optional(),
  }
  ```
- **Mechanism:**
  The Spotify MCP server validates arguments using Zod. Passing `q` instead of `query` resulted in a Zod validation error (`Required field 'query' is missing`).

### Defect 4: Silent Provider Fallback
- **Evidence:**
  `zye_music/provider_router.py` lines 86–94:
  When `spotify_search` failed, Gemini Live called `search_music({})` or `play_music()`.
  Because no provider was explicitly passed, `origin == InputOrigin.VOICE` silently resolved to `local_provider`.
  The local provider looked for "Kannana Kanne" in `data/music`, found nothing, returned `TRACK_NOT_FOUND`, and then Gemini called `play_music()` with no query, which triggered `_tracks[0]` (Pure Melody).
  At no point was the user informed that Spotify failed or that a local fallback occurred.

### Defect 5: False-Success & Error Masking in Spotify MCP
- **Evidence:**
  `external_mcp/spotify-mcp-server/src/utils.ts` line 707:
  ```typescript
  if (err?.status === 200 && msg.includes('Unexpected end of JSON input')) {
    return undefined as T;
  }
  ```
  `external_mcp/spotify-mcp-server/src/play.ts`:
  Certain error cases returned `isError: false` or placed error text inside content without flagging the top-level MCP `isError` field, causing the Python MCP host to classify failed executions as success.

---

## 3. Required Engineering Source Changes

1. **`main.py`**:
   Replace naive `tool_name[8:]` slicing with explicit `SPOTIFY_TOOL_NAME_MAP` mapping `spotify_search` -> `searchSpotify`, `spotify_play_music` -> `playMusic`, etc.
   Normalize argument keys (`q` -> `query`, default `type="track"`).
2. **`zye_gemini_live.py`**:
   Remove line 806 (`call play_music() with empty string or 'melody'`). Replace with explicit instructions passing `'any'` for open-ended requests and exact song titles for specific requests.
3. **`zye_music/local_music_provider.py`**:
   Implement `DiverseTrackSelector` (history size 10, current-track exclusion, non-repeating choice).
   Eliminate hardcoded `self._tracks[0]`.
4. **`zye_music/provider_router.py`**:
   Enforce fail-closed provider selection. If Spotify is requested and fails/unauthorized, return typed error; NEVER silently fall back to local melody.
5. **`zye_music/spotify_mcp_adapter.py`**:
   Add `build_spotify_search_args()`, normalize queries, handle structured search responses.
6. **`external_mcp/spotify-mcp-server/src/read.ts` & `src/playback-verifier.ts`**:
   Add structured JSON search result output.
   Add exact track identity verification (`verifyExactTrackPlayback`).
   Rebuild TypeScript via `npm run build`.
7. **Windows Audio Attribution (`audio_source_attribution.py`)**:
   Inspect active Windows audio sessions via CoreAudio/WASAPI/comtypes to correlate audible output with process identity (Spotify.exe vs python.exe).
