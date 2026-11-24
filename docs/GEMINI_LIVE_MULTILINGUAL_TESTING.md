# GEMINI LIVE MULTILINGUAL UNDERSTANDING (TAMIL, ENGLISH, TANGLISH)

## 1. Natural Spoken Intent Recognition
Gemini Live receives audio directly, leveraging Gemini's foundational multimodal pre-training across Indian English, Tamil, and Tanglish.

### Supported Language Modes:
1. **Tamil:**
   - "நாளைக்கு காலை பத்து மணிக்கு மீட்டிங் வை." -> Correctly maps to `schedule_calendar_event` tool with `time="10:00 AM"`.
2. **English:**
   - "Zye, can you hear me?" -> Native conversational response confirming audio hearing.
   - "Schedule a project meeting tomorrow at 10 AM." -> Tool execution.
3. **Tanglish Code-Switching:**
   - "Zye, Chrome open pannu." -> Maps to `open_any_app` with `app_name="chrome"`.
   - "Work Gmail-la latest emails check pannu." -> Maps to `manage_emails` tool.
   - "Excel-la row 1 to 10 sum calculate pannu." -> Maps to `office_master` Excel tool.
   - "ChatGPT and Claude rendu peraiyum kettu compare pannu." -> Maps to `run_ai_council` tool.
   - "Previous meeting-a thirty minutes later move pannu." -> Contextual reference to previous meeting ID with 30-minute delta.

## 2. Follow-Up References & Context Continuity
- User: "Tomorrow 3 PM-ku Project Review meeting create pannu."
- User: "Adha 4 PM-ku move pannu."
- The pronoun "Adha" (Tamil: "that") is understood by Gemini Live as referring to the Project Review meeting created in the prior turn.
