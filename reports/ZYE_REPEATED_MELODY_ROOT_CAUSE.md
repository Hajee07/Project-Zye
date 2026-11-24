# ZYE AI — The Repeated Melody Defect Forensic Timeline & Root-Cause Analysis

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Defect Severity:** P0 — Critical Voice & Music Experience Regression  
**Identified Sound:** `d:\Zye\data\music\AR Rahman Style - Pure Melody.wav`  
**Playback Engine:** Local Python Pygame Mixer (`pygame.mixer.music`)  
**Status:** PERMANENTLY RESOLVED  

---

## 1. The Symptom
The user reported:
> "Whenever I ask Zye for a song, it repeatedly plays the same melody. Requesting different songs does not change the playing track."

---

## 2. Complete Forensic Chain of Events

```
User Voice Request: "ஏதாச்சும் ஒரு சாங் பாடு" (Sing any song)
           │
           ▼
[Step 1: Gemini Live Prompt Instruction]
  zye_gemini_live.py line 806 explicitly told Gemini:
  "When asked for any random or ambient song, call play_music() with empty string or 'melody'."
           │
           ▼
[Step 2: Tool Call Dispatched to main.py]
  Gemini invoked: play_music(query="melody")
           │
           ▼
[Step 3: Tool Execution in LocalMusicProvider]
  zye_music/local_music_provider.py lines 231-239:
  - If query is empty or "any" or "melody":
    target_track = self._tracks[0]  <--- HARDCODED FIRST TRACK!
  - In d:/Zye/data/music/, the alphabetically first track was:
    "AR Rahman Style - Pure Melody.wav"
           │
           ▼
[Step 4: Pygame Mixer Playback]
  pygame.mixer.music.load("d:/Zye/data/music/AR Rahman Style - Pure Melody.wav")
  pygame.mixer.music.play()
           │
           ▼
[Step 5: Subsequent Song Requests (e.g. "Kannana Kanne")]
  - Gemini tried spotify_search(q="Kannana Kanne")
  - main.py stripped tool_name to "search" (Tool not found in MCP)
  - Gemini fell back to search_music({}) or play_music("melody")
  - Triggered target_track = self._tracks[0] again!
```

---

## 3. The 3 Root Causes That Compounded
1. **Hardcoded Index 0:** `local_music_provider.py` defaulted to `self._tracks[0]`.
2. **Prompt Hardcoding:** `zye_gemini_live.py` line 806 literally ordered the LLM to request `'melody'`.
3. **Broken Spotify MCP Dispatch:** Slicing `tool_name[8:]` made every Spotify tool fail, forcing fallback to local.

---

## 4. Permanent Remediation Applied
1. **Replaced `self._tracks[0]` with `DiverseTrackSelector`:**
   Open-ended requests now dynamically select across all available tracks, excluding the currently playing track and tracks in the recent history window (size 10).
2. **Removed Prompt Hardcoding:**
   Updated `zye_gemini_live.py` to instruct Gemini to pass the exact user song title or `'any'`, and never force `'melody'`.
3. **Fixed Tool Name Dispatch:**
   Mapped all `spotify_*` tool names to exact camelCase names in `external_mcp/spotify-mcp-server/`.
4. **Added Exclusion Filtering:**
   Supported negative queries (e.g. `"melody vendaam"` / `"no melody"`) to explicitly filter out melody tracks.
5. **No Track-Not-Found Fallback Audio:**
   If a requested specific song is not in the library, the system returns `TRACK_NOT_FOUND` and speaks a truthful error instead of playing an unrelated melody.
