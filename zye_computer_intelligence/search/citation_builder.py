"""
Source Citation Builder.
Constructs traceable citations for local documents (file path, line, section)
and web sources (verified URL, domain, title), formatted for Markdown and voice.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.citation_builder")


class CitationBuilder:
    """Builds clean, traceable citations for Gemini Live voice and Markdown UI."""

    @classmethod
    def build_citations(cls, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Constructs structured citation entries for each search result."""
        citations = []
        for idx, res in enumerate(results):
            cid = f"[{idx + 1}]"
            source_type = res.get("source_type", "unknown")
            title = res.get("title", "Untitled Source")

            if source_type == "local":
                fpath = res.get("file_path", "")
                fname = res.get("file_name", "")
                entry = {
                    "citation_marker": cid,
                    "citation_id": res.get("citation_id", f"local_{idx+1}"),
                    "source_type": "local",
                    "title": title,
                    "location": fpath,
                    "file_name": fname,
                    "text_reference": f"{cid} Local file: '{fname}' ({fpath})",
                }
            else:
                url = res.get("url", "")
                domain = res.get("domain", "")
                entry = {
                    "citation_marker": cid,
                    "citation_id": res.get("citation_id", f"web_{idx+1}"),
                    "source_type": "web",
                    "title": title,
                    "location": url,
                    "domain": domain,
                    "text_reference": f"{cid} Web: '{title}' ({url})",
                }
            citations.append(entry)
        return citations

    @classmethod
    def format_markdown_citations(cls, citations: list[dict[str, Any]]) -> str:
        """Formats citation list into clean GitHub-flavored markdown."""
        if not citations:
            return ""

        lines = ["\n### Sources & Citations"]
        for c in citations:
            marker = c["citation_marker"]
            title = c["title"]
            loc = c["location"]
            if c["source_type"] == "local":
                lines.append(f"- **{marker}** `{c.get('file_name', title)}` — `{loc}`")
            else:
                lines.append(f"- **{marker}** [{title}]({loc}) — `{c.get('domain', '')}`")

        return "\n".join(lines)

    @classmethod
    def format_voice_citations(cls, citations: list[dict[str, Any]], max_sources: int = 3) -> tuple[str, str]:
        """Generates concise bilingual Tanglish and English citations for Gemini Live speech."""
        if not citations:
            return "Sources edhuvum kidaikkala.", "No sources were found."

        top = citations[:max_sources]
        local_count = sum(1 for c in citations if c["source_type"] == "local")
        web_count = sum(1 for c in citations if c["source_type"] == "web")

        names = [c.get("file_name") or c.get("domain") or c.get("title", "") for c in top]
        src_list_str = ", ".join(filter(None, names))

        tanglish = f"Idhuku {len(citations)} sources irukku ({local_count} local, {web_count} web). Mukkiyamana sources: {src_list_str}."
        english = f"Found {len(citations)} sources ({local_count} local, {web_count} web). Key references include: {src_list_str}."

        return tanglish, english
