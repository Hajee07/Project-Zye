# Third-Party Notices & Open-Source Attribution

This document records the provenance, licenses, and third-party notices for open-source code and patterns referenced or adapted within the ZYE AI assistant project.

---

## 1. OpenJarvis

- **Project:** OpenJarvis (openjarvis-chat)
- **Source Archive:** `OpenJarvis-main.zip` (SHA-256: `245e3e30dbb44abfaefee1f517341ae65ce63f3fdcda39d5ef9ceba3fd9895e5`)
- **Reference Location:** `references/OpenJarvis-main/`
- **License:** Apache License 2.0
- **Copyright:** Copyright (c) 2024 OpenJarvis Contributors

### Apache License 2.0 Terms Summary
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

### Reused / Adapted Components
1. **Event Bus Patterns:** Adapted from `src/openjarvis/core/events.py` into `zye_core/event_bus.py`.
2. **Tool Loop Guard Patterns:** Adapted from `src/openjarvis/agents/loop_guard.py` into `zye_reliability/tool_loop_guard.py`.
3. **Model Circuit Breaker Patterns:** Adapted from `src/openjarvis/engine/multi.py` into `zye_intelligence/circuit_breaker.py`.
4. **Capability-Based Security:** Adapted from `src/openjarvis/security/capabilities.py` into `zye_security/capabilities.py`.
5. **Background Fact Extraction:** Adapted from `src/openjarvis/memory/service.py` into `zye_memory/memory_service.py`.
6. **Task Scheduler Architecture:** Adapted from `src/openjarvis/scheduler/scheduler.py` into `zye_scheduler/task_scheduler.py`.
7. **HUD Overlay Layout:** Adapted from `desktop/src-tauri/src/overlay.html` into `desktop/overlay.html`.
8. **WebSocket Bridge:** Adapted from `src/openjarvis/server/ws_bridge.py` into `zye_desktop/ws_bridge.py`.

---

## 2. Other Core Libraries

- **Google GenAI SDK:** Apache License 2.0 (Google LLC)
- **MCP (Model Context Protocol) Python SDK:** MIT License (Anthropic, PBC)
- **Pygame:** GNU LGPL v2.1 (Pete Shinners, Pygame Community)
- **PyYAML / TOMLlib:** MIT License / Python Software Foundation License
- **psutil:** BSD 3-Clause License (Giampaolo Rodola)
