"""
Day 23 MCP Tool Integration Facade — Zye Day 23.
Consolidates PowerPoint, Outlook, and Desktop UI engines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from zye_office.desktop_ui import (
    DesktopRibbonAccelerator,
    DesktopUIInspector,
    KeyboardSequenceEngine,
)
from zye_office.outlook import (
    OutlookAdapter,
    OutlookAttachmentManager,
    OutlookCategoryManager,
    OutlookContactTaskManager,
    OutlookDraftEngine,
    OutlookFolderManager,
    OutlookMailboxInspector,
    OutlookMessageReader,
    OutlookReplyEngine,
    OutlookSearchEngine,
    OutlookSendEngine,
)
from zye_office.powerpoint import (
    PowerPointAccessibilityEngine,
    PowerPointAdapter,
    PowerPointAnimationEngine,
    PowerPointAuditor,
    PowerPointChartEngine,
    PowerPointContentEngine,
    PowerPointExporter,
    PowerPointFormattingEngine,
    PowerPointLayoutEngine,
    PowerPointMediaEngine,
    PowerPointNotesEngine,
    PowerPointPresentationManager,
    PowerPointShapeEngine,
    PowerPointSlideManager,
    PowerPointSlideMasterEngine,
    PowerPointTableEngine,
    PowerPointThemeEngine,
    PowerPointTimelineEngine,
    PowerPointTransitionEngine,
)

logger = logging.getLogger("zye.office.day23_facade")


class Day23MCPIntegrationFacade:
    """Consolidated facade managing PowerPoint, Outlook, and Desktop UI capabilities."""

    def __init__(self) -> None:
        # PowerPoint Subsystems
        self.ppt_adapter = PowerPointAdapter()
        self.ppt_manager = PowerPointPresentationManager(adapter=self.ppt_adapter)
        self.slide_manager = PowerPointSlideManager(adapter=self.ppt_adapter)
        self.layout_engine = PowerPointLayoutEngine(adapter=self.ppt_adapter)
        self.content_engine = PowerPointContentEngine(adapter=self.ppt_adapter)
        self.shape_engine = PowerPointShapeEngine(adapter=self.ppt_adapter)
        self.formatting_engine = PowerPointFormattingEngine(adapter=self.ppt_adapter)
        self.master_engine = PowerPointSlideMasterEngine(adapter=self.ppt_adapter)
        self.theme_engine = PowerPointThemeEngine(adapter=self.ppt_adapter)
        self.transition_engine = PowerPointTransitionEngine(adapter=self.ppt_adapter)
        self.animation_engine = PowerPointAnimationEngine(adapter=self.ppt_adapter)
        self.timeline_engine = PowerPointTimelineEngine(adapter=self.ppt_adapter)
        self.table_engine = PowerPointTableEngine(adapter=self.ppt_adapter)
        self.chart_engine = PowerPointChartEngine(adapter=self.ppt_adapter)
        self.media_engine = PowerPointMediaEngine(adapter=self.ppt_adapter)
        self.notes_engine = PowerPointNotesEngine(adapter=self.ppt_adapter)
        self.accessibility_engine = PowerPointAccessibilityEngine(adapter=self.ppt_adapter)
        self.auditor = PowerPointAuditor(adapter=self.ppt_adapter)
        self.exporter = PowerPointExporter(adapter=self.ppt_adapter)

        # Outlook Subsystems
        self.ol_adapter = OutlookAdapter()
        self.mailbox_inspector = OutlookMailboxInspector(adapter=self.ol_adapter)
        self.message_reader = OutlookMessageReader(adapter=self.ol_adapter)
        self.search_engine = OutlookSearchEngine(adapter=self.ol_adapter)
        self.draft_engine = OutlookDraftEngine(adapter=self.ol_adapter)
        self.reply_engine = OutlookReplyEngine(adapter=self.ol_adapter)
        self.attachment_manager = OutlookAttachmentManager(adapter=self.ol_adapter)
        self.send_engine = OutlookSendEngine(adapter=self.ol_adapter)
        self.folder_manager = OutlookFolderManager(adapter=self.ol_adapter)
        self.category_manager = OutlookCategoryManager(adapter=self.ol_adapter)
        self.contact_task_manager = OutlookContactTaskManager(adapter=self.ol_adapter)

        # Desktop UI Subsystems
        self.ui_inspector = DesktopUIInspector()
        self.keyboard_engine = KeyboardSequenceEngine()
        self.ribbon_accelerator = DesktopRibbonAccelerator(self.keyboard_engine)

    # -------------------------------------------------------------------------
    # PowerPoint Operations
    # -------------------------------------------------------------------------

    def ppt_inspect_live(self) -> Dict[str, Any]:
        return self.ppt_adapter.inspect_powerpoint_application()

    def ppt_create_presentation(self) -> Dict[str, Any]:
        return self.ppt_manager.create_presentation()

    def ppt_open_presentation(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        return self.ppt_manager.open_presentation(file_path=file_path, read_only=read_only)

    def ppt_save_presentation(self) -> Dict[str, Any]:
        return self.ppt_manager.save_presentation()

    def ppt_save_as(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        return self.ppt_manager.save_presentation_as(file_path=file_path, overwrite=overwrite)

    def ppt_close_presentation(self, save_changes: bool = False) -> Dict[str, Any]:
        return self.ppt_manager.close_presentation(save_changes=save_changes)

    def ppt_get_slides(self) -> List[Dict[str, Any]]:
        return self.slide_manager.get_all_slides()

    def ppt_add_slide(self, layout: int = 2) -> Dict[str, Any]:
        return self.slide_manager.add_slide(layout=layout)

    def ppt_duplicate_slide(self, slide_index: int) -> Dict[str, Any]:
        return self.slide_manager.duplicate_slide(slide_index=slide_index)

    def ppt_delete_slide(self, slide_index: int, confirmed: bool = False) -> Dict[str, Any]:
        return self.slide_manager.delete_slide(slide_index=slide_index, confirmed=confirmed)

    def ppt_move_slide(self, from_index: int, to_index: int) -> Dict[str, Any]:
        return self.slide_manager.move_slide(from_index=from_index, to_index=to_index)

    def ppt_hide_slide(self, slide_index: int, hide: bool = True) -> Dict[str, Any]:
        return self.slide_manager.hide_slide(slide_index=slide_index, hide=hide)

    def ppt_change_layout(self, slide_index: int, layout_name: str) -> Dict[str, Any]:
        return self.layout_engine.change_layout(slide_index=slide_index, layout_name=layout_name)

    def ppt_set_title(self, slide_index: int, title: str) -> Dict[str, Any]:
        return self.content_engine.set_slide_title(slide_index=slide_index, title=title)

    def ppt_add_text(self, slide_index: int, text: str) -> Dict[str, Any]:
        return self.content_engine.add_slide_text(slide_index=slide_index, text=text)

    def ppt_add_bullets(self, slide_index: int, bullets: List[str]) -> Dict[str, Any]:
        return self.content_engine.add_bullet_points(slide_index=slide_index, bullets=bullets)

    def ppt_add_shape(self, slide_index: int, shape_type: str = "rectangle", left: float = 150.0, top: float = 150.0, width: float = 200.0, height: float = 120.0) -> Dict[str, Any]:
        return self.shape_engine.add_shape(slide_index=slide_index, shape_type=shape_type, left=left, top=top, width=width, height=height)

    def ppt_add_textbox(self, slide_index: int, text: str, left: float = 100.0, top: float = 100.0, width: float = 400.0, height: float = 100.0) -> Dict[str, Any]:
        return self.shape_engine.add_textbox(slide_index=slide_index, text=text, left=left, top=top, width=width, height=height)

    def ppt_delete_shape(self, slide_index: int, shape_identifier: Any) -> Dict[str, Any]:
        return self.shape_engine.delete_shape(slide_index=slide_index, shape_identifier=shape_identifier)

    def ppt_format_text(self, slide_index: int, shape_identifier: Any = "Title", font_name: Optional[str] = None, font_size: Optional[float] = None, bold: Optional[bool] = None, italic: Optional[bool] = None, color_bgr: Optional[int] = None) -> Dict[str, Any]:
        return self.formatting_engine.format_text(slide_index=slide_index, shape_identifier=shape_identifier, font_name=font_name, font_size=font_size, bold=bold, italic=italic, color_bgr=color_bgr)

    def ppt_set_background(self, slide_index: int, color_bgr: int) -> Dict[str, Any]:
        return self.formatting_engine.set_slide_background(slide_index=slide_index, color_bgr=color_bgr)

    def ppt_apply_theme(self, theme_path_or_name: str) -> Dict[str, Any]:
        return self.theme_engine.apply_theme(theme_path_or_name=theme_path_or_name)

    def ppt_set_transition(self, slide_index: int, transition_name: str = "fade", duration: float = 1.0) -> Dict[str, Any]:
        return self.transition_engine.set_slide_transition(slide_index=slide_index, transition_name=transition_name, duration=duration)

    def ppt_set_all_transitions(self, transition_name: str = "fade", duration: float = 1.0) -> Dict[str, Any]:
        return self.transition_engine.set_all_slide_transitions(transition_name=transition_name, duration=duration)

    def ppt_get_transitions(self) -> Dict[str, Any]:
        return self.transition_engine.get_slide_transitions()

    def ppt_add_animation(self, slide_index: int, shape_identifier: Any = "Title", effect_name: str = "fly_in", start_mode: str = "on_click", duration: float = 0.75, delay: float = 0.0) -> Dict[str, Any]:
        return self.animation_engine.add_animation(slide_index=slide_index, shape_identifier=shape_identifier, effect_name=effect_name, start_mode=start_mode, duration=duration, delay=delay)

    def ppt_remove_animation(self, slide_index: int, effect_index: int = 1) -> Dict[str, Any]:
        return self.animation_engine.remove_animation(slide_index=slide_index, effect_index=effect_index)

    def ppt_get_animations(self, slide_index: int) -> Dict[str, Any]:
        return self.animation_engine.get_slide_animations(slide_index=slide_index)

    def ppt_clear_timeline(self, slide_index: int) -> Dict[str, Any]:
        return self.timeline_engine.clear_timeline(slide_index=slide_index)

    def ppt_add_table(self, slide_index: int, rows: int = 3, columns: int = 3, data: Optional[List[List[Any]]] = None) -> Dict[str, Any]:
        return self.table_engine.add_table(slide_index=slide_index, rows=rows, columns=columns, data=data)

    def ppt_add_chart(self, slide_index: int, chart_type: str = "column", title: Optional[str] = None) -> Dict[str, Any]:
        return self.chart_engine.add_chart(slide_index=slide_index, chart_type=chart_type, title=title)

    def ppt_insert_picture(self, slide_index: int, file_path: str, left: float = 150.0, top: float = 150.0) -> Dict[str, Any]:
        return self.media_engine.insert_picture(slide_index=slide_index, file_path=file_path, left=left, top=top)

    def ppt_add_notes(self, slide_index: int, notes_text: str) -> Dict[str, Any]:
        return self.notes_engine.add_notes(slide_index=slide_index, notes_text=notes_text)

    def ppt_get_notes(self, slide_index: int) -> Dict[str, Any]:
        return self.notes_engine.get_notes(slide_index=slide_index)

    def ppt_audit_presentation(self) -> Dict[str, Any]:
        return self.auditor.audit_presentation()

    def ppt_accessibility_report(self) -> Dict[str, Any]:
        return self.accessibility_engine.generate_accessibility_report()

    def ppt_export_pdf(self, output_path: str, overwrite: bool = True) -> Dict[str, Any]:
        return self.exporter.export_pdf(output_path=output_path, overwrite=overwrite)

    # -------------------------------------------------------------------------
    # Outlook Operations
    # -------------------------------------------------------------------------

    def ol_inspect_live(self) -> Dict[str, Any]:
        return self.ol_adapter.inspect_outlook_application()

    def ol_get_unread_count(self) -> Dict[str, Any]:
        return self.mailbox_inspector.get_unread_count()

    def ol_get_recent_messages(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.mailbox_inspector.get_recent_messages(limit=limit)

    def ol_search_messages(self, sender: Optional[str] = None, subject: Optional[str] = None, unread_only: bool = False, limit: int = 10) -> List[Dict[str, Any]]:
        return self.search_engine.search_messages(sender=sender, subject=subject, unread_only=unread_only, limit=limit)

    def ol_read_message(self, entry_id: str) -> Dict[str, Any]:
        return self.message_reader.read_message(entry_id=entry_id)

    def ol_create_draft(self, to_recipients: List[str], subject: str, body: str, cc_recipients: Optional[List[str]] = None, html_body: Optional[str] = None, attachment_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.draft_engine.create_draft(to_recipients=to_recipients, subject=subject, body=body, cc_recipients=cc_recipients, html_body=html_body, attachment_paths=attachment_paths)

    def ol_reply_to_message(self, entry_id: str, reply_text: str, reply_all: bool = False) -> Dict[str, Any]:
        return self.reply_engine.reply_to_message(entry_id=entry_id, reply_text=reply_text, reply_all=reply_all)

    def ol_forward_message(self, entry_id: str, to_recipients: List[str], forward_text: str = "") -> Dict[str, Any]:
        return self.reply_engine.forward_message(entry_id=entry_id, to_recipients=to_recipients, forward_text=forward_text)

    def ol_add_attachment(self, entry_id: str, file_path: str) -> Dict[str, Any]:
        return self.attachment_manager.add_attachment(entry_id=entry_id, file_path=file_path)

    def ol_prepare_send(self, entry_id: str) -> Dict[str, Any]:
        return self.send_engine.prepare_send_summary(entry_id=entry_id)

    def ol_send_authorized(self, entry_id: str, confirmed: bool = False) -> Dict[str, Any]:
        return self.send_engine.send_authorized_email(entry_id=entry_id, confirmed=confirmed)

    def ol_get_folders(self) -> List[Dict[str, Any]]:
        return self.folder_manager.get_folders()

    def ol_create_folder(self, folder_name: str) -> Dict[str, Any]:
        return self.folder_manager.create_folder(folder_name=folder_name)

    def ol_move_message(self, entry_id: str, destination_folder_name: str) -> Dict[str, Any]:
        return self.folder_manager.move_message(entry_id=entry_id, destination_folder_name=destination_folder_name)

    def ol_get_categories(self) -> List[str]:
        return self.category_manager.get_categories()

    def ol_assign_category(self, entry_id: str, category_name: str) -> Dict[str, Any]:
        return self.category_manager.assign_category(entry_id=entry_id, category_name=category_name)

    def ol_mark_read(self, entry_id: str, is_read: bool = True) -> Dict[str, Any]:
        return self.category_manager.mark_read_status(entry_id=entry_id, is_read=is_read)

    def ol_search_contacts(self, query: str) -> List[Dict[str, Any]]:
        return self.contact_task_manager.search_contacts(query=query)

    def ol_create_contact(self, full_name: str, email: str) -> Dict[str, Any]:
        return self.contact_task_manager.create_contact(full_name=full_name, email=email)

    def ol_get_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.contact_task_manager.get_tasks(limit=limit)

    def ol_create_task(self, subject: str, due_date: Optional[str] = None) -> Dict[str, Any]:
        return self.contact_task_manager.create_task(subject=subject, due_date=due_date)

    def ol_get_calendar_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.contact_task_manager.get_calendar_items(limit=limit)

    def ol_create_calendar_item(self, subject: str, start_time: str, duration_minutes: int = 30) -> Dict[str, Any]:
        return self.contact_task_manager.create_calendar_item(subject=subject, start_time=start_time, duration_minutes=duration_minutes)

    # -------------------------------------------------------------------------
    # Desktop UI Operations
    # -------------------------------------------------------------------------

    def desktop_inspect_active_window(self) -> Dict[str, Any]:
        return self.ui_inspector.inspect_active_window()

    def desktop_inspect_app_ui(self, max_controls: int = 50) -> Dict[str, Any]:
        return self.ui_inspector.inspect_app_controls(max_controls=max_controls)

    def desktop_execute_keyboard_sequence(self, keys: List[str], expected_process: Optional[str] = None) -> Dict[str, Any]:
        return self.keyboard_engine.execute_sequence(keys=keys, expected_process=expected_process)

    def desktop_trigger_ribbon_accelerator(self, tab_key: str, expected_process: Optional[str] = None) -> Dict[str, Any]:
        return self.ribbon_accelerator.trigger_ribbon_tab(tab_key=tab_key, expected_process=expected_process)
