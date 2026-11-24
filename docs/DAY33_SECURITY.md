# Day 33 Security Architecture: Path Traversal, SSRF & Injection Defense

## 1. Overview

Because search operations interact with both the local desktop filesystem and the public internet, Day 33 enforces defense-in-depth across three security boundaries:
1. **Local Search Policy (Filesystem Boundary)**
2. **SSRF Protection Policy (Network Boundary)**
3. **Untrusted Content Guard (Model Context Boundary)**

---

## 2. Security Defense Matrix

| Threat Vector | Attack Vector Example | Defense Mechanism | Mitigation Result |
|---|---|---|---|
| **Path Traversal** | `../../Windows/System32` | `LocalSearchPolicy.validate_file_access` | Access Denied, `LocalSearchSecurityError` |
| **Credential Exfiltration** | `.env`, `id_rsa`, `cookies.sqlite` | Forbidden extension & filename patterns | File access blocked before read |
| **Recursive Traversal** | `.venv`, `node_modules`, `.git` | In-place subtree pruning in `os.walk` | Traversal aborted at folder root |
| **Localhost SSRF** | `http://127.0.0.1:8080/admin` | `SSRFProtectionPolicy.is_private_ip` | URL blocked, `WebSecurityError` |
| **Cloud Metadata SSRF** | `http://169.254.169.254/latest` | Hardcoded metadata IP blocklist | URL rejected |
| **Internal Domain SSRF** | `http://router.local/status` | Suffix blacklist (`.local`, `.internal`) | Domain rejected |
| **Non-HTTP Protocols** | `file:///C:/Windows/win.ini` | Protocol scheme whitelist (`http`, `https`) | Protocol blocked |
| **Prompt Injection** | `"Ignore previous instructions"` | `UntrustedContentGuard.sanitize_untrusted_text` | Stripped & wrapped as passive data |
