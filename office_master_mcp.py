"""
Zye Microsoft Office Live COM Master MCP Server (Day 20).
Unified FastMCP server exposing high-level tools for Microsoft Word, Excel,
PowerPoint, and Outlook live COM automation, active document inspection,
allowlisted operations, native PDF exports, and verified Ribbon accelerators.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union

# FastMCP Server initialization
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except ImportError:
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

            async def list_tools(self) -> list[Any]:
                class _Stub:
                    def __init__(self, n: str):
                        self.name = n
                return [_Stub(n) for n in self._tools]


# Configure logging: write strictly to stderr so MCP stdio protocol is not corrupted
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("zye.office.mcp")

# Core Subsystem Imports
from zye_office import (
    OfficeAppType,
    ConnectionPolicy,
    STACOMWorker,
    get_shared_sta_worker,
    OfficeCOMRuntime,
    OfficeSessionManager,
    OfficeStateInspector,
    OfficeCapabilityRegistry,
    OfficeOperationRegistry,
    OfficeOperationExecutor,
    OfficeFileExporter,
    OfficeRibbonAccelerator,
    OfficeIntegrationHealth,
    OfficeAppRegistry,
    format_office_error,
)

# Instantiate Server and Subsystems
mcp = FastMCP("office-master-mcp")

# Shared lazy instances
_worker: Optional[STACOMWorker] = None
_runtime: Optional[OfficeCOMRuntime] = None
_session_mgr: Optional[OfficeSessionManager] = None
_inspector: Optional[OfficeStateInspector] = None
_cap_registry: Optional[OfficeCapabilityRegistry] = None
_op_registry: Optional[OfficeOperationRegistry] = None
_executor: Optional[OfficeOperationExecutor] = None
_exporter: Optional[OfficeFileExporter] = None
_accelerator: Optional[OfficeRibbonAccelerator] = None
_app_registry: Optional[OfficeAppRegistry] = None
_health: Optional[OfficeIntegrationHealth] = None
_word_facade: Any = None
_excel_facade: Any = None
_day23_facade: Any = None


def _init_subsystems():
    global _worker, _runtime, _session_mgr, _inspector, _cap_registry
    global _op_registry, _executor, _exporter, _accelerator, _app_registry, _health, _word_facade, _excel_facade, _day23_facade

    if _worker is None:
        _worker = get_shared_sta_worker()
        _runtime = OfficeCOMRuntime(worker=_worker)
        _session_mgr = OfficeSessionManager(com_runtime=_runtime)
        _inspector = OfficeStateInspector(com_runtime=_runtime)
        _cap_registry = OfficeCapabilityRegistry()
        _op_registry = OfficeOperationRegistry()
        _executor = OfficeOperationExecutor(
            runtime=_runtime,
            session_manager=_session_mgr,
            registry=_op_registry,
        )
        _exporter = OfficeFileExporter(
            runtime=_runtime,
            session_manager=_session_mgr,
        )
        _accelerator = OfficeRibbonAccelerator()
        _app_registry = OfficeAppRegistry()
        _health = OfficeIntegrationHealth(
            worker=_worker,
            registry=_app_registry,
            session_manager=_session_mgr,
            op_registry=_op_registry,
            cap_registry=_cap_registry,
        )
        from zye_office.integration.word_mcp_integration import WordMCPIntegrationFacade
        _word_facade = WordMCPIntegrationFacade()
        from zye_office.integration.excel_mcp_integration import ExcelMCPIntegrationFacade
        _excel_facade = ExcelMCPIntegrationFacade()
        from zye_office.integration.day23_mcp_integration import Day23MCPIntegrationFacade
        _day23_facade = Day23MCPIntegrationFacade()


# =============================================================================
# Tools: Application Connection & Session Management
# =============================================================================

@mcp.tool()
def office_connect(
    app_name: str,
    connection_policy: str = "ATTACH_EXISTING",
) -> Dict[str, Any]:
    """
    Connect to a live Microsoft Office application (word, excel, powerpoint, outlook).
    Policies: 'ATTACH_EXISTING' (default), 'LAUNCH_NEW', 'AUTO_ATTACH_OR_LAUNCH', 'INSPECT_ONLY'.
    """
    _init_subsystems()
    try:
        policy = ConnectionPolicy(connection_policy.upper())
    except ValueError:
        return format_office_error(
            "INVALID_POLICY",
            f"Invalid connection policy '{connection_policy}'. Choose from: ATTACH_EXISTING, LAUNCH_NEW, AUTO_ATTACH_OR_LAUNCH, INSPECT_ONLY.",
            app_name=app_name,
        )

    res = _session_mgr.create_office_session(app_name, policy=policy)
    return res


@mcp.tool()
def office_disconnect(
    session_id_or_app: str,
) -> Dict[str, Any]:
    """
    Disconnect an active Office session and release COM interfaces.
    Accepts session ID or application name ('word', 'excel', etc.).
    """
    _init_subsystems()
    sess = _session_mgr.get_session(session_id_or_app)
    if not sess:
        return {"status": "NOT_FOUND", "message": f"No active session found for '{session_id_or_app}'."}
    return _session_mgr.close_office_session(sess.session_id)


@mcp.tool()
def office_get_session_details(
    session_id_or_app: str,
) -> Dict[str, Any]:
    """
    Retrieve full session metadata, verifying live COM responsiveness.
    """
    _init_subsystems()
    sess = _session_mgr.get_session(session_id_or_app)
    if not sess:
        return {"status": "NOT_FOUND", "message": f"No active session found for '{session_id_or_app}'."}
    return _session_mgr.get_office_session_details(sess.session_id)


@mcp.tool()
def office_list_sessions() -> Dict[str, Any]:
    """
    List all tracked Microsoft Office sessions and their current connection states.
    """
    _init_subsystems()
    sessions = _session_mgr.list_sessions()
    return {
        "status": "SUCCESS",
        "count": len(sessions),
        "sessions": [s.model_dump() for s in sessions],
    }


# =============================================================================
# Tools: Live Document Inspection
# =============================================================================

@mcp.tool()
def office_inspect_document(
    app_name: str,
    max_preview_chars: int = 1500,
) -> Dict[str, Any]:
    """
    Inspect the currently active document, workbook, presentation, or Outlook folder.
    Word: page/word/char count, track changes state, text preview.
    Excel: workbook name, sheet names, active cell, used range, formula calculation mode.
    PowerPoint: presentation name, slide count, active slide, slide titles.
    Outlook: session status, explorer count, inspector count, active folder name.
    """
    _init_subsystems()
    norm = app_name.lower().strip()
    if norm == "word":
        res = _inspector.inspect_active_word_document(preview_limit=max_preview_chars)
        return res if isinstance(res, dict) else res.model_dump()
    elif norm == "excel":
        res = _inspector.inspect_active_excel_workbook()
        return res if isinstance(res, dict) else res.model_dump()
    elif norm == "powerpoint":
        res = _inspector.inspect_active_powerpoint_presentation()
        return res if isinstance(res, dict) else res.model_dump()
    elif norm == "outlook":
        res = _inspector.inspect_active_outlook_session()
        return res if isinstance(res, dict) else res.model_dump()
    else:
        return format_office_error(
            "UNSUPPORTED_APP",
            f"Unsupported application '{app_name}'. Supported: word, excel, powerpoint, outlook.",
            app_name=app_name,
        )


# =============================================================================
# Tools: Allowlisted Operation Execution
# =============================================================================

@mcp.tool()
def office_execute_operation(
    session_id_or_app: str,
    operation_id: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a typed allowlisted operation on a connected Office application.
    Supported operations include:
    - word.insert_text, word.insert_heading, word.apply_style, word.set_track_changes, word.save_document
    - excel.set_cell_value, excel.set_cell_formula, excel.format_range, excel.calculate, excel.save_workbook
    - powerpoint.get_slide_details, powerpoint.insert_slide, powerpoint.set_slide_title, powerpoint.save_presentation
    - outlook.create_draft, outlook.get_unread_count
    """
    _init_subsystems()
    sess = _session_mgr.get_session(session_id_or_app)
    if not sess:
        # Attempt auto-connection if app name provided
        try:
            conn_res = _session_mgr.create_office_session(session_id_or_app, policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn_res.get("status") != "SUCCESS":
                return conn_res
            sess = _session_mgr.get_session(session_id_or_app)
        except Exception as e:
            return format_office_error(e, context="auto_connect")

    if not sess:
        return {"status": "NOT_FOUND", "message": f"Could not find or establish session for '{session_id_or_app}'."}

    return _executor.execute(sess.session_id, operation_id, params or {})


# =============================================================================
# Tools: Native PDF Export
# =============================================================================

@mcp.tool()
def office_export_pdf(
    session_id_or_app: str,
    output_path: str,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Export the active Word document, Excel workbook, or PowerPoint presentation to PDF.
    Uses native COM ExportAsFixedFormat APIs and verifies output file non-zero size.
    """
    _init_subsystems()
    sess = _session_mgr.get_session(session_id_or_app)
    if not sess:
        # Attempt auto-connection
        try:
            conn_res = _session_mgr.create_office_session(session_id_or_app, policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn_res.get("status") != "SUCCESS":
                return conn_res
            sess = _session_mgr.get_session(session_id_or_app)
        except Exception as e:
            return format_office_error(e, context="auto_connect")

    if not sess:
        return {"status": "NOT_FOUND", "message": f"Could not find or establish session for '{session_id_or_app}'."}

    try:
        res = _exporter.export_active_to_pdf(sess.session_id, output_path, overwrite=overwrite)
        return res.model_dump()
    except Exception as e:
        return format_office_error(e, context="export_pdf", app_name=sess.app_name)


# =============================================================================
# Tools: Ribbon & Menu Key Accelerator
# =============================================================================

@mcp.tool()
def office_accelerate_ribbon(
    app_name: str,
    action_or_keys: str,
    auto_focus: bool = True,
) -> Dict[str, Any]:
    """
    Execute a Ribbon shortcut or keytip sequence on the target Office application.
    Enforces that the application window is active and in the foreground before sending keys.
    Predefined actions: 'save', 'bold', 'italic', 'underline', 'undo', 'redo', 'find',
    'print', 'new_item', 'new_slide', 'home_tab', 'insert_tab', 'review_tab', etc.
    """
    _init_subsystems()
    try:
        app_type = OfficeAppType(app_name.lower().strip())
    except ValueError:
        return format_office_error("INVALID_APP", f"Unknown Office application '{app_name}'.")

    try:
        return _accelerator.execute_accelerator(app_type, action_or_keys, auto_focus=auto_focus)
    except Exception as e:
        return format_office_error(e, context="accelerate_ribbon", app_name=app_name)


# =============================================================================
# Tools: Health, Discovery & Metadata Inspection
# =============================================================================

@mcp.tool()
def office_health_check() -> Dict[str, Any]:
    """
    Execute non-invasive diagnostic checks across all Office automation subsystems:
    COM runtime, STA worker thread, registry detection, session storage, and export directory.
    """
    _init_subsystems()
    return _health.run_health_check()


@mcp.tool()
def office_check_installation(
    app_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if Office applications are installed and COM-registered on the Windows host.
    If app_name is provided, inspects that specific app; otherwise checks all supported apps.
    """
    _init_subsystems()
    if app_name:
        info = _app_registry.check_office_installation(app_name)
        return info.model_dump()
    else:
        apps = _app_registry.get_registered_office_apps()
        return {
            "status": "SUCCESS",
            "installed_count": sum(1 for a in apps if a.is_installed),
            "applications": [a.model_dump() for a in apps],
        }


@mcp.tool()
def office_list_capabilities(
    app_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List supported automation capabilities and version requirements for Office applications.
    """
    _init_subsystems()
    if app_name:
        try:
            atype = OfficeAppType(app_name.lower().strip())
            return {
                "status": "SUCCESS",
                "app_name": app_name,
                "capabilities": _cap_registry.list_capabilities_for_app(atype),
            }
        except ValueError:
            return format_office_error("INVALID_APP", f"Unknown application '{app_name}'.")
    else:
        return {
            "status": "SUCCESS",
            "capabilities": _cap_registry.get_all_capabilities(),
        }


@mcp.tool()
def office_list_operations(
    app_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all allowlisted typed operations and parameter schemas.
    """
    _init_subsystems()
    atype = None
    if app_name:
        try:
            atype = OfficeAppType(app_name.lower().strip())
        except ValueError:
            return format_office_error("INVALID_APP", f"Unknown application '{app_name}'.")

    return {
        "status": "SUCCESS",
        "operations": _op_registry.list_operations(app_type=atype),
    }


# =============================================================================
# Day 21 Tools: Advanced Microsoft Word Automation
# =============================================================================

@mcp.tool()
def word_create_document() -> Dict[str, Any]:
    """Create a new blank document in Microsoft Word."""
    _init_subsystems()
    try:
        return _word_facade.create_document()
    except Exception as e:
        return format_office_error(e, context="word_create_document", app_name="word")


@mcp.tool()
def word_open_document(file_path: str, read_only: bool = False) -> Dict[str, Any]:
    """Open an existing Word document (.docx/.doc) by canonical path."""
    _init_subsystems()
    try:
        return _word_facade.open_document(file_path, read_only=read_only)
    except Exception as e:
        return format_office_error(e, context="word_open_document", app_name="word")


@mcp.tool()
def word_inspect_document(max_preview_chars: int = 1500) -> Dict[str, Any]:
    """Inspect active Word document metadata, page/word/table/section counts, and text preview."""
    _init_subsystems()
    try:
        return _word_facade.inspect_document(max_preview_chars=max_preview_chars)
    except Exception as e:
        return format_office_error(e, context="word_inspect_document", app_name="word")


@mcp.tool()
def word_get_document_metadata() -> Dict[str, Any]:
    """Get active Word document full statistics and saved/protection state."""
    _init_subsystems()
    try:
        return _word_facade.inspect_document()
    except Exception as e:
        return format_office_error(e, context="word_get_document_metadata", app_name="word")


@mcp.tool()
def word_save_document(path: Optional[str] = None) -> Dict[str, Any]:
    """Save the active Word document."""
    _init_subsystems()
    try:
        return _word_facade.save_document(path=path)
    except Exception as e:
        return format_office_error(e, context="word_save_document", app_name="word")


@mcp.tool()
def word_save_document_as(file_path: str) -> Dict[str, Any]:
    """Save active Word document under a new path."""
    _init_subsystems()
    try:
        return _word_facade.save_document_as(file_path)
    except Exception as e:
        return format_office_error(e, context="word_save_document_as", app_name="word")


@mcp.tool()
def word_close_document(save_changes: bool = False) -> Dict[str, Any]:
    """Close the active Word document."""
    _init_subsystems()
    try:
        return _word_facade.close_document(save_changes=save_changes)
    except Exception as e:
        return format_office_error(e, context="word_close_document", app_name="word")


@mcp.tool()
def word_insert_text(text: str, position: str = "end") -> Dict[str, Any]:
    """Insert Unicode text at 'end', 'start', or 'selection' in the active Word document."""
    _init_subsystems()
    try:
        return _word_facade.insert_text(text, location=position)
    except Exception as e:
        return format_office_error(e, context="word_insert_text", app_name="word")


@mcp.tool()
def word_replace_text(old_text: str, new_text: str, replace_all: bool = False, confirmed: bool = False) -> Dict[str, Any]:
    """Find and replace text in active Word document (bulk replace requires confirmed=True)."""
    _init_subsystems()
    try:
        return _word_facade.replace_text(old_text, new_text, replace_all=replace_all, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="word_replace_text", app_name="word")


@mcp.tool()
def word_delete_selected_text(confirmed: bool = False) -> Dict[str, Any]:
    """Delete selected text in active Word document (requires confirmed=True)."""
    _init_subsystems()
    try:
        return _word_facade.delete_selected_text(confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="word_delete_selected_text", app_name="word")


@mcp.tool()
def word_insert_page_break() -> Dict[str, Any]:
    """Insert a page break at current selection."""
    _init_subsystems()
    try:
        return _word_facade.insert_page_break()
    except Exception as e:
        return format_office_error(e, context="word_insert_page_break", app_name="word")


@mcp.tool()
def word_insert_section_break() -> Dict[str, Any]:
    """Insert a section break (Next Page) at current selection."""
    _init_subsystems()
    try:
        return _word_facade.insert_section_break()
    except Exception as e:
        return format_office_error(e, context="word_insert_section_break", app_name="word")


@mcp.tool()
def word_format_text(format_options: Dict[str, Any]) -> Dict[str, Any]:
    """Format font, size, bold, italic, underline, or color of active selection."""
    _init_subsystems()
    try:
        return _word_facade.format_text(format_options)
    except Exception as e:
        return format_office_error(e, context="word_format_text", app_name="word")


@mcp.tool()
def word_format_paragraph(format_options: Dict[str, Any]) -> Dict[str, Any]:
    """Format paragraph alignment (left/center/right/justify), line spacing, or indentation."""
    _init_subsystems()
    try:
        return _word_facade.format_text(format_options)
    except Exception as e:
        return format_office_error(e, context="word_format_paragraph", app_name="word")


@mcp.tool()
def word_apply_style(style_name: str) -> Dict[str, Any]:
    """Apply a built-in or custom Word style (e.g. 'Heading 1', 'Title', 'Normal')."""
    _init_subsystems()
    try:
        return _word_facade.apply_style(style_name)
    except Exception as e:
        return format_office_error(e, context="word_apply_style", app_name="word")


@mcp.tool()
def word_create_custom_style(style_config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a corporate style preset (e.g. 'BUSINESS_REPORT', 'ACADEMIC_REPORT', 'EXECUTIVE_SUMMARY')."""
    _init_subsystems()
    try:
        preset_name = style_config.get("preset_name", "BUSINESS_REPORT")
        return _word_facade.apply_preset(preset_name)
    except Exception as e:
        return format_office_error(e, context="word_create_custom_style", app_name="word")


@mcp.tool()
def word_create_table(rows: int, columns: int, autofit: str = "window", data: Optional[List[List[Any]]] = None, style_preset: Optional[str] = None) -> Dict[str, Any]:
    """Create a table in active Word document with optional matrix population and preset style."""
    _init_subsystems()
    try:
        return _word_facade.create_table(rows, columns, autofit=autofit, data=data, style_preset=style_preset)
    except Exception as e:
        return format_office_error(e, context="word_create_table", app_name="word")


@mcp.tool()
def word_populate_table(table_id: int, data: List[List[Any]]) -> Dict[str, Any]:
    """Bulk populate an existing Word table with a 2D matrix of values."""
    _init_subsystems()
    try:
        return _word_facade.populate_table(table_id, data)
    except Exception as e:
        return format_office_error(e, context="word_populate_table", app_name="word")


@mcp.tool()
def word_format_table(table_id: int, style_name: str) -> Dict[str, Any]:
    """Apply a style preset ('PROFESSIONAL_BLUE', 'PROFESSIONAL_GRAY', 'MINIMAL') to a table."""
    _init_subsystems()
    try:
        return _word_facade.table_engine.create_word_table(1, 1, style_preset=style_name)
    except Exception as e:
        return format_office_error(e, context="word_format_table", app_name="word")


@mcp.tool()
def word_add_table_row(table_id: int) -> Dict[str, Any]:
    """Append a new row to an existing Word table."""
    _init_subsystems()
    try:
        return _word_facade.add_table_row(table_id)
    except Exception as e:
        return format_office_error(e, context="word_add_table_row", app_name="word")


@mcp.tool()
def word_delete_table_row(table_id: int, row: int) -> Dict[str, Any]:
    """Delete a row from a Word table by 1-based index."""
    _init_subsystems()
    try:
        return _word_facade.delete_table_row(table_id, row)
    except Exception as e:
        return format_office_error(e, context="word_delete_table_row", app_name="word")


@mcp.tool()
def word_set_header(text: str, section_index: int = 1, alignment: str = "center") -> Dict[str, Any]:
    """Set text in the primary header of a Word document section."""
    _init_subsystems()
    try:
        return _word_facade.set_header(text, section_index=section_index, alignment=alignment)
    except Exception as e:
        return format_office_error(e, context="word_set_header", app_name="word")


@mcp.tool()
def word_set_footer(text: str, section_index: int = 1, alignment: str = "center") -> Dict[str, Any]:
    """Set text in the primary footer of a Word document section."""
    _init_subsystems()
    try:
        return _word_facade.set_footer(text, section_index=section_index, alignment=alignment)
    except Exception as e:
        return format_office_error(e, context="word_set_footer", app_name="word")


@mcp.tool()
def word_insert_page_numbers(position: str = "footer_right", section_index: int = 1) -> Dict[str, Any]:
    """Insert dynamic page numbering into footer or header."""
    _init_subsystems()
    try:
        return _word_facade.insert_page_numbers(position=position, section_index=section_index)
    except Exception as e:
        return format_office_error(e, context="word_insert_page_numbers", app_name="word")


@mcp.tool()
def word_set_first_page_header(text: str, section_index: int = 1) -> Dict[str, Any]:
    """Enable DifferentFirstPageHeaderFooter and assign first page header text."""
    _init_subsystems()
    try:
        return _word_facade.set_first_page_header(text, section_index=section_index)
    except Exception as e:
        return format_office_error(e, context="word_set_first_page_header", app_name="word")


@mcp.tool()
def word_set_page_orientation(orientation: str, section_index: Optional[int] = None) -> Dict[str, Any]:
    """Set page orientation ('PORTRAIT' or 'LANDSCAPE') for a section or entire document."""
    _init_subsystems()
    try:
        return _word_facade.set_page_orientation(orientation, section_index=section_index)
    except Exception as e:
        return format_office_error(e, context="word_set_page_orientation", app_name="word")


@mcp.tool()
def word_set_page_margins(margins: Dict[str, float], section_index: Optional[int] = None) -> Dict[str, Any]:
    """Set page margins (top, bottom, left, right in points) for a section or entire document."""
    _init_subsystems()
    try:
        return _word_facade.set_page_margins(
            top=margins.get("top"),
            bottom=margins.get("bottom"),
            left=margins.get("left"),
            right=margins.get("right"),
            section_index=section_index,
        )
    except Exception as e:
        return format_office_error(e, context="word_set_page_margins", app_name="word")


@mcp.tool()
def word_set_paper_size(size: str, section_index: Optional[int] = None) -> Dict[str, Any]:
    """Set paper size ('A4', 'LETTER', 'LEGAL', 'A3') for a section or entire document."""
    _init_subsystems()
    try:
        return _word_facade.set_paper_size(size, section_index=section_index)
    except Exception as e:
        return format_office_error(e, context="word_set_paper_size", app_name="word")


@mcp.tool()
def word_create_bullet_list(items: List[str]) -> Dict[str, Any]:
    """Insert a bulleted list of items into active Word document."""
    _init_subsystems()
    try:
        return _word_facade.create_bullet_list(items)
    except Exception as e:
        return format_office_error(e, context="word_create_bullet_list", app_name="word")


@mcp.tool()
def word_create_numbered_list(items: List[str]) -> Dict[str, Any]:
    """Insert a numbered list of items into active Word document."""
    _init_subsystems()
    try:
        return _word_facade.create_numbered_list(items)
    except Exception as e:
        return format_office_error(e, context="word_create_numbered_list", app_name="word")


@mcp.tool()
def word_insert_toc(levels: int = 3) -> Dict[str, Any]:
    """Generate an automated Table of Contents based on document heading styles."""
    _init_subsystems()
    try:
        return _word_facade.insert_toc(upper_level=1, lower_level=levels)
    except Exception as e:
        return format_office_error(e, context="word_insert_toc", app_name="word")


@mcp.tool()
def word_update_toc() -> Dict[str, Any]:
    """Refresh all Table of Contents fields in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.update_toc()
    except Exception as e:
        return format_office_error(e, context="word_update_toc", app_name="word")


@mcp.tool()
def word_insert_hyperlink(display_text: str, url: str) -> Dict[str, Any]:
    """Insert a verified hyperlink (http/https/mailto) into active Word document."""
    _init_subsystems()
    try:
        return _word_facade.insert_hyperlink(display_text, url)
    except Exception as e:
        return format_office_error(e, context="word_insert_hyperlink", app_name="word")


@mcp.tool()
def word_create_bookmark(name: str) -> Dict[str, Any]:
    """Create a named bookmark at current selection in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.create_bookmark(name)
    except Exception as e:
        return format_office_error(e, context="word_create_bookmark", app_name="word")


@mcp.tool()
def word_get_track_changes_status() -> Dict[str, Any]:
    """Query whether Track Changes is actively enabled and count pending revisions."""
    _init_subsystems()
    try:
        return _word_facade.get_track_changes_status()
    except Exception as e:
        return format_office_error(e, context="word_get_track_changes_status", app_name="word")


@mcp.tool()
def word_set_track_changes(enabled: bool) -> Dict[str, Any]:
    """Enable or disable Track Changes recording in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.set_track_changes(enabled)
    except Exception as e:
        return format_office_error(e, context="word_set_track_changes", app_name="word")


@mcp.tool()
def word_get_revisions() -> Dict[str, Any]:
    """List pending revisions in active document with authors and change previews."""
    _init_subsystems()
    try:
        return _word_facade.get_revisions()
    except Exception as e:
        return format_office_error(e, context="word_get_revisions", app_name="word")


@mcp.tool()
def word_accept_revision(revision_id: int) -> Dict[str, Any]:
    """Accept a specific revision in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.accept_revision(revision_id)
    except Exception as e:
        return format_office_error(e, context="word_accept_revision", app_name="word")


@mcp.tool()
def word_reject_revision(revision_id: int) -> Dict[str, Any]:
    """Reject a specific revision in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.reject_revision(revision_id)
    except Exception as e:
        return format_office_error(e, context="word_reject_revision", app_name="word")


@mcp.tool()
def word_accept_all_revisions(confirmed: bool = False) -> Dict[str, Any]:
    """Accept ALL revisions in document (HIGH_RISK: requires confirmed=True)."""
    _init_subsystems()
    try:
        return _word_facade.accept_all_revisions(confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="word_accept_all_revisions", app_name="word")


@mcp.tool()
def word_reject_all_revisions(confirmed: bool = False) -> Dict[str, Any]:
    """Reject ALL revisions in document (HIGH_RISK: requires confirmed=True)."""
    _init_subsystems()
    try:
        return _word_facade.reject_all_revisions(confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="word_reject_all_revisions", app_name="word")


@mcp.tool()
def word_add_comment(text: str) -> Dict[str, Any]:
    """Attach an annotation comment to current selection in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.add_comment(text)
    except Exception as e:
        return format_office_error(e, context="word_add_comment", app_name="word")


@mcp.tool()
def word_get_comments() -> Dict[str, Any]:
    """List all comments attached to active Word document."""
    _init_subsystems()
    try:
        return _word_facade.get_comments()
    except Exception as e:
        return format_office_error(e, context="word_get_comments", app_name="word")


@mcp.tool()
def word_resolve_comment(comment_id: int) -> Dict[str, Any]:
    """Mark a comment as resolved in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.resolve_comment(comment_id)
    except Exception as e:
        return format_office_error(e, context="word_resolve_comment", app_name="word")


@mcp.tool()
def word_inspect_mail_merge() -> Dict[str, Any]:
    """Inspect mail merge configuration and field codes in active Word document."""
    _init_subsystems()
    try:
        return _word_facade.inspect_mail_merge()
    except Exception as e:
        return format_office_error(e, context="word_inspect_mail_merge", app_name="word")


@mcp.tool()
def word_connect_merge_source(source_path: str) -> Dict[str, Any]:
    """Connect a validated CSV or Excel spreadsheet as Word's Mail Merge data source."""
    _init_subsystems()
    try:
        return _word_facade.connect_merge_source(source_path)
    except Exception as e:
        return format_office_error(e, context="word_connect_merge_source", app_name="word")


@mcp.tool()
def word_execute_mail_merge(confirmed: bool = False) -> Dict[str, Any]:
    """Execute Mail Merge into a new document (HIGH_RISK: requires confirmed=True)."""
    _init_subsystems()
    try:
        return _word_facade.execute_mail_merge(confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="word_execute_mail_merge", app_name="word")


@mcp.tool()
def word_get_statistics() -> Dict[str, Any]:
    """Get exact word, page, character, paragraph, and table counts."""
    _init_subsystems()
    try:
        return _word_facade.get_statistics()
    except Exception as e:
        return format_office_error(e, context="word_get_statistics", app_name="word")


@mcp.tool()
def word_set_document_properties(properties: Dict[str, str]) -> Dict[str, Any]:
    """Update document properties (title, author, subject, keywords, company)."""
    _init_subsystems()
    try:
        return _word_facade.set_document_properties(properties)
    except Exception as e:
        return format_office_error(e, context="word_set_document_properties", app_name="word")


@mcp.tool()
def word_inspect_accessibility() -> Dict[str, Any]:
    """Inspect active Word document for digital accessibility compliance."""
    _init_subsystems()
    try:
        return _word_facade.inspect_accessibility()
    except Exception as e:
        return format_office_error(e, context="word_inspect_accessibility", app_name="word")


@mcp.tool()
def word_generate_accessibility_report() -> Dict[str, Any]:
    """Generate accessibility compliance report with recommendations."""
    _init_subsystems()
    try:
        return _word_facade.inspect_accessibility()
    except Exception as e:
        return format_office_error(e, context="word_generate_accessibility_report", app_name="word")


@mcp.tool()
def word_export_pdf_advanced(output_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Export active Word document to PDF using native COM ExportAsFixedFormat."""
    _init_subsystems()
    try:
        return _word_facade.export_pdf_advanced(output_path, overwrite=overwrite)
    except Exception as e:
        return format_office_error(e, context="word_export_pdf_advanced", app_name="word")


# =============================================================================
# Day 22 Tools: Advanced Microsoft Excel Automation
# =============================================================================

@mcp.tool()
def excel_create_workbook() -> Dict[str, Any]:
    """Create a fresh blank Microsoft Excel workbook."""
    _init_subsystems()
    try:
        return _excel_facade.create_workbook()
    except Exception as e:
        return format_office_error(e, context="excel_create_workbook", app_name="excel")


@mcp.tool()
def excel_open_workbook(file_path: str, read_only: bool = False) -> Dict[str, Any]:
    """Open an existing Microsoft Excel workbook."""
    _init_subsystems()
    try:
        return _excel_facade.open_workbook(file_path, read_only=read_only)
    except Exception as e:
        return format_office_error(e, context="excel_open_workbook", app_name="excel")


@mcp.tool()
def excel_inspect_workbook() -> Dict[str, Any]:
    """Inspect the active Microsoft Excel workbook, sheets, and active cell."""
    _init_subsystems()
    try:
        return _excel_facade.inspect_workbook()
    except Exception as e:
        return format_office_error(e, context="excel_inspect_workbook", app_name="excel")


@mcp.tool()
def excel_save_workbook() -> Dict[str, Any]:
    """Save the active Microsoft Excel workbook."""
    _init_subsystems()
    try:
        return _excel_facade.save_workbook()
    except Exception as e:
        return format_office_error(e, context="excel_save_workbook", app_name="excel")


@mcp.tool()
def excel_save_workbook_as(file_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Save the active Excel workbook to a new destination file."""
    _init_subsystems()
    try:
        return _excel_facade.save_workbook_as(file_path, overwrite=overwrite)
    except Exception as e:
        return format_office_error(e, context="excel_save_workbook_as", app_name="excel")


@mcp.tool()
def excel_get_workbook_metadata() -> Dict[str, Any]:
    """Retrieve structured metadata and properties of the active Excel workbook."""
    _init_subsystems()
    try:
        return _excel_facade.get_workbook_metadata()
    except Exception as e:
        return format_office_error(e, context="excel_get_workbook_metadata", app_name="excel")


@mcp.tool()
def excel_get_worksheets() -> List[Dict[str, Any]]:
    """List all worksheets in the active Excel workbook with metadata."""
    _init_subsystems()
    try:
        return _excel_facade.get_worksheets()
    except Exception as e:
        return [format_office_error(e, context="excel_get_worksheets", app_name="excel")]


@mcp.tool()
def excel_create_worksheet(name: Optional[str] = None) -> Dict[str, Any]:
    """Create a new worksheet in the active workbook."""
    _init_subsystems()
    try:
        return _excel_facade.create_worksheet(name=name)
    except Exception as e:
        return format_office_error(e, context="excel_create_worksheet", app_name="excel")


@mcp.tool()
def excel_rename_worksheet(old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename an existing worksheet in the active workbook."""
    _init_subsystems()
    try:
        return _excel_facade.rename_worksheet(old_name, new_name)
    except Exception as e:
        return format_office_error(e, context="excel_rename_worksheet", app_name="excel")


@mcp.tool()
def excel_delete_worksheet(name: str, confirmed: bool = False) -> Dict[str, Any]:
    """Delete a worksheet from the active workbook (requires confirmed=True)."""
    _init_subsystems()
    try:
        return _excel_facade.delete_worksheet(name, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="excel_delete_worksheet", app_name="excel")


@mcp.tool()
def excel_duplicate_worksheet(name: str, new_name: Optional[str] = None) -> Dict[str, Any]:
    """Duplicate an existing worksheet in the active workbook."""
    _init_subsystems()
    try:
        return _excel_facade.duplicate_worksheet(name, new_name=new_name)
    except Exception as e:
        return format_office_error(e, context="excel_duplicate_worksheet", app_name="excel")


@mcp.tool()
def excel_get_cell_value(cell: str) -> Dict[str, Any]:
    """Read the evaluated value of a single cell (e.g. 'A1')."""
    _init_subsystems()
    try:
        return _excel_facade.get_cell_value(cell)
    except Exception as e:
        return format_office_error(e, context="excel_get_cell_value", app_name="excel")


@mcp.tool()
def excel_set_cell_value(cell: str, value: Any) -> Dict[str, Any]:
    """Write a value into a single cell (e.g. 'C21', 1500)."""
    _init_subsystems()
    try:
        return _excel_facade.set_cell_value(cell, value)
    except Exception as e:
        return format_office_error(e, context="excel_set_cell_value", app_name="excel")


@mcp.tool()
def excel_get_cell_formula(cell: str) -> Dict[str, Any]:
    """Read the formula string of a single cell."""
    _init_subsystems()
    try:
        return _excel_facade.get_cell_formula(cell)
    except Exception as e:
        return format_office_error(e, context="excel_get_cell_formula", app_name="excel")


@mcp.tool()
def excel_set_cell_formula(cell: str, formula: str) -> Dict[str, Any]:
    """Write a formula into a single cell (e.g. 'C21', '=SUM(C2:C20)')."""
    _init_subsystems()
    try:
        return _excel_facade.set_cell_formula(cell, formula)
    except Exception as e:
        return format_office_error(e, context="excel_set_cell_formula", app_name="excel")


@mcp.tool()
def excel_get_range_values(range_address: str) -> Dict[str, Any]:
    """Read a 2D matrix of values from a range (e.g. 'A1:D20') in bulk."""
    _init_subsystems()
    try:
        return _excel_facade.get_range_values(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_get_range_values", app_name="excel")


@mcp.tool()
def excel_set_range_values(range_address: str, data: List[List[Any]]) -> Dict[str, Any]:
    """Write a 2D matrix of values into a range in a single high-performance COM call."""
    _init_subsystems()
    try:
        return _excel_facade.set_range_values(range_address, data)
    except Exception as e:
        return format_office_error(e, context="excel_set_range_values", app_name="excel")


@mcp.tool()
def excel_fill_formula_down(range_address: str, formula: Optional[str] = None) -> Dict[str, Any]:
    """Autofill a formula downwards across a range."""
    _init_subsystems()
    try:
        return _excel_facade.fill_formula_down(range_address, formula=formula)
    except Exception as e:
        return format_office_error(e, context="excel_fill_formula_down", app_name="excel")


@mcp.tool()
def excel_audit_formulas(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Audit formulas in a range or worksheet to detect errors like #REF! or #DIV/0!."""
    _init_subsystems()
    try:
        return _excel_facade.audit_formulas(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_audit_formulas", app_name="excel")


@mcp.tool()
def excel_find_formula_errors(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Find all cells evaluating to Excel formula errors with suggested remediations."""
    _init_subsystems()
    try:
        return _excel_facade.find_formula_errors(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_find_formula_errors", app_name="excel")


@mcp.tool()
def excel_format_range(range_address: str, format_options: Dict[str, Any]) -> Dict[str, Any]:
    """Apply typography, fills, alignments, borders, and number formats to a range."""
    _init_subsystems()
    try:
        return _excel_facade.format_range(range_address, format_options)
    except Exception as e:
        return format_office_error(e, context="excel_format_range", app_name="excel")


@mcp.tool()
def excel_autofit_columns(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Automatically adjust column widths to fit content."""
    _init_subsystems()
    try:
        return _excel_facade.autofit_columns(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_autofit_columns", app_name="excel")


@mcp.tool()
def excel_set_number_format(range_address: str, number_format: str) -> Dict[str, Any]:
    """Set custom number formatting string (e.g. '$#,##0.00', '0.0%')."""
    _init_subsystems()
    try:
        return _excel_facade.set_number_format(range_address, number_format)
    except Exception as e:
        return format_office_error(e, context="excel_set_number_format", app_name="excel")


@mcp.tool()
def excel_add_conditional_formatting(range_address: str, rule_config: Dict[str, Any]) -> Dict[str, Any]:
    """Add native Excel conditional formatting rule (cell_value, formula, duplicate, color_scale, data_bar)."""
    _init_subsystems()
    try:
        return _excel_facade.add_conditional_formatting(range_address, rule_config)
    except Exception as e:
        return format_office_error(e, context="excel_add_conditional_formatting", app_name="excel")


@mcp.tool()
def excel_get_conditional_formatting(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Inspect active conditional formatting rules in a range."""
    _init_subsystems()
    try:
        return _excel_facade.get_conditional_formatting(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_get_conditional_formatting", app_name="excel")


@mcp.tool()
def excel_remove_conditional_formatting(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Remove conditional formatting rules from a range or active worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.remove_conditional_formatting(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_remove_conditional_formatting", app_name="excel")


@mcp.tool()
def excel_create_chart(chart_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a native embedded Excel chart (column, bar, line, pie, 3D, combo)."""
    _init_subsystems()
    try:
        return _excel_facade.create_chart(chart_config)
    except Exception as e:
        return format_office_error(e, context="excel_create_chart", app_name="excel")


@mcp.tool()
def excel_update_chart(chart_id: int, chart_config: Dict[str, Any]) -> Dict[str, Any]:
    """Update title or visual properties of an existing chart."""
    _init_subsystems()
    try:
        # Re-create or apply update
        return _excel_facade.create_chart(chart_config)
    except Exception as e:
        return format_office_error(e, context="excel_update_chart", app_name="excel")


@mcp.tool()
def excel_get_charts() -> Dict[str, Any]:
    """List all charts in the active worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.get_charts()
    except Exception as e:
        return format_office_error(e, context="excel_get_charts", app_name="excel")


@mcp.tool()
def excel_delete_chart(chart_id: Union[int, str]) -> Dict[str, Any]:
    """Delete a chart from the active worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.delete_chart(chart_id)
    except Exception as e:
        return format_office_error(e, context="excel_delete_chart", app_name="excel")


@mcp.tool()
def excel_create_pivot_table(pivot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a native Excel Pivot Table with custom row, column, filter, and value aggregations."""
    _init_subsystems()
    try:
        return _excel_facade.create_pivot_table(pivot_config)
    except Exception as e:
        return format_office_error(e, context="excel_create_pivot_table", app_name="excel")


@mcp.tool()
def excel_get_pivot_tables() -> Dict[str, Any]:
    """List all Pivot Tables in the active worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.get_pivot_tables()
    except Exception as e:
        return format_office_error(e, context="excel_get_pivot_tables", app_name="excel")


@mcp.tool()
def excel_refresh_pivot_table(pivot_id: Optional[str] = None) -> Dict[str, Any]:
    """Refresh a specific Pivot Table or all Pivot Tables in the worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.refresh_pivot_table(pivot_id)
    except Exception as e:
        return format_office_error(e, context="excel_refresh_pivot_table", app_name="excel")


@mcp.tool()
def excel_create_pivot_chart(pivot_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Pivot Table and attach a linked native Pivot Chart."""
    _init_subsystems()
    try:
        return _excel_facade.create_pivot_chart(pivot_config)
    except Exception as e:
        return format_office_error(e, context="excel_create_pivot_chart", app_name="excel")


@mcp.tool()
def excel_create_table(range_address: str, table_name: Optional[str] = None) -> Dict[str, Any]:
    """Convert a range into an Excel structured Table (ListObject)."""
    _init_subsystems()
    try:
        return _excel_facade.create_table(range_address, table_name=table_name)
    except Exception as e:
        return format_office_error(e, context="excel_create_table", app_name="excel")


@mcp.tool()
def excel_get_tables() -> Dict[str, Any]:
    """List all structured tables in the active worksheet."""
    _init_subsystems()
    try:
        return _excel_facade.get_tables()
    except Exception as e:
        return format_office_error(e, context="excel_get_tables", app_name="excel")


@mcp.tool()
def excel_format_table(table_name: str, style_name: str) -> Dict[str, Any]:
    """Apply a built-in table style to an Excel structured Table."""
    _init_subsystems()
    try:
        return _excel_facade.format_table(table_name, style_name)
    except Exception as e:
        return format_office_error(e, context="excel_format_table", app_name="excel")


@mcp.tool()
def excel_add_dropdown_validation(range_address: str, values: List[str]) -> Dict[str, Any]:
    """Add a dropdown list data validation constraint to a range."""
    _init_subsystems()
    try:
        return _excel_facade.add_dropdown_validation(range_address, values)
    except Exception as e:
        return format_office_error(e, context="excel_add_dropdown_validation", app_name="excel")


@mcp.tool()
def excel_add_data_validation(range_address: str, validation_config: Dict[str, Any]) -> Dict[str, Any]:
    """Add data validation constraint (numeric, date, text length, custom) to a range."""
    _init_subsystems()
    try:
        return _excel_facade.add_data_validation(range_address, validation_config)
    except Exception as e:
        return format_office_error(e, context="excel_add_data_validation", app_name="excel")


@mcp.tool()
def excel_inspect_data_validation(range_address: str) -> Dict[str, Any]:
    """Inspect data validation rules on a range or cell."""
    _init_subsystems()
    try:
        return _excel_facade.inspect_data_validation(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_inspect_data_validation", app_name="excel")


@mcp.tool()
def excel_sort_range(range_address: str, sort_config: Dict[str, Any]) -> Dict[str, Any]:
    """Sort a range by column index or letter ascending/descending."""
    _init_subsystems()
    try:
        return _excel_facade.sort_range(range_address, sort_config)
    except Exception as e:
        return format_office_error(e, context="excel_sort_range", app_name="excel")


@mcp.tool()
def excel_apply_filter(range_address: str, filter_config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply an AutoFilter criteria to a range or enable AutoFilter."""
    _init_subsystems()
    try:
        return _excel_facade.apply_filter(range_address, filter_config)
    except Exception as e:
        return format_office_error(e, context="excel_apply_filter", app_name="excel")


@mcp.tool()
def excel_clear_filters() -> Dict[str, Any]:
    """Clear all active AutoFilter criteria to display all rows."""
    _init_subsystems()
    try:
        return _excel_facade.clear_filters()
    except Exception as e:
        return format_office_error(e, context="excel_clear_filters", app_name="excel")


@mcp.tool()
def excel_remove_duplicates(
    range_address: Optional[str] = None,
    columns: Optional[List[int]] = None,
    confirmed: bool = False,
) -> Dict[str, Any]:
    """Remove duplicate rows from a dataset (requires confirmed=True)."""
    _init_subsystems()
    try:
        return _excel_facade.remove_duplicates(range_address, columns=columns, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="excel_remove_duplicates", app_name="excel")


@mcp.tool()
def excel_find_missing_values(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Audit dataset to find empty cells and completeness score."""
    _init_subsystems()
    try:
        return _excel_facade.generate_data_quality_report(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_find_missing_values", app_name="excel")


@mcp.tool()
def excel_generate_data_quality_report(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Generate comprehensive data quality and completeness audit report."""
    _init_subsystems()
    try:
        return _excel_facade.generate_data_quality_report(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_generate_data_quality_report", app_name="excel")


@mcp.tool()
def excel_create_named_range(name: str, range_address: str) -> Dict[str, Any]:
    """Create a workbook-level defined named range."""
    _init_subsystems()
    try:
        return _excel_facade.create_named_range(name, range_address)
    except Exception as e:
        return format_office_error(e, context="excel_create_named_range", app_name="excel")


@mcp.tool()
def excel_get_named_ranges() -> Dict[str, Any]:
    """List all defined named ranges in the active workbook."""
    _init_subsystems()
    try:
        return _excel_facade.get_named_ranges()
    except Exception as e:
        return format_office_error(e, context="excel_get_named_ranges", app_name="excel")


@mcp.tool()
def excel_delete_named_range(name: str) -> Dict[str, Any]:
    """Delete a defined named range."""
    _init_subsystems()
    try:
        return _excel_facade.delete_named_range(name)
    except Exception as e:
        return format_office_error(e, context="excel_delete_named_range", app_name="excel")


@mcp.tool()
def excel_analyze_dataset(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Provide bounded summary profiling and statistical shape of dataset."""
    _init_subsystems()
    try:
        return _excel_facade.analyze_dataset(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_analyze_dataset", app_name="excel")


@mcp.tool()
def excel_summarize_dataset(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve tabular column headers and preview sample rows."""
    _init_subsystems()
    try:
        return _excel_facade.summarize_dataset(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_summarize_dataset", app_name="excel")


@mcp.tool()
def excel_generate_data_insights(range_address: Optional[str] = None) -> Dict[str, Any]:
    """Generate recommendations for charts, formulas, and pivot summaries."""
    _init_subsystems()
    try:
        return _excel_facade.generate_data_insights(range_address)
    except Exception as e:
        return format_office_error(e, context="excel_generate_data_insights", app_name="excel")


@mcp.tool()
def excel_generate_report(report_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a multi-section executive report with KPIs, tables, and charts."""
    _init_subsystems()
    try:
        return _excel_facade.generate_report(report_config)
    except Exception as e:
        return format_office_error(e, context="excel_generate_report", app_name="excel")


@mcp.tool()
def excel_generate_kpi_dashboard(report_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a structured KPI executive dashboard sheet."""
    _init_subsystems()
    try:
        return _excel_facade.generate_kpi_dashboard(report_config)
    except Exception as e:
        return format_office_error(e, context="excel_generate_kpi_dashboard", app_name="excel")


@mcp.tool()
def excel_export_pdf(output_path: str, export_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Export active Excel worksheet or workbook to high-fidelity PDF."""
    _init_subsystems()
    try:
        return _excel_facade.export_pdf(output_path, export_config=export_config)
    except Exception as e:
        return format_office_error(e, context="excel_export_pdf", app_name="excel")


# =============================================================================
# Day 23 Tools: PowerPoint Automation Suite
# =============================================================================

@mcp.tool()
def powerpoint_inspect_live() -> Dict[str, Any]:
    """Inspect the live Microsoft PowerPoint instance, active presentation, and slide count."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_inspect_live()
    except Exception as e:
        return format_office_error(e, context="powerpoint_inspect_live", app_name="powerpoint")


@mcp.tool()
def powerpoint_create_presentation() -> Dict[str, Any]:
    """Create a new blank Microsoft PowerPoint presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_create_presentation()
    except Exception as e:
        return format_office_error(e, context="powerpoint_create_presentation", app_name="powerpoint")


@mcp.tool()
def powerpoint_open_presentation(file_path: str, read_only: bool = False) -> Dict[str, Any]:
    """Open an existing Microsoft PowerPoint presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_open_presentation(file_path=file_path, read_only=read_only)
    except Exception as e:
        return format_office_error(e, context="powerpoint_open_presentation", app_name="powerpoint")


@mcp.tool()
def powerpoint_save_presentation() -> Dict[str, Any]:
    """Save the active Microsoft PowerPoint presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_save_presentation()
    except Exception as e:
        return format_office_error(e, context="powerpoint_save_presentation", app_name="powerpoint")


@mcp.tool()
def powerpoint_save_as(file_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Save active presentation to a specified path with overwrite protection."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_save_as(file_path=file_path, overwrite=overwrite)
    except Exception as e:
        return format_office_error(e, context="powerpoint_save_as", app_name="powerpoint")


@mcp.tool()
def powerpoint_close_presentation(save_changes: bool = False) -> Dict[str, Any]:
    """Close the active Microsoft PowerPoint presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_close_presentation(save_changes=save_changes)
    except Exception as e:
        return format_office_error(e, context="powerpoint_close_presentation", app_name="powerpoint")


@mcp.tool()
def powerpoint_get_slides() -> List[Dict[str, Any]]:
    """Enumerate all slides in the active presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_get_slides()
    except Exception as e:
        return [format_office_error(e, context="powerpoint_get_slides", app_name="powerpoint")]


@mcp.tool()
def powerpoint_add_slide(layout: int = 2) -> Dict[str, Any]:
    """Add a new slide to the active presentation with the specified layout."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_slide(layout=layout)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_slide", app_name="powerpoint")


@mcp.tool()
def powerpoint_duplicate_slide(slide_index: int) -> Dict[str, Any]:
    """Duplicate an existing slide by 1-based index."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_duplicate_slide(slide_index=slide_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_duplicate_slide", app_name="powerpoint")


@mcp.tool()
def powerpoint_delete_slide(slide_index: int, confirmed: bool = False) -> Dict[str, Any]:
    """Delete a slide by 1-based index (destructive, requires confirmation)."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_delete_slide(slide_index=slide_index, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="powerpoint_delete_slide", app_name="powerpoint")


@mcp.tool()
def powerpoint_move_slide(from_index: int, to_index: int) -> Dict[str, Any]:
    """Move a slide from one position to another (1-based indices)."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_move_slide(from_index=from_index, to_index=to_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_move_slide", app_name="powerpoint")


@mcp.tool()
def powerpoint_hide_slide(slide_index: int, hide: bool = True) -> Dict[str, Any]:
    """Hide or unhide a slide during slide show presentations."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_hide_slide(slide_index=slide_index, hide=hide)
    except Exception as e:
        return format_office_error(e, context="powerpoint_hide_slide", app_name="powerpoint")


@mcp.tool()
def powerpoint_change_layout(slide_index: int, layout_name: str) -> Dict[str, Any]:
    """Change the layout of a slide (title, title_content, blank, two_content, etc.)."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_change_layout(slide_index=slide_index, layout_name=layout_name)
    except Exception as e:
        return format_office_error(e, context="powerpoint_change_layout", app_name="powerpoint")


@mcp.tool()
def powerpoint_set_title(slide_index: int, title: str) -> Dict[str, Any]:
    """Set the title text of a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_set_title(slide_index=slide_index, title=title)
    except Exception as e:
        return format_office_error(e, context="powerpoint_set_title", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_text(slide_index: int, text: str) -> Dict[str, Any]:
    """Add body text to a slide's primary body/content shape."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_text(slide_index=slide_index, text=text)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_text", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_bullets(slide_index: int, bullets: List[str]) -> Dict[str, Any]:
    """Add structured bullet points to a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_bullets(slide_index=slide_index, bullets=bullets)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_bullets", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_shape(
    slide_index: int,
    shape_type: str = "rectangle",
    left: float = 150.0,
    top: float = 150.0,
    width: float = 200.0,
    height: float = 120.0,
) -> Dict[str, Any]:
    """Add an AutoShape (rectangle, oval, arrow, etc.) to a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_shape(
            slide_index=slide_index,
            shape_type=shape_type,
            left=left,
            top=top,
            width=width,
            height=height,
        )
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_shape", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_textbox(
    slide_index: int,
    text: str,
    left: float = 100.0,
    top: float = 100.0,
    width: float = 400.0,
    height: float = 100.0,
) -> Dict[str, Any]:
    """Add a standalone text box to a slide with specified coordinates."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_textbox(
            slide_index=slide_index,
            text=text,
            left=left,
            top=top,
            width=width,
            height=height,
        )
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_textbox", app_name="powerpoint")


@mcp.tool()
def powerpoint_delete_shape(slide_index: int, shape_identifier: Union[int, str]) -> Dict[str, Any]:
    """Delete a shape from a slide by name or 1-based index."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_delete_shape(slide_index=slide_index, shape_identifier=shape_identifier)
    except Exception as e:
        return format_office_error(e, context="powerpoint_delete_shape", app_name="powerpoint")


@mcp.tool()
def powerpoint_format_text(
    slide_index: int,
    shape_identifier: Union[int, str] = "Title",
    font_name: Optional[str] = None,
    font_size: Optional[float] = None,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    color_bgr: Optional[int] = None,
) -> Dict[str, Any]:
    """Format font, size, style, or color of text within a slide shape."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_format_text(
            slide_index=slide_index,
            shape_identifier=shape_identifier,
            font_name=font_name,
            font_size=font_size,
            bold=bold,
            italic=italic,
            color_bgr=color_bgr,
        )
    except Exception as e:
        return format_office_error(e, context="powerpoint_format_text", app_name="powerpoint")


@mcp.tool()
def powerpoint_set_background(slide_index: int, color_bgr: int) -> Dict[str, Any]:
    """Set the solid background color of a slide using a BGR integer."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_set_background(slide_index=slide_index, color_bgr=color_bgr)
    except Exception as e:
        return format_office_error(e, context="powerpoint_set_background", app_name="powerpoint")


@mcp.tool()
def powerpoint_apply_theme(theme_path_or_name: str) -> Dict[str, Any]:
    """Apply an Office presentation theme (.thmx file)."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_apply_theme(theme_path_or_name=theme_path_or_name)
    except Exception as e:
        return format_office_error(e, context="powerpoint_apply_theme", app_name="powerpoint")


@mcp.tool()
def powerpoint_set_transition(slide_index: int, transition_name: str = "fade", duration: float = 1.0) -> Dict[str, Any]:
    """Set the transition effect and duration for a specific slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_set_transition(slide_index=slide_index, transition_name=transition_name, duration=duration)
    except Exception as e:
        return format_office_error(e, context="powerpoint_set_transition", app_name="powerpoint")


@mcp.tool()
def powerpoint_set_all_transitions(transition_name: str = "fade", duration: float = 1.0) -> Dict[str, Any]:
    """Apply a uniform transition effect to all slides in the presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_set_all_transitions(transition_name=transition_name, duration=duration)
    except Exception as e:
        return format_office_error(e, context="powerpoint_set_all_transitions", app_name="powerpoint")


@mcp.tool()
def powerpoint_get_transitions() -> Dict[str, Any]:
    """List transitions configured across all slides in active presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_get_transitions()
    except Exception as e:
        return format_office_error(e, context="powerpoint_get_transitions", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_animation(
    slide_index: int,
    shape_identifier: Union[int, str] = "Title",
    effect_name: str = "fly_in",
    start_mode: str = "on_click",
    duration: float = 0.75,
    delay: float = 0.0,
) -> Dict[str, Any]:
    """Add an animation effect (fly_in, fade, appear, zoom) to a shape in the timeline."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_animation(
            slide_index=slide_index,
            shape_identifier=shape_identifier,
            effect_name=effect_name,
            start_mode=start_mode,
            duration=duration,
            delay=delay,
        )
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_animation", app_name="powerpoint")


@mcp.tool()
def powerpoint_remove_animation(slide_index: int, effect_index: int = 1) -> Dict[str, Any]:
    """Remove an animation effect from a slide's timeline by index."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_remove_animation(slide_index=slide_index, effect_index=effect_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_remove_animation", app_name="powerpoint")


@mcp.tool()
def powerpoint_get_animations(slide_index: int) -> Dict[str, Any]:
    """Get all animation effects in the MainSequence timeline of a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_get_animations(slide_index=slide_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_get_animations", app_name="powerpoint")


@mcp.tool()
def powerpoint_clear_timeline(slide_index: int) -> Dict[str, Any]:
    """Clear all animations from a slide's MainSequence timeline."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_clear_timeline(slide_index=slide_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_clear_timeline", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_table(
    slide_index: int,
    rows: int = 3,
    columns: int = 3,
    data: Optional[List[List[Any]]] = None,
) -> Dict[str, Any]:
    """Insert a table onto a slide and optionally populate it with 2D data."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_table(slide_index=slide_index, rows=rows, columns=columns, data=data)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_table", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_chart(slide_index: int, chart_type: str = "column", title: Optional[str] = None) -> Dict[str, Any]:
    """Insert a chart (column, bar, line, pie) onto a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_chart(slide_index=slide_index, chart_type=chart_type, title=title)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_chart", app_name="powerpoint")


@mcp.tool()
def powerpoint_insert_picture(
    slide_index: int,
    file_path: str,
    left: float = 150.0,
    top: float = 150.0,
) -> Dict[str, Any]:
    """Insert an image file onto a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_insert_picture(slide_index=slide_index, file_path=file_path, left=left, top=top)
    except Exception as e:
        return format_office_error(e, context="powerpoint_insert_picture", app_name="powerpoint")


@mcp.tool()
def powerpoint_add_notes(slide_index: int, notes_text: str) -> Dict[str, Any]:
    """Add or replace speaker notes for a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_add_notes(slide_index=slide_index, notes_text=notes_text)
    except Exception as e:
        return format_office_error(e, context="powerpoint_add_notes", app_name="powerpoint")


@mcp.tool()
def powerpoint_get_notes(slide_index: int) -> Dict[str, Any]:
    """Retrieve speaker notes for a slide."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_get_notes(slide_index=slide_index)
    except Exception as e:
        return format_office_error(e, context="powerpoint_get_notes", app_name="powerpoint")


@mcp.tool()
def powerpoint_audit_presentation() -> Dict[str, Any]:
    """Audit the active presentation for empty titles, transitions, and animations."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_audit_presentation()
    except Exception as e:
        return format_office_error(e, context="powerpoint_audit_presentation", app_name="powerpoint")


@mcp.tool()
def powerpoint_accessibility_report() -> Dict[str, Any]:
    """Generate an accessibility check report for the active presentation."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_accessibility_report()
    except Exception as e:
        return format_office_error(e, context="powerpoint_accessibility_report", app_name="powerpoint")


@mcp.tool()
def powerpoint_export_pdf(output_path: str, overwrite: bool = True) -> Dict[str, Any]:
    """Export the active presentation to a high-fidelity PDF file."""
    _init_subsystems()
    try:
        return _day23_facade.ppt_export_pdf(output_path=output_path, overwrite=overwrite)
    except Exception as e:
        return format_office_error(e, context="powerpoint_export_pdf", app_name="powerpoint")


# =============================================================================
# Day 23 Tools: Outlook Automation Suite
# =============================================================================

@mcp.tool()
def outlook_inspect_live() -> Dict[str, Any]:
    """Inspect the live Microsoft Outlook instance, current user, and default folders."""
    _init_subsystems()
    try:
        return _day23_facade.ol_inspect_live()
    except Exception as e:
        return format_office_error(e, context="outlook_inspect_live", app_name="outlook")


@mcp.tool()
def outlook_get_unread_count() -> Dict[str, Any]:
    """Get the unread email count from Outlook's default Inbox."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_unread_count()
    except Exception as e:
        return format_office_error(e, context="outlook_get_unread_count", app_name="outlook")


@mcp.tool()
def outlook_get_recent_messages(limit: int = 5) -> List[Dict[str, Any]]:
    """Get the most recent messages from the Inbox."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_recent_messages(limit=limit)
    except Exception as e:
        return [format_office_error(e, context="outlook_get_recent_messages", app_name="outlook")]


@mcp.tool()
def outlook_search_messages(
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search Inbox messages by sender, subject substring, or unread status."""
    _init_subsystems()
    try:
        return _day23_facade.ol_search_messages(sender=sender, subject=subject, unread_only=unread_only, limit=limit)
    except Exception as e:
        return [format_office_error(e, context="outlook_search_messages", app_name="outlook")]


@mcp.tool()
def outlook_read_message(entry_id: str) -> Dict[str, Any]:
    """Read full details, plain-text body, and attachment list for a specific message."""
    _init_subsystems()
    try:
        return _day23_facade.ol_read_message(entry_id=entry_id)
    except Exception as e:
        return format_office_error(e, context="outlook_read_message", app_name="outlook")


@mcp.tool()
def outlook_create_draft(
    to_recipients: List[str],
    subject: str,
    body: str,
    cc_recipients: Optional[List[str]] = None,
    html_body: Optional[str] = None,
    attachment_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create and safely save a draft email in Outlook Drafts folder (never sent automatically)."""
    _init_subsystems()
    try:
        return _day23_facade.ol_create_draft(
            to_recipients=to_recipients,
            subject=subject,
            body=body,
            cc_recipients=cc_recipients,
            html_body=html_body,
            attachment_paths=attachment_paths,
        )
    except Exception as e:
        return format_office_error(e, context="outlook_create_draft", app_name="outlook")


@mcp.tool()
def outlook_reply_to_message(entry_id: str, reply_text: str, reply_all: bool = False) -> Dict[str, Any]:
    """Create a draft reply to an email message (saved to Drafts)."""
    _init_subsystems()
    try:
        return _day23_facade.ol_reply_to_message(entry_id=entry_id, reply_text=reply_text, reply_all=reply_all)
    except Exception as e:
        return format_office_error(e, context="outlook_reply_to_message", app_name="outlook")


@mcp.tool()
def outlook_forward_message(entry_id: str, to_recipients: List[str], forward_text: str = "") -> Dict[str, Any]:
    """Create a draft forward of an existing email (saved to Drafts)."""
    _init_subsystems()
    try:
        return _day23_facade.ol_forward_message(entry_id=entry_id, to_recipients=to_recipients, forward_text=forward_text)
    except Exception as e:
        return format_office_error(e, context="outlook_forward_message", app_name="outlook")


@mcp.tool()
def outlook_add_attachment(entry_id: str, file_path: str) -> Dict[str, Any]:
    """Attach a local file to an existing draft email."""
    _init_subsystems()
    try:
        return _day23_facade.ol_add_attachment(entry_id=entry_id, file_path=file_path)
    except Exception as e:
        return format_office_error(e, context="outlook_add_attachment", app_name="outlook")


@mcp.tool()
def outlook_prepare_send(entry_id: str) -> Dict[str, Any]:
    """Pre-send validation: inspect draft recipient count, subject, and preview prior to confirmation."""
    _init_subsystems()
    try:
        return _day23_facade.ol_prepare_send(entry_id=entry_id)
    except Exception as e:
        return format_office_error(e, context="outlook_prepare_send", app_name="outlook")


@mcp.tool()
def outlook_send_authorized(entry_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Send an authorized email. Strictly fails if confirmed is not True."""
    _init_subsystems()
    try:
        return _day23_facade.ol_send_authorized(entry_id=entry_id, confirmed=confirmed)
    except Exception as e:
        return format_office_error(e, context="outlook_send_authorized", app_name="outlook")


@mcp.tool()
def outlook_get_folders() -> List[Dict[str, Any]]:
    """List mail folders in the default Outlook store."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_folders()
    except Exception as e:
        return [format_office_error(e, context="outlook_get_folders", app_name="outlook")]


@mcp.tool()
def outlook_create_folder(folder_name: str) -> Dict[str, Any]:
    """Create a new subfolder under Outlook Inbox."""
    _init_subsystems()
    try:
        return _day23_facade.ol_create_folder(folder_name=folder_name)
    except Exception as e:
        return format_office_error(e, context="outlook_create_folder", app_name="outlook")


@mcp.tool()
def outlook_move_message(entry_id: str, destination_folder_name: str) -> Dict[str, Any]:
    """Move an email message to a specified folder."""
    _init_subsystems()
    try:
        return _day23_facade.ol_move_message(entry_id=entry_id, destination_folder_name=destination_folder_name)
    except Exception as e:
        return format_office_error(e, context="outlook_move_message", app_name="outlook")


@mcp.tool()
def outlook_get_categories() -> List[str]:
    """List available category names configured in Outlook."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_categories()
    except Exception as e:
        return [str(e)]


@mcp.tool()
def outlook_assign_category(entry_id: str, category_name: str) -> Dict[str, Any]:
    """Assign a color category label to an email message."""
    _init_subsystems()
    try:
        return _day23_facade.ol_assign_category(entry_id=entry_id, category_name=category_name)
    except Exception as e:
        return format_office_error(e, context="outlook_assign_category", app_name="outlook")


@mcp.tool()
def outlook_mark_read(entry_id: str, is_read: bool = True) -> Dict[str, Any]:
    """Mark an email message as read or unread."""
    _init_subsystems()
    try:
        return _day23_facade.ol_mark_read(entry_id=entry_id, is_read=is_read)
    except Exception as e:
        return format_office_error(e, context="outlook_mark_read", app_name="outlook")


@mcp.tool()
def outlook_search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search Outlook Contacts by name or email address."""
    _init_subsystems()
    try:
        return _day23_facade.ol_search_contacts(query=query)
    except Exception as e:
        return [format_office_error(e, context="outlook_search_contacts", app_name="outlook")]


@mcp.tool()
def outlook_create_contact(full_name: str, email: str) -> Dict[str, Any]:
    """Create a new contact in Outlook Contacts folder."""
    _init_subsystems()
    try:
        return _day23_facade.ol_create_contact(full_name=full_name, email=email)
    except Exception as e:
        return format_office_error(e, context="outlook_create_contact", app_name="outlook")


@mcp.tool()
def outlook_get_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve tasks from Outlook Tasks folder."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_tasks(limit=limit)
    except Exception as e:
        return [format_office_error(e, context="outlook_get_tasks", app_name="outlook")]


@mcp.tool()
def outlook_create_task(subject: str, due_date: Optional[str] = None) -> Dict[str, Any]:
    """Create a new task item in Outlook Tasks folder."""
    _init_subsystems()
    try:
        return _day23_facade.ol_create_task(subject=subject, due_date=due_date)
    except Exception as e:
        return format_office_error(e, context="outlook_create_task", app_name="outlook")


@mcp.tool()
def outlook_get_calendar_items(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve upcoming appointments/meetings from Outlook Calendar."""
    _init_subsystems()
    try:
        return _day23_facade.ol_get_calendar_items(limit=limit)
    except Exception as e:
        return [format_office_error(e, context="outlook_get_calendar_items", app_name="outlook")]


@mcp.tool()
def outlook_create_calendar_item(subject: str, start_time: str, duration_minutes: int = 30) -> Dict[str, Any]:
    """Schedule a new appointment in Outlook Calendar."""
    _init_subsystems()
    try:
        return _day23_facade.ol_create_calendar_item(
            subject=subject,
            start_time=start_time,
            duration_minutes=duration_minutes,
        )
    except Exception as e:
        return format_office_error(e, context="outlook_create_calendar_item", app_name="outlook")


# =============================================================================
# Day 23 Tools: Desktop UI Automation Suite
# =============================================================================

@mcp.tool()
def desktop_inspect_active_window() -> Dict[str, Any]:
    """Inspect currently focused foreground window title, process name, PID, and HWND."""
    _init_subsystems()
    try:
        return _day23_facade.desktop_inspect_active_window()
    except Exception as e:
        return format_office_error(e, context="desktop_inspect_active_window", app_name="desktop_ui")


@mcp.tool()
def desktop_inspect_app_ui(max_controls: int = 50) -> Dict[str, Any]:
    """Inspect top-level UI controls and elements of the active foreground application."""
    _init_subsystems()
    try:
        return _day23_facade.desktop_inspect_app_ui(max_controls=max_controls)
    except Exception as e:
        return format_office_error(e, context="desktop_inspect_app_ui", app_name="desktop_ui")


@mcp.tool()
def desktop_execute_keyboard_sequence(keys: List[str], expected_process: Optional[str] = None) -> Dict[str, Any]:
    """Execute a safe, bounded keyboard shortcut sequence with foreground window safety verification."""
    _init_subsystems()
    try:
        return _day23_facade.desktop_execute_keyboard_sequence(keys=keys, expected_process=expected_process)
    except Exception as e:
        return format_office_error(e, context="desktop_execute_keyboard_sequence", app_name="desktop_ui")


@mcp.tool()
def desktop_trigger_ribbon_accelerator(tab_key: str, expected_process: Optional[str] = None) -> Dict[str, Any]:
    """Trigger a Microsoft Office Ribbon tab accelerator shortcut safely with focus verification."""
    _init_subsystems()
    try:
        return _day23_facade.desktop_trigger_ribbon_accelerator(tab_key=tab_key, expected_process=expected_process)
    except Exception as e:
        return format_office_error(e, context="desktop_trigger_ribbon_accelerator", app_name="desktop_ui")


# =============================================================================
# Standalone CLI / FastMCP stdio Runner
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Zye Microsoft Office Live COM Master MCP Server...")
    _init_subsystems()
    mcp.run()
