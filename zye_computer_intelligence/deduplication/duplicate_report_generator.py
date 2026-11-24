"""
Duplicate Report Generator.
Renders structured reports in Markdown and JSON formats.
Enforces read-only safety notices and highlights reclaimable storage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from zye_computer_intelligence.deduplication.storage_calculator import format_bytes_human
from zye_computer_intelligence.schemas.duplicate_schemas import DuplicateScanResult


class DuplicateReportGenerator:
    """Generates human-readable Markdown and structured JSON deduplication reports."""

    @classmethod
    def generate_markdown_report(cls, result: DuplicateScanResult) -> str:
        """Renders comprehensive Markdown audit report."""
        lines = [
            f"# ZYE AI — SHA-256 Duplicate File Audit Report",
            f"",
            f"> [!IMPORTANT]",
            f"> **READ-ONLY AUDIT**: ZYE AI never deletes or moves files automatically.",
            f"> Review the duplicate groups and storage estimates below before taking any manual action.",
            f"",
            f"### Scan Overview",
            f"- **Scan ID**: `{result.scan_id}`",
            f"- **Timestamp**: `{result.created_at}`",
            f"- **Scan Directories**: {', '.join(f'`{d}`' for d in result.scan_directories)}",
            f"- **Total Files Scanned**: {result.total_files_scanned:,}",
            f"- **Total Scanned Data**: {format_bytes_human(result.total_bytes_scanned)}",
            f"- **Duplicate Groups Found**: {result.duplicate_groups_count}",
            f"- **Total Redundant Copies**: {result.duplicate_files_count}",
            f"- **Potential Reclaimable Storage**: **{format_bytes_human(result.potential_reclaimable_bytes)}**",
            f"- **Scan Duration**: {result.duration_ms:.2f} ms",
            f"",
        ]

        if not result.groups:
            lines.extend([
                f"### Duplicate Groups",
                f"",
                f"*No duplicate files were detected in the scanned directories.*",
                f"",
            ])
        else:
            lines.extend([
                f"### Duplicate File Groups ({len(result.groups)} groups)",
                f"",
            ])

            for idx, grp in enumerate(result.groups, 1):
                lines.extend([
                    f"#### Group {idx}: {grp.file_count} copies ({format_bytes_human(grp.file_size_bytes)} each)",
                    f"- **SHA-256**: `{grp.sha256}`",
                    f"- **Type**: `{grp.duplicate_type.value}`",
                    f"- **Verification**: `{grp.verification_status.value}`",
                    f"- **Reclaimable Space**: `{format_bytes_human(grp.potential_reclaimable_bytes)}`",
                    f"- **Identified Files**:",
                ])
                for f_info in grp.files:
                    link_note = " *(Hard Link)*" if f_info.is_hard_link else ""
                    lines.append(f"  - `{f_info.path}`{link_note}")
                lines.append("")

        if result.unreadable_files:
            lines.extend([
                f"### Inaccessible or Skipped Files ({len(result.unreadable_files)})",
                f"",
            ])
            for u in result.unreadable_files[:30]:
                lines.append(f"- `{u}`")
            if len(result.unreadable_files) > 30:
                lines.append(f"- *...and {len(result.unreadable_files) - 30} more.*")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def generate_json_report(cls, result: DuplicateScanResult) -> str:
        """Renders full structured JSON string."""
        return result.model_dump_json(indent=2)
