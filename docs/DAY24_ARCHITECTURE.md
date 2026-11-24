# Zye AI — Day 24 Architecture: Universal Multi-Account Chrome Browser Intelligence

## 1. Architectural Overview

Day 24 establishes the **Browser Intelligence & Multi-Account Automation Subsystem** for Zye AI, bridging natural language desktop voice commands with live web automation powered by Google Chrome and Playwright.

```
VOICE COMMAND (Tamil / English / Tanglish)
                 │
                 ▼
       GEMINI AI MASTER BRAIN
                 │
                 ▼
     MASTER MCP ORCHESTRATOR
                 │
                 ▼
     browser_accounts_mcp.py (FastMCP "ZyeBrowserAccounts")
                 │
  ┌──────────────┼─────────────────────────┬────────────────────────┐
  ▼              ▼                         ▼                        ▼
Profile Manager  Session & Navigation     DOM Extraction Engine    Web App Adapters
- Discovery      - Playwright Singleton   - Text Cleaner           - Gmail (Read-Only)
- Local State    - Chrome Channel         - Prompt Injection Shield - Drive (Read-Only)
- Lock Manager   - URL Security Validator - Content Chunker        - YouTube
- Voice Selector - Tab Controller         - Filter (Urgent/Finance) - Search
```

---

## 2. Security & Zero Credential Exposure Policy

1. **Zero Credential Reading:**
   Zye never reads, extracts, or transmits stored passwords, authentication cookies, or cryptographic keys from Chrome or Windows Credential Manager.
2. **Metadata-Only Discovery:**
   Chrome profile discovery only parses non-sensitive JSON metadata from `%LOCALAPPDATA%\Google\Chrome\User Data\Local State` (`profile.info_cache`).
3. **Directory Isolation:**
   All persistent browser sessions operate inside isolated user data directories located under `%LOCALAPPDATA%\ZyeAI\browser_profiles\profile_<id>`, preventing database corruption of the user's active Chrome instance.
4. **Read-Only Default for Personal Clouds:**
   Gmail and Google Drive web interactions are strictly read-only. No email sending, deleting, or file alteration is executed without explicit user confirmation.
5. **Prompt Injection Neutralization:**
   All visible DOM text extracted from web pages is treated as untrusted data. A dedicated sanitizer (`VisibleTextCleaner`) strips known prompt injection signatures and instructs Gemini to treat web content strictly as context.

---

## 3. Subsystem Breakdown

- **`zye_browser/profile_manager.py`**: Manages profile persistence, directory verification, lock acquisition, and lifecycle.
- **`zye_browser/account_selector.py`**: Disambiguates user voice queries into specific profiles using Tamil, English, and Tanglish aliases.
- **`zye_browser/browser_session_manager.py`**: Manages persistent Playwright context (`channel="chrome"`, headless or visible).
- **`zye_browser/browser_navigation.py`**: Enforces URL schemes (`http`, `https`), blocks loopback/SSRF, and handles history.
- **`zye_browser/gmail_adapter.py`**: Reads email threads, subjects, senders, snippets, and bodies with 12,000 char limits.
- **`zye_browser/google_drive_adapter.py`**: Lists files/folders and searches Drive items.
- **`zye_browser/dom_content_extractor.py`**: Coordinates text extraction, filtering, and page snapshot formatting.
- **`zye_browser/web_click_engine.py`**: Safe DOM clicking with ambiguity checks and safeguards for irreversible actions.
- **`zye_browser/gemini_web_bridge.py`**: Connects browser content directly with Central Gemini Gateway for summarization and Q&A.
