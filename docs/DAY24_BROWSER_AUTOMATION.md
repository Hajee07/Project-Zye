# Zye AI — Day 24: Playwright Browser Automation & Security Controls

## 1. Engine Architecture

Zye uses Microsoft Playwright for Python with Google Chrome Stable (`channel="chrome"`).

### Persistent Browser Context Launch:
```python
context = await playwright.chromium.launch_persistent_context(
    user_data_dir=str(profile_path),
    channel="chrome",
    headless=headless_mode,
    viewport={"width": 1280, "height": 850},
    args=[
        "--disable-blink-features=AutomationControlled",
        "--no-default-browser-check",
        "--disable-features=IsolateOrigins,site-per-process",
    ],
    accept_downloads=True,
)
```

---

## 2. URL Validation & Security Shield

`BrowserURLValidator` prevents SSRF, local port attacks, and execution of untrusted scripts:

1. **Protocol Restrictions:**
   - Allowed: `http://`, `https://`
   - Blocked: `javascript:`, `file:`, `data:`, `blob:`, `vbscript:`
2. **Local Loopback & Private IP Defense:**
   - Blocks `localhost`, `127.0.0.1`, `::1`, `0.0.0.0` unless `allow_localhost=True`.
   - Blocks RFC 1918 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
3. **Automatic Normalization:**
   - Prepends `https://` if domain was passed bare (e.g. `google.com` -> `https://google.com`).

---

## 3. Tab Management & Navigation

- **Tab Enumeration:** Lists all open tabs with URLs, titles, and active state.
- **Tab Switching:** Focuses tab by integer ID.
- **Tab Creation & Closure:** Creates new tabs or closes background/active tabs safely.
- **History Actions:** Supports `go_back()`, `go_forward()`, and `reload()`.
