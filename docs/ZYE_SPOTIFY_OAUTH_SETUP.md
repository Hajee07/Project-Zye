# ZYE AI — Spotify OAuth 2.0 Authorization Setup Guide

## 1. Overview
Spotify Web API requires OAuth 2.0 authorization code flow with PKCE or client secret exchange.
Zye protects your credentials by storing configuration outside the code repository in:
`C:\ZyeSecrets\spotify-config.json`

---

## 2. Protected Configuration File
Path: `C:\ZyeSecrets\spotify-config.json`

```json
{
  "clientId": "13d7f564c564416dae3b4e7fa408b7f3",
  "clientSecret": "92ef2af6688a417793677103d971b909",
  "redirectUri": "http://127.0.0.1:8888/callback"
}
```

> [!SECURITY]
> The configuration file is excluded from Git version control via `.gitignore`.
> Never commit secrets or tokens into version control or share them in public logs.

---

## 3. Required Spotify Developer Application Settings
1. Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Select your registered application (`Zye AI`).
3. Click **Settings** and ensure the following:
   - **Redirect URIs**: Add `http://127.0.0.1:8888/callback` and `http://localhost:8888/callback`.
   - **APIs Used**: Web API.
   - **Development Mode**: Note that user accounts must be explicitly added to the **User Management** section in development mode.

---

## 4. Required OAuth 2.0 Scopes
The Zye Spotify MCP server requests the following least-privilege scopes:
- `user-read-playback-state`: Read player state and active devices.
- `user-modify-playback-state`: Control playback (play, pause, next, volume, seek).
- `user-read-currently-playing`: Retrieve currently playing track metadata.
- `playlist-read-private`: Browse user playlists.
- `playlist-modify-public`: Modify public playlists.
- `playlist-modify-private`: Modify private playlists.
- `user-library-read`: Read saved tracks and albums.
- `user-library-modify`: Save tracks/albums to library.
- `user-top-read`: Retrieve top tracks and artists.
- `user-read-recently-played`: Retrieve recently played history.
- `user-follow-read`: Retrieve followed artists.

---

## 5. One-Time Authorization Flow
When running the Spotify MCP server for the first time:
```powershell
cd d:\Zye\external_mcp\spotify-mcp-server
$env:SPOTIFY_CONFIG_PATH="C:\ZyeSecrets\spotify-config.json"
node build/index.js
```
The server will print an authorization URL or open a browser window to `http://127.0.0.1:8888/callback`.
Once authorized in the browser:
1. Spotify sends an authorization code to the loopback server.
2. The server exchanges the code for access and refresh tokens.
3. Tokens are encrypted and persisted into `C:\ZyeSecrets\spotify-config.json`.
4. The server automatically refreshes tokens upon expiration.

---

## 6. Spotify Connect Devices
To control playback via Spotify Web API:
1. Ensure the Spotify desktop app, web player, or mobile app is running on at least one device under your account.
2. The device will be discovered by `getAvailableDevices` / `get_available_playback_devices`.
