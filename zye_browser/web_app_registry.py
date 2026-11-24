"""
Web Application Registry — Day 24.
Loads and caches configuration for known web applications (Gmail, Drive, YouTube, Calendar, Search).
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ZyeWebAppRegistry")


class WebAppRegistry:
    """Provides configuration and selector maps for supported web applications."""

    DEFAULT_CONFIG_PATH = Path("configs/web_apps.toml")

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._apps: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load web apps configuration from TOML file."""
        if not self.config_path.exists():
            # Built-in fallback
            self._apps = {
                "gmail": {
                    "domain": "mail.google.com",
                    "search_selector": "input[aria-label*='Search']",
                    "read_only": True,
                },
                "google_drive": {
                    "domain": "drive.google.com",
                    "search_selector": "input[aria-label*='Search']",
                    "read_only": True,
                },
                "youtube": {
                    "domain": "youtube.com",
                    "search_selector": "input[name='search_query']",
                    "read_only": True,
                },
            }
            return

        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            self._apps = data.get("apps", {})
        except Exception as exc:
            logger.error("Failed to load web_apps.toml: %s", exc)
            self._apps = {}

    def get_app(self, app_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration for app by key (e.g. 'gmail', 'google_drive')."""
        return self._apps.get(app_key.lower())

    def list_apps(self) -> List[str]:
        """Return list of supported app keys."""
        return list(self._apps.keys())

    def get_app_for_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Find app configuration matching domain."""
        clean_domain = domain.lower()
        for key, conf in self._apps.items():
            conf_domain = conf.get("domain", "").lower()
            if conf_domain and (conf_domain in clean_domain or clean_domain in conf_domain):
                return {"key": key, **conf}
        return None
