"""
Zye Office Capability Registry
Defines supported Office automation capabilities, version requirements,
and feature matrix per application.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import os
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from zye_office.models import OfficeAppType


@dataclass
class CapabilityDef:
    name: str
    description: str
    min_version: str = "12.0"  # Office 2007+
    requires_active_document: bool = True
    supported_apps: List[OfficeAppType] = field(default_factory=list)
    risk_level: str = "READ_ONLY"


class OfficeCapabilityRegistry:
    """
    Maintains and queries the matrix of supported capabilities across
    Office applications.
    """

    DEFAULT_CAPABILITIES = {
        "com_bridge": CapabilityDef(
            name="com_bridge",
            description="Live COM runtime connection via STA worker thread",
            min_version="11.0",
            requires_active_document=False,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT, OfficeAppType.OUTLOOK],
            risk_level="READ_ONLY",
        ),
        "document_inspection": CapabilityDef(
            name="document_inspection",
            description="Inspect active document structure, word count, sheets, slides, or folders",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT, OfficeAppType.OUTLOOK],
            risk_level="READ_ONLY",
        ),
        "content_modification": CapabilityDef(
            name="content_modification",
            description="Insert text, headings, or content into active documents",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT],
            risk_level="LOW_RISK",
        ),
        "formatting": CapabilityDef(
            name="formatting",
            description="Apply styles, fonts, cell formatting or alignment",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT],
            risk_level="LOW_RISK",
        ),
        "formula_manipulation": CapabilityDef(
            name="formula_manipulation",
            description="Read and write cell formulas and calculate workbooks",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.EXCEL],
            risk_level="LOW_RISK",
        ),
        "slide_operations": CapabilityDef(
            name="slide_operations",
            description="Insert slides, modify slide titles, inspect shapes",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.POWERPOINT],
            risk_level="LOW_RISK",
        ),
        "email_drafting": CapabilityDef(
            name="email_drafting",
            description="Create draft emails in Outlook without sending",
            min_version="12.0",
            requires_active_document=False,
            supported_apps=[OfficeAppType.OUTLOOK],
            risk_level="MEDIUM_RISK",
        ),
        "pdf_export": CapabilityDef(
            name="pdf_export",
            description="Export active document, workbook or presentation directly to PDF via COM",
            min_version="12.0",
            requires_active_document=True,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT],
            risk_level="LOW_RISK",
        ),
        "ribbon_accelerator": CapabilityDef(
            name="ribbon_accelerator",
            description="Trigger menu and ribbon shortcut key sequences with foreground verification",
            min_version="12.0",
            requires_active_document=False,
            supported_apps=[OfficeAppType.WORD, OfficeAppType.EXCEL, OfficeAppType.POWERPOINT, OfficeAppType.OUTLOOK],
            risk_level="LOW_RISK",
        ),
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join("configs", "office_capabilities.toml")
        self._capabilities: Dict[str, CapabilityDef] = dict(self.DEFAULT_CAPABILITIES)
        self._load_config()

    def _load_config(self) -> None:
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            caps = data.get("capabilities", {})
            for name, details in caps.items():
                app_names = details.get("supported_apps", [])
                apps = []
                for a in app_names:
                    try:
                        apps.append(OfficeAppType(a.lower()))
                    except ValueError:
                        pass
                self._capabilities[name] = CapabilityDef(
                    name=name,
                    description=details.get("description", ""),
                    min_version=details.get("min_version", "12.0"),
                    requires_active_document=details.get("requires_active_document", True),
                    supported_apps=apps,
                    risk_level=details.get("risk_level", "LOW_RISK"),
                )
        except Exception as e:
            sys.stderr.write(f"[OfficeCapabilityRegistry] Error loading {self.config_path}: {e}\n")

    def get_capability(self, name: str) -> Optional[CapabilityDef]:
        return self._capabilities.get(name)

    def is_supported(self, app_type: OfficeAppType, capability_name: str) -> bool:
        cap = self.get_capability(capability_name)
        if not cap:
            return False
        return app_type in cap.supported_apps

    def list_capabilities_for_app(self, app_type: OfficeAppType) -> List[Dict[str, Any]]:
        results = []
        for name, cap in self._capabilities.items():
            if app_type in cap.supported_apps:
                results.append({
                    "name": cap.name,
                    "description": cap.description,
                    "min_version": cap.min_version,
                    "requires_active_document": cap.requires_active_document,
                    "risk_level": cap.risk_level,
                })
        return results

    def get_all_capabilities(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "name": cap.name,
                "description": cap.description,
                "min_version": cap.min_version,
                "requires_active_document": cap.requires_active_document,
                "supported_apps": [a.value for a in cap.supported_apps],
                "risk_level": cap.risk_level,
            }
            for name, cap in self._capabilities.items()
        }
