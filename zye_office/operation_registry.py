"""
Zye Office Operation Registry
Maintains a strict, typed allowlist of permitted Office automation operations.
Dynamic code evaluation (exec, eval, arbitrary VBA) is strictly prohibited.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from zye_office.models import OfficeAppType, RiskCategory, OfficeOperation
from zye_office.errors import OfficeSecurityError, OfficeValidationError


@dataclass
class ParamDef:
    name: str
    param_type: type
    required: bool = True
    default: Any = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""


@dataclass
class OperationDef:
    operation_id: str
    app_type: OfficeAppType
    description: str
    risk_level: RiskCategory = RiskCategory.LOW_RISK
    params: Dict[str, ParamDef] = field(default_factory=dict)
    requires_active_document: bool = True

    def validate_params(self, passed_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates passed arguments against parameter definitions.
        Returns a normalized parameter dictionary with defaults applied.
        """
        validated = {}
        for param_name, pdef in self.params.items():
            if param_name in passed_params:
                val = passed_params[param_name]
                # Type check
                if pdef.param_type is not Any:
                    if pdef.param_type is int and isinstance(val, (int, float)) and not isinstance(val, bool):
                        val = int(val)
                    elif pdef.param_type is float and isinstance(val, (int, float)) and not isinstance(val, bool):
                        val = float(val)
                    elif pdef.param_type is bool and isinstance(val, bool):
                        pass
                    elif pdef.param_type is str and isinstance(val, str):
                        pass
                    elif not isinstance(val, pdef.param_type):
                        raise OfficeValidationError(
                            f"Parameter '{param_name}' must be of type {pdef.param_type.__name__}, got {type(val).__name__}"
                        )
                
                # Value check
                if pdef.allowed_values is not None and val not in pdef.allowed_values:
                    raise OfficeValidationError(
                        f"Parameter '{param_name}' value '{val}' not in allowed values: {pdef.allowed_values}"
                    )
                validated[param_name] = val
            else:
                if pdef.required:
                    raise OfficeValidationError(f"Missing required parameter '{param_name}' for operation '{self.operation_id}'")
                validated[param_name] = pdef.default

        # Disallow unrecognized parameters to prevent injection or confusion
        for k in passed_params:
            if k not in self.params:
                raise OfficeValidationError(f"Unrecognized parameter '{k}' for operation '{self.operation_id}'")

        return validated


