"""
Secure Application Name Resolver (Zye Reliability Engineering).
Resolves colloquial names and aliases to verified AppInfo instances across
Win32, Windows Store (UWP), and Start Menu inventories with ambiguity protection.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from zye_windows.app_discovery import WindowsAppDiscovery
from zye_windows.windows_models import AppInfo, InstallationType

logger = logging.getLogger("zye.windows.application_resolver")

COMMON_ALIASES: Dict[str, str] = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "calc": "Calculator",
    "calculator": "Calculator",
    "whatsapp": "WhatsApp",
    "whatsapp desktop": "WhatsApp",
    "code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "notepad": "Notepad",
    "word": "Microsoft Word",
    "ms word": "Microsoft Word",
    "winword": "Microsoft Word",
    "excel": "Microsoft Excel",
    "ms excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "ms powerpoint": "Microsoft PowerPoint",
    "ppt": "Microsoft PowerPoint",
    "outlook": "Outlook",
    "ms outlook": "Outlook",
    "edge": "Microsoft Edge",
    "msedge": "Microsoft Edge",
    "microsoft edge": "Microsoft Edge",
    "terminal": "Windows Terminal",
    "cmd": "Command Prompt",
    "powershell": "Windows PowerShell",
    "vlc": "VLC media player",
    "spotify": "Spotify",
    "explorer": "File Explorer",
    "files": "File Explorer",
    "settings": "Settings",
    "control panel": "Control Panel",
}


class ApplicationResolver:
    """Discovers and resolves application identifiers safely without shell injection."""

    def __init__(self, discovery: Optional[WindowsAppDiscovery] = None) -> None:
        self.discovery = discovery or WindowsAppDiscovery()

    def resolve(self, query: str) -> Tuple[str, Optional[AppInfo], List[str]]:
        """
        Resolves a user-provided application query string.
        Returns:
            (status, resolved_app_or_None, candidate_names_list)
        Statuses:
            - EXACT_MATCH: Single unambiguous target found
            - ALIAS_MATCH: Matched a verified well-known alias
            - AMBIGUOUS_MATCH: Multiple candidates match query
            - NOT_FOUND: No registered or discovered application matches
        """
        if not query or not str(query).strip():
            return "NOT_FOUND", None, []

        clean_query = str(query).strip()
        lower_query = clean_query.lower()

        # Sanitize query: forbid shell metacharacters
        clean_query = re.sub(r"[;&|`$<>()\n\r]", "", clean_query).strip()
        if not clean_query:
            return "NOT_FOUND", None, []

        # 1. Alias lookup
        if lower_query in COMMON_ALIASES:
            canonical_name = COMMON_ALIASES[lower_query]
            matches = self.discovery.search_installed_apps(canonical_name)
            if matches:
                # Prefer exact match by canonical name
                for m in matches:
                    if m.application_name.lower() == canonical_name.lower():
                        return "ALIAS_MATCH", m, []
                return "ALIAS_MATCH", matches[0], []
            else:
                # Construct fallback AppInfo for verified alias
                fallback = AppInfo(
                    application_name=canonical_name,
                    app_id=canonical_name,
                    installation_type=InstallationType.UNKNOWN,
                    available=True,
                )
                return "ALIAS_MATCH", fallback, []

        # 2. Search installed applications inventory
        matches = self.discovery.search_installed_apps(clean_query)
        if not matches:
            return "NOT_FOUND", None, []

        # 3. Check for exact matches
        exact_matches = [
            m for m in matches
            if m.application_name.lower() == lower_query or (m.app_id and m.app_id.lower() == lower_query)
        ]
        if len(exact_matches) == 1:
            return "EXACT_MATCH", exact_matches[0], []

        # 4. Check for prefix matches
        prefix_matches = [
            m for m in matches
            if m.application_name.lower().startswith(lower_query)
        ]
        if len(prefix_matches) == 1:
            return "EXACT_MATCH", prefix_matches[0], []

        if len(matches) == 1:
            return "EXACT_MATCH", matches[0], []

        # 5. Ambiguous: multiple possibilities
        candidates = [f"{m.application_name} (AppID: {m.app_id})" for m in matches[:6]]
        return "AMBIGUOUS_MATCH", None, candidates
