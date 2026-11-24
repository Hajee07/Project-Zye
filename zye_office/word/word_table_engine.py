"""
Advanced Microsoft Word Table Engine — Zye Day 21.
Handles creation, matrix data population, cell manipulation, row/column expansion,
borders, shading, and header repetition across page boundaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_constants import (
    WD_ALIGN_PARAGRAPH_CENTER,
    WD_ALIGN_VERTICAL_CENTER,
    WD_AUTOFIT_CONTENT,
    WD_AUTOFIT_FIXED,
    WD_AUTOFIT_WINDOW,
    WD_COLOR_BLUE,
    WD_COLOR_GRAY,
)
from zye_office.word.word_errors import (
    WordInvalidRangeError,
    WordInvalidTableError,
    WordNoActiveDocumentError,
)
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.tables")

# Predefined table appearance presets
TABLE_STYLE_PRESETS = {
    "PROFESSIONAL_BLUE": {
        "header_bg": 16711680,  # Deep blue
        "header_font_bold": True,
        "header_color": 16777215,  # White
        "repeat_header": True,
        "autofit": WD_AUTOFIT_WINDOW,
    },
    "PROFESSIONAL_GRAY": {
        "header_bg": 8421504,  # Gray
        "header_font_bold": True,
        "header_color": 16777215,
        "repeat_header": True,
        "autofit": WD_AUTOFIT_WINDOW,
    },
    "MINIMAL": {
        "header_bg": None,
        "header_font_bold": True,
        "repeat_header": True,
        "autofit": WD_AUTOFIT_CONTENT,
    },
}


class WordTableEngine:
    """Enterprise table generation, matrix population, styling and layout engine."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def create_word_table(
        self,
        rows: int,
        columns: int,
        autofit: str = "window",
        data: Optional[List[List[Any]]] = None,
        style_preset: Optional[str] = None,
        style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a table in the active document and optionally populates and styles it."""
        self.validator.validate_table_dimensions(rows, columns)
        chosen_style = style or style_preset

        def _sta_create_table() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = app.Selection.Range
            tbl = doc.Tables.Add(Range=rng, NumRows=rows, NumColumns=columns)

            # AutoFit behavior
            fit_mode = WD_AUTOFIT_WINDOW if autofit == "window" else WD_AUTOFIT_CONTENT
            try:
                tbl.AutoFitBehavior(fit_mode)
            except Exception:
                pass

            table_id = tbl.TableIndex if hasattr(tbl, "TableIndex") else doc.Tables.Count

            # Populate data if provided
            if data:
                for r_idx, row_vals in enumerate(data[:rows]):
                    for c_idx, val in enumerate(row_vals[:columns]):
                        clean_val = self.validator.validate_unicode_text(str(val))
                        cell = tbl.Cell(r_idx + 1, c_idx + 1)
                        cell.Range.Text = clean_val

            # Format headers
            if style_preset and style_preset.upper() in TABLE_STYLE_PRESETS:
                cfg = TABLE_STYLE_PRESETS[style_preset.upper()]
                hdr_row = tbl.Rows(1)
                if cfg.get("repeat_header"):
                    hdr_row.HeadingFormat = True
                if cfg.get("header_bg"):
                    hdr_row.Shading.BackgroundPatternColor = cfg["header_bg"]
                if cfg.get("header_color"):
                    hdr_row.Range.Font.Color = cfg["header_color"]
                if cfg.get("header_font_bold"):
                    hdr_row.Range.Font.Bold = True

            return {
                "status": "SUCCESS",
                "table_id": table_id,
                "rows": rows,
                "columns": columns,
                "autofit": autofit,
                "populated_rows": len(data) if data else 0,
                "message": f"Table ({rows}x{columns}) created successfully (Table ID: {table_id}).",
            }

        return self.adapter.worker.run(_sta_create_table)

    def populate_word_table(self, table_id: int, data: List[List[Any]]) -> Dict[str, Any]:
        """Bulk populates an existing table with 2D matrix data."""
        def _sta_populate() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if table_id < 1 or table_id > doc.Tables.Count:
                raise WordInvalidTableError(f"Table index {table_id} does not exist (Document has {doc.Tables.Count} tables).")

            tbl = doc.Tables(table_id)
            try:
                total_rows = int(tbl.Rows.Count)
                total_cols = int(tbl.Columns.Count)
            except Exception:
                total_rows = 1000
                total_cols = 100

            cells_written = 0
            for r_idx, row_vals in enumerate(data):
                if r_idx + 1 > total_rows:
                    break
                for c_idx, val in enumerate(row_vals):
                    if c_idx + 1 > total_cols:
                        break
                    clean_val = self.validator.validate_unicode_text(str(val))
                    tbl.Cell(r_idx + 1, c_idx + 1).Range.Text = clean_val
                    cells_written += 1

            return {
                "status": "SUCCESS",
                "table_id": table_id,
                "cells_written": cells_written,
                "message": f"Populated {cells_written} cells in Table {table_id}.",
            }

        return self.adapter.worker.run(_sta_populate)

    def set_table_cell_value(self, table_id: int, row: int, column: int, value: Any) -> Dict[str, Any]:
        """Assign value to an exact 1-based table coordinate."""
        clean_val = self.validator.validate_unicode_text(str(value))

        def _sta_set_cell() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if table_id < 1 or table_id > doc.Tables.Count:
                raise WordInvalidTableError(f"Table index {table_id} does not exist.")

            tbl = doc.Tables(table_id)
            if row < 1 or row > tbl.Rows.Count or column < 1 or column > tbl.Columns.Count:
                raise WordInvalidRangeError(f"Coordinate ({row}, {column}) out of table bounds ({tbl.Rows.Count}x{tbl.Columns.Count}).")

            tbl.Cell(row, column).Range.Text = clean_val
            return {
                "status": "SUCCESS",
                "table_id": table_id,
                "row": row,
                "column": column,
                "value": clean_val,
            }

        return self.adapter.worker.run(_sta_set_cell)

    def add_table_row(self, table_id: int) -> Dict[str, Any]:
        """Appends a new row to the end of specified table."""
        def _sta_add_row() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if table_id < 1 or table_id > doc.Tables.Count:
                raise WordInvalidTableError(f"Table index {table_id} does not exist.")

            tbl = doc.Tables(table_id)
            tbl.Rows.Add()
            return {
                "status": "SUCCESS",
                "table_id": table_id,
                "total_rows": tbl.Rows.Count,
                "message": f"Added row. Total rows now {tbl.Rows.Count}.",
            }

        return self.adapter.worker.run(_sta_add_row)

    def delete_table_row(self, table_id: int, row_index: int) -> Dict[str, Any]:
        """Deletes a 1-based row index from specified table."""
        def _sta_del_row() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            if table_id < 1 or table_id > doc.Tables.Count:
                raise WordInvalidTableError(f"Table index {table_id} does not exist.")

            tbl = doc.Tables(table_id)
            if row_index < 1 or row_index > tbl.Rows.Count:
                raise WordInvalidRangeError(f"Row {row_index} out of table bounds (1..{tbl.Rows.Count}).")

            tbl.Rows(row_index).Delete()
            return {
                "status": "SUCCESS",
                "table_id": table_id,
                "remaining_rows": tbl.Rows.Count,
                "message": f"Deleted row {row_index}.",
            }

        return self.adapter.worker.run(_sta_del_row)

    create_table = create_word_table
    populate_table = populate_word_table