class OfficeOperationRegistry:
    """
    Registry of all verified, safe Office automation operations.
    """

    def __init__(self):
        self._operations: Dict[str, OperationDef] = {}
        self._register_default_operations()

    def _register_default_operations(self) -> None:
        # --- Word Operations ---
        self.register(OperationDef(
            operation_id="word.insert_text",
            app_type=OfficeAppType.WORD,
            description="Insert text at the current selection or document end",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "text": ParamDef("text", str, required=True, description="Text to insert"),
                "location": ParamDef("location", str, required=False, default="end", allowed_values=["end", "selection", "start"], description="Where to insert text"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="word.insert_heading",
            app_type=OfficeAppType.WORD,
            description="Insert a heading with specified level",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "text": ParamDef("text", str, required=True, description="Heading text"),
                "level": ParamDef("level", int, required=False, default=1, allowed_values=[1, 2, 3, 4, 5, 6, 7, 8, 9], description="Heading level (1-9)"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="word.apply_style",
            app_type=OfficeAppType.WORD,
            description="Apply a paragraph style or formatting style",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "style_name": ParamDef("style_name", str, required=True, description="Built-in or custom style name"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="word.set_track_changes",
            app_type=OfficeAppType.WORD,
            description="Enable or disable track revisions in active document",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "enabled": ParamDef("enabled", bool, required=True, description="True to enable, False to disable"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="word.save_document",
            app_type=OfficeAppType.WORD,
            description="Save the active document to its current path or new path",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "path": ParamDef("path", str, required=False, default=None, description="Optional target save path"),
            },
            requires_active_document=True,
        ))

        # --- Excel Operations ---
        self.register(OperationDef(
            operation_id="excel.set_cell_value",
            app_type=OfficeAppType.EXCEL,
            description="Set cell value at coordinate address (e.g. A1)",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "cell": ParamDef("cell", str, required=True, description="Cell reference e.g. 'A1' or 'B5'"),
                "value": ParamDef("value", Any, required=True, description="Value to assign"),
                "sheet": ParamDef("sheet", str, required=False, default=None, description="Sheet name (defaults to active)"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="excel.set_cell_formula",
            app_type=OfficeAppType.EXCEL,
            description="Set formula in specified cell",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "cell": ParamDef("cell", str, required=True, description="Cell reference e.g. 'A10'"),
                "formula": ParamDef("formula", str, required=True, description="Formula starting with '=' e.g. '=SUM(A1:A9)'"),
                "sheet": ParamDef("sheet", str, required=False, default=None, description="Sheet name (defaults to active)"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="excel.format_range",
            app_type=OfficeAppType.EXCEL,
            description="Apply font and appearance styling to cell range",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "range_address": ParamDef("range_address", str, required=True, description="Cell or range e.g. 'A1:C1'"),
                "bold": ParamDef("bold", bool, required=False, default=None, description="Bold text"),
                "italic": ParamDef("italic", bool, required=False, default=None, description="Italic text"),
                "font_size": ParamDef("font_size", int, required=False, default=None, description="Font size in pt"),
                "font_name": ParamDef("font_name", str, required=False, default=None, description="Font family name"),
                "color": ParamDef("color", int, required=False, default=None, description="RGB color integer"),
                "sheet": ParamDef("sheet", str, required=False, default=None, description="Sheet name"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="excel.calculate",
            app_type=OfficeAppType.EXCEL,
            description="Recalculate open Excel workbooks",
            risk_level=RiskCategory.READ_ONLY,
            params={},
            requires_active_document=False,
        ))

        self.register(OperationDef(
            operation_id="excel.save_workbook",
            app_type=OfficeAppType.EXCEL,
            description="Save the active workbook",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "path": ParamDef("path", str, required=False, default=None, description="Optional target save path"),
            },
            requires_active_document=True,
        ))

        # --- PowerPoint Operations ---
        self.register(OperationDef(
            operation_id="powerpoint.get_slide_details",
            app_type=OfficeAppType.POWERPOINT,
            description="Retrieve shape count, notes and text summary for a slide",
            risk_level=RiskCategory.READ_ONLY,
            params={
                "slide_index": ParamDef("slide_index", int, required=True, description="1-based slide index"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="powerpoint.insert_slide",
            app_type=OfficeAppType.POWERPOINT,
            description="Insert a new slide into active presentation",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "index": ParamDef("index", int, required=False, default=-1, description="1-based insertion index (-1 for end)"),
                "layout": ParamDef("layout", int, required=False, default=1, description="Slide layout type (1=Title, 2=Text)"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="powerpoint.set_slide_title",
            app_type=OfficeAppType.POWERPOINT,
            description="Set the title shape text of a slide",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "slide_index": ParamDef("slide_index", int, required=True, description="1-based slide index"),
                "title": ParamDef("title", str, required=True, description="New title text"),
            },
            requires_active_document=True,
        ))

        self.register(OperationDef(
            operation_id="powerpoint.save_presentation",
            app_type=OfficeAppType.POWERPOINT,
            description="Save the active presentation",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "path": ParamDef("path", str, required=False, default=None, description="Optional target save path"),
            },
            requires_active_document=True,
        ))

        # --- Outlook Operations ---
        self.register(OperationDef(
            operation_id="outlook.create_draft",
            app_type=OfficeAppType.OUTLOOK,
            description="Draft a new email message in Outlook (never automatically sent)",
            risk_level=RiskCategory.MEDIUM_RISK,
            params={
                "subject": ParamDef("subject", str, required=True, description="Email subject line"),
                "body": ParamDef("body", str, required=True, description="Email body content"),
                "to": ParamDef("to", str, required=False, default="", description="Recipient email address"),
                "cc": ParamDef("cc", str, required=False, default="", description="Carbon-copy recipient"),
                "is_html": ParamDef("is_html", bool, required=False, default=False, description="Whether body is HTML"),
            },
            requires_active_document=False,
        ))

        self.register(OperationDef(
            operation_id="outlook.get_unread_count",
            app_type=OfficeAppType.OUTLOOK,
            description="Get count of unread items in Inbox or specified folder",
            risk_level=RiskCategory.READ_ONLY,
            params={
                "folder_name": ParamDef("folder_name", str, required=False, default="Inbox", description="Outlook folder name"),
            },
            requires_active_document=False,
        ))

        # --- General / Ribbon Operations ---
        self.register(OperationDef(
            operation_id="office.accelerate_ribbon",
            app_type=OfficeAppType.WORD,  # Multi-app handled via caller
            description="Execute verified ribbon shortcut keystrokes with active window focus",
            risk_level=RiskCategory.LOW_RISK,
            params={
                "app_name": ParamDef("app_name", str, required=True, allowed_values=["word", "excel", "powerpoint", "outlook"], description="Target application"),
                "shortcut": ParamDef("shortcut", str, required=True, description="Shortcut ID or key sequence e.g. 'save', 'bold', 'new_slide'"),
            },
            requires_active_document=False,
        ))

    def register(self, op: OperationDef) -> None:
        self._operations[op.operation_id] = op

    def get_operation(self, operation_id: str) -> Optional[OperationDef]:
        return self._operations.get(operation_id)

    def validate_and_normalize(self, operation_id: str, params: Dict[str, Any]) -> tuple[OperationDef, Dict[str, Any]]:
        op = self.get_operation(operation_id)
        if not op:
            raise OfficeSecurityError(
                f"Operation '{operation_id}' is not allowlisted in OfficeOperationRegistry. "
                f"Dynamic code or unverified actions are strictly prohibited."
            )
        clean_params = op.validate_params(params)
        return op, clean_params

    def list_operations(self, app_type: Optional[OfficeAppType] = None) -> List[Dict[str, Any]]:
        results = []
        for op in self._operations.values():
            if app_type is None or op.app_type == app_type:
                results.append({
                    "operation_id": op.operation_id,
                    "app_type": op.app_type.value,
                    "description": op.description,
                    "risk_level": op.risk_level.value,
                    "requires_active_document": op.requires_active_document,
                    "params": {
                        pname: {
                            "type": pdef.param_type.__name__ if pdef.param_type is not Any else "Any",
                            "required": pdef.required,
                            "default": pdef.default,
                            "allowed_values": pdef.allowed_values,
                            "description": pdef.description,
                        }
                        for pname, pdef in op.params.items()
                    }
                })
        return results
