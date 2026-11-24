# Zye AI — Day 24: Voice Command Catalog (Tamil / English / Tanglish)

## 1. Browser & Profile Commands

| Language | Voice Command Pattern | Mapped Action / Tool |
| :--- | :--- | :--- |
| English | "Launch browser with work profile" | `browser_launch_session(profile_id='work')` |
| Tamil | "வேலை கணக்கில் பிரவுசர் திற" | `browser_launch_session(profile_id='work')` |
| Tanglish | "Personal profile-la Chrome open pannu" | `browser_launch_session(profile_id='personal')` |
| English | "Switch to Zyren account" | `browser_switch_profile(account_query='zyren')` |
| Tamil | "பிரவுசரை மூடு" | `browser_close_session()` |
| Tanglish | "Browser close pannidu" | `browser_close_session()` |

---

## 2. Web App & Navigation Commands

| Language | Voice Command Pattern | Mapped Action / Tool |
| :--- | :--- | :--- |
| English | "Open Gmail" | `browser_open_app(app_name='gmail')` |
| Tamil | "ஜிமெயில் திற" | `browser_open_app(app_name='gmail')` |
| Tanglish | "Office mail open pannu" | Resolves office profile -> `browser_open_app(app_name='gmail')` |
| English | "Open Google Drive and search for Project Roadmap" | `browser_open_app(app_name='drive', query='Project Roadmap')` |
| Tamil | "கூகிள் டிரைவில் பட்ஜெட் தேடு" | `browser_drive_search(query='பட்ஜெட்')` |
| Tanglish | "YouTube-la Python tutorial search pannu" | `browser_open_app(app_name='youtube', query='Python tutorial')` |

---

## 3. DOM Intelligence & Summarization Commands

| Language | Voice Command Pattern | Mapped Action / Tool |
| :--- | :--- | :--- |
| English | "Summarize this page" | `browser_summarize_page(language='en')` |
| Tamil | "இந்த பக்கத்தை சுருக்கமாக சொல்" | `browser_summarize_page(language='ta')` |
| English | "What are the action items on this page?" | `browser_filter_content(criteria='action_items')` |
| Tanglish | "Indha page-la urgent matters irukka?" | `browser_filter_content(criteria='urgent')` |
| English | "What is the total invoice amount?" | `browser_filter_content(criteria='invoices')` |
