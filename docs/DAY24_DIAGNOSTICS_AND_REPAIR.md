# Zye AI — Day 24: Diagnostics, Health Checks & Self-Healing

## 1. Doctor Stage 20 Integration

Day 24 adds **Stage 20: Universal Chrome Browser Intelligence & Playwright Automation** to `doctor.py`.

### Diagnostic Checks in Stage 20:
1. **`d24_playwright_installed`**: Verifies `playwright` package in `.venv`.
2. **`d24_host_chrome_binary`**: Verifies installed Google Chrome 64-bit binary (`C:\Program Files\Google\Chrome\Application\chrome.exe`).
3. **`d24_chrome_local_state`**: Verifies host Chrome User Data directory and `Local State` profile discovery.
4. **`d24_browser_profiles_storage`**: Verifies persistent profiles storage directory permissions.
5. **`d24_browser_configs`**: Verifies all 3 configuration files (`browser_profiles.toml`, `browser_security.toml`, `web_apps.toml`).
6. **`d24_zye_browser_package`**: Verifies `zye_browser` module imports and 57 exported symbols.
7. **`d24_browser_mcp_server`**: Verifies `browser_accounts_mcp.py` syntax and FastMCP tool registrations.
8. **`d24_profile_registry`**: Verifies JSON profile registry loading and profile counts.

---

## 2. CLI Execution Flags

```bash
# Run Stage 20 Browser Diagnostics only:
.venv\Scripts\python.exe doctor.py --day24-check

# Run Full System Diagnostics across all 20 stages:
.venv\Scripts\python.exe doctor.py
```

---

## 3. Self-Healing & Failure Recovery

### Stale Lock Recovery
If Chrome or a previous session crashed, `ProfileLockManager.clean_stale_locks()` automatically inspects the PID recorded in `.zye_lock`. If `psutil.pid_exists(pid)` is False, the lock is purged automatically on the next launch request without manual intervention.

### Fallback to Isolated Storage
If `%LOCALAPPDATA%` is inaccessible or restricted by a sandboxed environment, `ProfilePathValidator` automatically falls back to `<workspace>\data\browser_profiles`, ensuring zero test failures.

### Element Ambiguity Guard
If a user requests a click on an element that matches multiple visible nodes on screen, `WebElementResolver` raises `DOMElementAmbiguousError` and presents candidate options instead of clicking the wrong button blindly.
