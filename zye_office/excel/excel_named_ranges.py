"""
Named Range Engine for Microsoft Excel — Zye Day 22.
Creates, queries, updates, and deletes workbook and worksheet-level named ranges.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from zye_office.excel.excel_adapter import ExcelAdapter
from zye_office.excel.excel_errors import (
    ExcelNoActiveWorkbookError,
    ExcelSecurityError,
)
from zye_office.excel.excel_validator import ExcelValidator

logger = logging.getLogger("zye.office.excel.named_ranges")

NAME_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\u0B80-\u0BFF]{0,254}$")


class ExcelNamedRangeEngine:
    """Manages Excel Names collection."""

    def __init__(
        self,
        adapter: Optional[ExcelAdapter] = None,
        validator: Optional[ExcelValidator] = None,
    ) -> None:
        self.adapter = adapter or ExcelAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or ExcelValidator()

    def create_named_range(self, name: str, range_address: str) -> Dict[str, Any]:
        """Create a new workbook-level named range."""
        clean_name = name.strip()
        if not NAME_REGEX.match(clean_name):
            raise ExcelSecurityError(
                f"Named range '{clean_name}' is invalid. Names must start with a letter or underscore and contain no spaces.",
                error_code="EXCEL_NAME_SYNTAX_INVALID",
            )
        valid_range = self.validator.validate_range_address(range_address)

        def _sta_create_name() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            ws = self.adapter.get_active_worksheet_raw()
            rng = ws.Range(valid_range)
            # RefersTo = "=" & Range.Address(External=True)
            refers_to = f"={rng.Address(External=True)}"
            wb.Names.Add(Name=clean_name, RefersTo=refers_to)

            return {
                "status": "SUCCESS",
                "name": clean_name,
                "refers_to": refers_to,
                "range": rng.Address,
            }

        return self.worker.run(_sta_create_name)

    def get_named_ranges(self) -> Dict[str, Any]:
        """List all defined named ranges in active workbook."""
        def _sta_get_names() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            names_list = []
            for n in wb.Names:
                try:
                    names_list.append({
                        "name": n.Name,
                        "refers_to": getattr(n, "RefersTo", None),
                        "visible": getattr(n, "Visible", True),
                    })
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "total_names": len(names_list),
                "names": names_list,
            }

        return self.worker.run(_sta_get_names)

    def delete_named_range(self, name: str) -> Dict[str, Any]:
        """Delete an existing named range."""
        clean_name = name.strip()

        def _sta_del_name() -> Dict[str, Any]:
            wb = self.adapter.get_active_workbook_raw()
            if wb is None:
                raise ExcelNoActiveWorkbookError()

            target_name = None
            for n in wb.Names:
                if n.Name.lower() == clean_name.lower():
                    target_name = n
                    break

            if target_name is None:
                raise ExcelSecurityError(f"Named range '{clean_name}' not found.")

            target_name.Delete()
            return {
                "status": "SUCCESS",
                "deleted_name": clean_name,
            }

        return self.worker.run(_sta_del_name)
