# Zye AI — Day 24: browser_accounts_mcp.py FastMCP Tool Reference

The `browser_accounts_mcp.py` server exports 39 FastMCP tools:

## 1. Profile Management Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_list_profiles` | None | List all registered persistent profiles and active locks. |
| `browser_discover_host_profiles` | None | Parse host Chrome Local State for installed accounts. |
| `browser_sync_host_profiles` | None | Auto-import host Chrome profiles into Zye registry. |
| `browser_create_profile` | `profile_id, display_name, email, account_type, aliases, tamil_aliases` | Register a new profile with designated aliases. |
| `browser_get_profile` | `profile_id` | Get metadata for specific profile. |
| `browser_update_profile` | `profile_id, display_name, email, aliases, tamil_aliases` | Update existing profile details. |
| `browser_delete_profile` | `profile_id, delete_files` | Delete profile and optionally remove directory. |
| `browser_resolve_account` | `query` | Disambiguate account name (Tamil/English/Tanglish). |

---

## 2. Browser Lifecycle & Sessions

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_launch_session` | `profile_id, headless` | Launch persistent Chrome session. |
| `browser_close_session` | None | Close running session and release profile locks. |
| `browser_restart_session` | `headless` | Restart active session. |
| `browser_switch_profile` | `account_query, headless` | Switch active session to another profile. |
| `browser_get_session_status` | None | Inspect running state, active profile, and tabs. |
| `browser_inspect_state` | None | Inspect readyState, DOM metrics, login gate detection. |

---

## 3. Tab Management

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_list_tabs` | None | List open tabs with index, URL, title. |
| `browser_new_tab` | `url` | Open new tab (optionally with URL). |
| `browser_switch_tab` | `tab_id` | Switch focused tab. |
| `browser_close_tab` | `tab_id` | Close specified tab. |

---

## 4. Navigation & Web Apps

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_navigate` | `url` | Navigate active page to sanitized URL. |
| `browser_open_app` | `app_name, query` | Shortcut for Gmail, Drive, YouTube, Calendar, Search. |
| `browser_go_back` | None | History back. |
| `browser_go_forward` | None | History forward. |
| `browser_reload` | None | Reload active tab. |
| `browser_search` | `query, app_override` | Execute search on active page search bar. |

---

## 5. Gmail & Google Drive Intelligence

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_gmail_list_threads` | `max_results, label` | Read-only extraction of Gmail threads. |
| `browser_gmail_read_thread` | `index` | Read detailed body of email thread. |
| `browser_gmail_search` | `query, max_results` | Search Gmail emails. |
| `browser_drive_list_items` | `max_results` | List Google Drive files and folders. |
| `browser_drive_search` | `query, max_results` | Search Google Drive files. |

---

## 6. DOM Extraction & Inspection

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_extract_page_snapshot` | `max_chars, filter_criteria` | Extract bounded, cleaned visible text snapshot. |
| `browser_inspect_dom` | None | Inspect headings, links, interactive elements, tables. |
| `browser_filter_content` | `criteria, keywords` | Filter page content (urgent, action items, invoices). |

---

## 7. Interaction & AI Synthesis

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `browser_click` | `selector_or_text, role, confirmed` | Safe click with ambiguity and high-stakes guards. |
| `browser_type` | `selector_or_text, text, press_enter` | Type text into input/textarea. |
| `browser_scroll` | `direction, amount` | Scroll page up or down. |
| `browser_press_key` | `key` | Press keyboard key (Enter, Escape, Tab). |
| `browser_summarize_page` | `language` | Gemini AI structured summary of active page. |
| `browser_ask_page` | `question` | Natural language Q&A about active page content. |
| `browser_check_health` | None | Run Day 24 diagnostic health check suite. |
