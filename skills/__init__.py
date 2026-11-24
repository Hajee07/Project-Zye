"""
ZYE AI — Skills Package
========================

This package provides the modular skills architecture for Zye AI.
Each skill is a self-contained module that exposes typed tool interfaces
through the Model Context Protocol (MCP).

Future Skill Categories
-----------------------
- **Core AI**: Gemini and Ollama reasoning, model routing, structured output.
- **Windows Automation**: Desktop control, application management, system tasks.
- **Browser Automation**: Multi-profile Playwright sessions, web interaction.
- **Office Automation**: Word, Excel, PowerPoint, PDF document processing.
- **Voice**: Speech recognition, text-to-speech, wake-word detection.
- **Memory**: Semantic search, session history, project context retrieval.
- **Computer Vision**: Screen capture, object detection, camera analysis.
- **Data Intelligence**: Analytics, SQL queries, scientific computation.
- **Cybersecurity**: Network monitoring, threat detection, system hardening.
- **Engineering**: CAD generation, structural calculations, unit conversion.

Architecture Notes
------------------
- Skills are discovered and loaded dynamically at runtime.
- Each skill registers its tools with the MCP server.
- Skills declare their dependencies and required permissions.
- The skill lifecycle (load, enable, disable, unload) is managed centrally.

Day 01 Status
-------------
This package is initialized as an empty namespace. Skill implementations
will be added in subsequent development phases.
"""

__version__ = "0.1.0"
__all__: list[str] = []
