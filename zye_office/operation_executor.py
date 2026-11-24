"""
Zye Office Operation Executor
Dispatches allowlisted operations to the Single-Threaded Apartment (STA) COM worker.
Guarantees thread-safety, argument validation, and bounded result serialization.
"""

from typing import Dict, Any, Optional
import time
import sys

from zye_office.models import OfficeAppType, RiskCategory, OfficeOperation
from zye_office.errors import (
    OfficeCOMError,
    OfficeValidationError,
    OfficeSecurityError,
    format_office_error,
)
from zye_office.operation_registry import OfficeOperationRegistry
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.session_manager import OfficeSessionManager
from zye_office.path_validator import OfficePathValidator


class OfficeOperationExecutor:
    """
    Validates, orchestrates and executes typed allowlisted operations
    against live Office applications via the STA COM worker.
    """

    def __init__(
        self,
        runtime: OfficeCOMRuntime,
        session_manager: OfficeSessionManager,
        registry: Optional[OfficeOperationRegistry] = None,
        path_validator: Optional[OfficePathValidator] = None,
    ):
        self.runtime = runtime
        self.session_manager = session_manager
        self.registry = registry or OfficeOperationRegistry()
        self.path_validator = path_validator or OfficePathValidator()

    def execute(self, session_id: str, operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the operation and executes it synchronously inside the STA COM worker.
        """
        # 1. Validate session
        session = self.session_manager.get_session(session_id)
        if not session or not session.is_active:
            raise OfficeValidationError(f"Invalid or inactive session ID: {session_id}")

        # 2. Validate allowlisted operation schema
        op_def, clean_params = self.registry.validate_and_normalize(operation_id, params)

        # 3. Check application compatibility
        if op_def.app_type != session.app_type:
            raise OfficeValidationError(
                f"Operation '{operation_id}' is for {op_def.app_type.value}, but session '{session_id}' is {session.app_type.value}"
            )

        # 4. Execute on STA COM worker
        start_time = time.time()
        try:
            result = self.runtime.worker.run(
                self._dispatch_internal,
                session_id=session_id,
                app_type=session.app_type,
                operation_id=operation_id,
                params=clean_params,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Record telemetry / state
            self.session_manager.touch_session(session_id)
            if isinstance(result, dict):
                result["elapsed_ms"] = round(elapsed_ms, 2)
                result["session_id"] = session_id
                result["operation_id"] = operation_id
            return result
        except Exception as e:
            err_dict = format_office_error(e, context=f"execute_{operation_id}")
            err_dict["session_id"] = session_id
            err_dict["operation_id"] = operation_id
            return err_dict

    def _dispatch_internal(
        self,
        session_id: str,
        app_type: OfficeAppType,
        operation_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Runs strictly within the STA worker thread."""
        app = self.runtime.get_app_instance(session_id)
        if not app:
            raise OfficeCOMError(f"COM instance for session '{session_id}' not found in worker cache")

        # Route by application
        if app_type == OfficeAppType.WORD:
            return self._exec_word(app, operation_id, params)
        elif app_type == OfficeAppType.EXCEL:
            return self._exec_excel(app, operation_id, params)
        elif app_type == OfficeAppType.POWERPOINT:
            return self._exec_powerpoint(app, operation_id, params)
        elif app_type == OfficeAppType.OUTLOOK:
            return self._exec_outlook(app, operation_id, params)
        else:
            raise OfficeValidationError(f"Unsupported application type: {app_type}")

    # --- Word Handlers ---
    def _exec_word(self, app: Any, operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if app.Documents.Count == 0 and operation_id != "word.save_document":
            raise OfficeCOMError("Word has no open document to execute operation upon")

        doc = app.ActiveDocument if app.Documents.Count > 0 else None

        if operation_id == "word.insert_text":
            text = params["text"]
            location = params.get("location", "end")
            if location == "end":
                doc.Content.InsertAfter(text)
            elif location == "start":
                doc.Content.InsertBefore(text)
            elif location == "selection":
                app.Selection.TypeText(text)
            return {"success": True, "chars_inserted": len(text), "location": location}

        elif operation_id == "word.insert_heading":
            text = params["text"]
            level = params.get("level", 1)
            sel = app.Selection
            sel.TypeParagraph()
            rng = sel.Range
            rng.Text = text
            try:
                # Built-in heading styles: "Heading 1", "Heading 2", etc.
                rng.Style = f"Heading {level}"
            except Exception:
                # Fallback if localized style names differ
                try:
                    rng.Bold = True
                    rng.Font.Size = max(12, 22 - (level * 2))
                except Exception:
                    pass
            sel.TypeParagraph()
            return {"success": True, "heading": text, "level": level}

        elif operation_id == "word.apply_style":
            style_name = params["style_name"]
            sel = app.Selection
            sel.Style = style_name
            return {"success": True, "applied_style": style_name}

        elif operation_id == "word.set_track_changes":
            enabled = params["enabled"]
            doc.TrackRevisions = enabled
            return {"success": True, "track_revisions": doc.TrackRevisions}

        elif operation_id == "word.save_document":
            target_path = params.get("path")
            if target_path:
                validated = self.path_validator.validate_path(target_path, OfficeAppType.WORD)
                doc.SaveAs(validated)
                saved_path = validated
            else:
                doc.Save()
                saved_path = getattr(doc, "FullName", "")
            return {"success": True, "saved_path": saved_path}

        raise OfficeValidationError(f"Unknown Word operation: {operation_id}")

    # --- Excel Handlers ---
    def _exec_excel(self, app: Any, operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation_id == "excel.calculate":
            app.Calculate()
            return {"success": True, "message": "Recalculation triggered successfully"}

        if app.Workbooks.Count == 0:
            raise OfficeCOMError("Excel has no open workbook to execute operation upon")

        wb = app.ActiveWorkbook
        sheet_name = params.get("sheet")
        ws = wb.Sheets(sheet_name) if sheet_name else app.ActiveSheet

        if operation_id == "excel.set_cell_value":
            cell = params["cell"]
            val = params["value"]
            ws.Range(cell).Value = val
            return {"success": True, "cell": cell, "value": val, "sheet": ws.Name}

        elif operation_id == "excel.set_cell_formula":
            cell = params["cell"]
            formula = params["formula"]
            if not formula.startswith("="):
                formula = f"={formula}"
            ws.Range(cell).Formula = formula
            return {"success": True, "cell": cell, "formula": formula, "sheet": ws.Name}

        elif operation_id == "excel.format_range":
            addr = params["range_address"]
            rng = ws.Range(addr)
            if params.get("bold") is not None:
                rng.Font.Bold = params["bold"]
            if params.get("italic") is not None:
                rng.Font.Italic = params["italic"]
            if params.get("font_size") is not None:
                rng.Font.Size = params["font_size"]
            if params.get("font_name") is not None:
                rng.Font.Name = params["font_name"]
            if params.get("color") is not None:
                rng.Font.Color = params["color"]
            return {"success": True, "range": addr, "sheet": ws.Name}

        elif operation_id == "excel.save_workbook":
            target_path = params.get("path")
            if target_path:
                validated = self.path_validator.validate_path(target_path, OfficeAppType.EXCEL)
                wb.SaveAs(validated)
                saved_path = validated
            else:
                wb.Save()
                saved_path = getattr(wb, "FullName", "")
            return {"success": True, "saved_path": saved_path}

        raise OfficeValidationError(f"Unknown Excel operation: {operation_id}")

    # --- PowerPoint Handlers ---
    def _exec_powerpoint(self, app: Any, operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if app.Presentations.Count == 0:
            raise OfficeCOMError("PowerPoint has no open presentation to execute operation upon")

        pres = app.ActivePresentation

        if operation_id == "powerpoint.get_slide_details":
            idx = params["slide_index"]
            if idx < 1 or idx > pres.Slides.Count:
                raise OfficeValidationError(f"Slide index {idx} out of range (1..{pres.Slides.Count})")
            slide = pres.Slides(idx)
            text_snippets = []
            for shape in slide.Shapes:
                try:
                    if shape.HasTextFrame and shape.TextFrame.HasText:
                        snippet = shape.TextFrame.TextRange.Text.strip()
                        if snippet:
                            text_snippets.append(snippet[:100])
                except Exception:
                    pass
            return {
                "success": True,
                "slide_index": idx,
                "shapes_count": slide.Shapes.Count,
                "text_previews": text_snippets[:5],
            }

        elif operation_id == "powerpoint.insert_slide":
            idx = params.get("index", -1)
            layout = params.get("layout", 1)  # 1 = ppLayoutTitle, 2 = ppLayoutText
            total = pres.Slides.Count
            target_pos = total + 1 if idx <= 0 or idx > total + 1 else idx
            new_slide = pres.Slides.Add(target_pos, layout)
            return {
                "success": True,
                "slide_index": new_slide.SlideIndex,
                "total_slides": pres.Slides.Count,
            }

        elif operation_id == "powerpoint.set_slide_title":
            idx = params["slide_index"]
            title = params["title"]
            if idx < 1 or idx > pres.Slides.Count:
                raise OfficeValidationError(f"Slide index {idx} out of range (1..{pres.Slides.Count})")
            slide = pres.Slides(idx)
            for shape in slide.Shapes:
                try:
                    if shape.HasTitle:
                        shape.TextFrame.TextRange.Text = title
                        return {"success": True, "slide_index": idx, "title": title}
                except Exception:
                    pass
            # If HasTitle not matched, try Shape 1
            if slide.Shapes.Count >= 1:
                try:
                    slide.Shapes(1).TextFrame.TextRange.Text = title
                    return {"success": True, "slide_index": idx, "title": title}
                except Exception:
                    pass
            return {"success": False, "error": "No title placeholder available on slide"}

        elif operation_id == "powerpoint.save_presentation":
            target_path = params.get("path")
            if target_path:
                validated = self.path_validator.validate_path(target_path, OfficeAppType.POWERPOINT)
                pres.SaveAs(validated)
                saved_path = validated
            else:
                pres.Save()
                saved_path = getattr(pres, "FullName", "")
            return {"success": True, "saved_path": saved_path}

        raise OfficeValidationError(f"Unknown PowerPoint operation: {operation_id}")

    # --- Outlook Handlers ---
    def _exec_outlook(self, app: Any, operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if operation_id == "outlook.create_draft":
            subject = params["subject"]
            body = params["body"]
            to = params.get("to", "")
            cc = params.get("cc", "")
            is_html = params.get("is_html", False)

            # olMailItem = 0
            mail = app.CreateItem(0)
            mail.Subject = subject
            if is_html:
                mail.HTMLBody = body
            else:
                mail.Body = body
            if to:
                mail.To = to
            if cc:
                mail.CC = cc
            # Explicit draft saving: never auto-sent
            mail.Save()
            entry_id = getattr(mail, "EntryID", "")
            return {
                "success": True,
                "status": "saved_to_drafts",
                "subject": subject,
                "to": to,
                "entry_id": entry_id,
            }

        elif operation_id == "outlook.get_unread_count":
            folder_name = params.get("folder_name", "Inbox")
            ns = app.GetNamespace("MAPI")
            # olFolderInbox = 6
            folder = ns.GetDefaultFolder(6)
            if folder_name.lower() != "inbox":
                try:
                    folder = folder.Folders(folder_name)
                except Exception:
                    pass
            unread = getattr(folder, "UnReadItemCount", 0)
            total = getattr(folder.Items, "Count", 0) if hasattr(folder, "Items") else 0
            return {
                "success": True,
                "folder": getattr(folder, "Name", folder_name),
                "unread_count": unread,
                "total_items": total,
            }

        raise OfficeValidationError(f"Unknown Outlook operation: {operation_id}")
