# ZYE AI — WhatsApp Desktop Automation Engine

## 1. Overview & Safety Interlock

The WhatsApp Desktop Automation subsystem (`windows_control_mcp.py` & `zye_windows/whatsapp_controller.py`) automates WhatsApp Desktop on Windows with strict safety gates separating message drafting from transmission.

---

## 2. Mandatory Two-Stage Safety Protocol

```
+-------------------------------------------------------------+
| Stage 1: DRAFTING (Safe, Non-Destructive)                   |
| Tool: compose_whatsapp_message(contact_name, message)       |
| - Searches contact in WhatsApp search box                   |
| - Opens target conversation                                 |
| - Types message text into message input box                 |
| - STOPS. Never presses Enter. Never clicks Send.            |
+-------------------------------------------------------------+
                              |
                              | Requires Explicit Voice / Tool Confirmation
                              v
+-------------------------------------------------------------+
| Stage 2: TRANSMISSION (Elevated, Irreversible)              |
| Tool: send_whatsapp_message(contact_name, message, confirmed)|
| - confirmed == False -> BLOCKED (CONFIRMATION_REQUIRED)     |
| - confirmed == True  -> Focuses chat, presses Enter         |
+-------------------------------------------------------------+
```

---

## 3. Tool Reference

- `search_whatsapp_contact(query)`: Focuses search bar, types contact name, queries matching contact items.
- `open_whatsapp_chat(contact_name)`: Selects contact from search results and focuses chat window.
- `compose_whatsapp_message(contact_name, message)`: Safely drafts message text into input box without sending.
- `send_whatsapp_message(contact_name, message, confirmed)`: Sends message only when confirmed.
- `start_whatsapp_voice_call(contact_name, confirmed)`: Initiates voice call only when confirmed.
- `start_whatsapp_video_call(contact_name, confirmed)`: Initiates video call only when confirmed.
- `end_whatsapp_call()`: Terminates active call immediately.
- `get_whatsapp_call_status()`: Queries call state (IDLE, DIALING, CONNECTED).
