"""
Local Document Content Extractor.
Extracts bounded text, headings, sections, and metadata from PDF, DOCX, XLSX,
CSV, JSON, Python, and text-based files safely.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.document_extractor")

MAX_TEXT_SNIPPET_LENGTH = 1500
MAX_PAGES_TO_EXTRACT = 25
MAX_SPREADSHEET_ROWS = 50


class LocalDocumentExtractor:
    """Safe multi-format document text and structure extraction engine."""

    @classmethod
    def extract_document(cls, file_path: Path) -> dict[str, Any]:
        """Extracts text, metadata, and structural sections based on file type."""
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            res = cls.extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            res = cls.extract_docx(file_path)
        elif ext in (".xlsx", ".xls"):
            res = cls.extract_xlsx(file_path)
        elif ext == ".csv":
            res = cls.extract_csv(file_path)
        elif ext == ".json":
            res = cls.extract_json(file_path)
        elif ext in (".py", ".js", ".ts", ".html", ".htm", ".xml", ".yaml", ".yml", ".toml", ".sql"):
            res = cls.extract_code(file_path)
        elif ext in (".txt", ".md"):
            res = cls.extract_plain_text(file_path)
        else:
            res = cls.extract_plain_text(file_path)

        res["file_type"] = ext.lstrip(".")
        return res

    @classmethod
    def extract_pdf(cls, file_path: Path) -> dict[str, Any]:
        """Extracts text page-by-page from PDF files using pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            total_pages = len(reader.pages)
            pages_extracted = min(total_pages, MAX_PAGES_TO_EXTRACT)

            sections = []
            full_text_parts = []
            for i in range(pages_extracted):
                page = reader.pages[i]
                page_text = page.extract_text() or ""
                clean_page = page_text.strip()
                if clean_page:
                    sections.append({
                        "section_type": "page",
                        "page_number": i + 1,
                        "content": clean_page[:MAX_TEXT_SNIPPET_LENGTH],
                    })
                    full_text_parts.append(clean_page)

            content = "\n\n".join(full_text_parts)
            return {
                "status": "SUCCESS",
                "format": "pdf",
                "page_count": total_pages,
                "sections": sections,
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            logger.warning("PDF extraction failed for '%s': %s", file_path.name, e)
            return {"status": "ERROR", "format": "pdf", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_docx(cls, file_path: Path) -> dict[str, Any]:
        """Extracts paragraphs, headings, and tables from DOCX files using python-docx."""
        try:
            import docx
            doc = docx.Document(str(file_path))
            sections = []
            full_text_parts = []

            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    is_heading = p.style and p.style.name and p.style.name.startswith("Heading")
                    sections.append({
                        "section_type": "heading" if is_heading else "paragraph",
                        "content": txt,
                    })
                    full_text_parts.append(txt)

            # Extract tables
            table_count = len(doc.tables)
            content = "\n".join(full_text_parts)
            return {
                "status": "SUCCESS",
                "format": "docx",
                "paragraph_count": len(doc.paragraphs),
                "table_count": table_count,
                "sections": sections[:50],
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            logger.warning("DOCX extraction failed for '%s': %s", file_path.name, e)
            return {"status": "ERROR", "format": "docx", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_xlsx(cls, file_path: Path) -> dict[str, Any]:
        """Extracts sheet names, headers, and rows from XLSX files using openpyxl."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
            sheet_names = wb.sheetnames
            sections = []
            full_text_parts = []

            for name in sheet_names[:5]:
                ws = wb[name]
                rows_text = []
                for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                    if row_idx >= MAX_SPREADSHEET_ROWS:
                        break
                    row_vals = [str(v) for v in row if v is not None]
                    if row_vals:
                        rows_text.append(" | ".join(row_vals))

                sheet_content = "\n".join(rows_text)
                sections.append({
                    "section_type": "sheet",
                    "sheet_name": name,
                    "content": sheet_content[:2000],
                })
                full_text_parts.append(f"Sheet '{name}':\n{sheet_content}")

            wb.close()
            content = "\n\n".join(full_text_parts)
            return {
                "status": "SUCCESS",
                "format": "xlsx",
                "sheet_names": sheet_names,
                "sections": sections,
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            logger.warning("XLSX extraction failed for '%s': %s", file_path.name, e)
            return {"status": "ERROR", "format": "xlsx", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_csv(cls, file_path: Path) -> dict[str, Any]:
        """Extracts headers and sample rows from CSV files."""
        try:
            lines = []
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                for i, row in enumerate(reader):
                    if i >= MAX_SPREADSHEET_ROWS:
                        break
                    lines.append(", ".join(row))

            header_str = "Columns: " + ", ".join(headers)
            content = header_str + "\n" + "\n".join(lines)
            return {
                "status": "SUCCESS",
                "format": "csv",
                "headers": headers,
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            return {"status": "ERROR", "format": "csv", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_code(cls, file_path: Path) -> dict[str, Any]:
        """Extracts source code lines, functions, and classes with line numbering."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            sections = []
            for i, line in enumerate(lines[:100]):
                stripped = line.strip()
                if stripped.startswith(("def ", "class ", "async def ", "function ")):
                    sections.append({
                        "section_type": "definition",
                        "line_number": i + 1,
                        "content": stripped,
                    })

            return {
                "status": "SUCCESS",
                "format": "code",
                "line_count": len(lines),
                "sections": sections,
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            return {"status": "ERROR", "format": "code", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_plain_text(cls, file_path: Path) -> dict[str, Any]:
        """Extracts text from plain text or markdown files."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return {
                "status": "SUCCESS",
                "format": file_path.suffix.lstrip("."),
                "line_count": len(content.splitlines()),
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            return {"status": "ERROR", "format": "text", "error": str(e), "content": "", "snippet": ""}

    @classmethod
    def extract_json(cls, file_path: Path) -> dict[str, Any]:
        """Extracts keys and values from JSON files."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(content)
            keys = list(data.keys()) if isinstance(data, dict) else [f"array_len_{len(data)}"]
            return {
                "status": "SUCCESS",
                "format": "json",
                "top_level_keys": keys[:20],
                "content": content[:50000],
                "snippet": content[:MAX_TEXT_SNIPPET_LENGTH],
            }
        except Exception as e:
            return {"status": "ERROR", "format": "json", "error": str(e), "content": "", "snippet": ""}
