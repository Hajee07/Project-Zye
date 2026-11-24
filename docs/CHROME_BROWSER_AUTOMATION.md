# ZYE AI — Google Chrome Browser Automation Engine

## 1. System Overview

The Chrome Browser Automation Engine (`browser_accounts_mcp.py` & `zye_browser/`) exposes 39 high-performance tools for web navigation, search, content extraction, and persistent authenticated web app control.

---

## 2. Key Capabilities

1. **Persistent Profile Management**:
   Connects to existing Chrome user profiles (Default, Profile 1, etc.) preserving user cookies, logins, and web application sessions.
2. **Web Navigation & Search**:
   - `browser_navigate(url)`: Navigates with DOM-ready and network-idle state detection.
   - `browser_search(query)`: Performs Google Search and returns top ranked organic results with title, link, and snippet.
3. **DOM Content Extraction & Readability**:
   - `browser_summarize_page()`: Filters navigation noise, sidebars, and ads, feeding clean markdown article content to the Gemini Master Brain.
   - `browser_click(selector)` & `browser_type(selector, text)`: Drives web forms and dynamic JavaScript interactions.
4. **Google Workspace Web Intelligence**:
   - `browser_gmail_search(query)`: Direct search inside authorized Gmail web application.
   - `browser_drive_search(query)`: Direct search inside authorized Google Drive web application.

---

## 3. Security & Anti-Prompt-Injection Defense

- **Untrusted Content Sandboxing**: All web page text is tagged inside `<untrusted_content>` tags before reaching Gemini Live to prevent indirect prompt injection.
- **Readability Cleaning**: Strips executable scripts, hidden CSS elements, iframe injections, and zero-width characters.
