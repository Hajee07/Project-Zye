"""
Publisher Identity & Ownership Registry (Day 38 / Phase 3).
Maps domains, display names, and subsidiaries to canonical publisher entities and ownership groups.
Identifies wire services, commercial press distribution networks, and affiliated media outlets.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


# Primary Global & Regional News Wire Services
WIRE_SERVICES: Dict[str, str] = {
    "reuters": "Reuters",
    "reuters.com": "Reuters",
    "thomson reuters": "Reuters",
    "ap": "Associated Press",
    "apnews.com": "Associated Press",
    "associated press": "Associated Press",
    "afp": "Agence France-Presse",
    "afp.com": "Agence France-Presse",
    "pti": "Press Trust of India",
    "ptinews.com": "Press Trust of India",
    "press trust of india": "Press Trust of India",
    "bloomberg": "Bloomberg News",
    "bloomberg.com": "Bloomberg News",
    "upi": "United Press International",
    "upi.com": "United Press International",
    "pr newswire": "PR Newswire",
    "prnewswire.com": "PR Newswire",
    "business wire": "Business Wire",
    "businesswire.com": "Business Wire",
    "globenewswire": "GlobeNewswire",
    "globenewswire.com": "GlobeNewswire",
    "ani": "Asian News International",
    "aninews.in": "Asian News International",
}

# Major Media Ownership Groups & Domain Aliases
PUBLISHER_OWNERSHIP_GROUPS: Dict[str, Set[str]] = {
    "THOMSON_REUTERS": {
        "reuters.com",
        "reutersagency.com",
        "reuters.tv",
    },
    "ASSOCIATED_PRESS": {
        "apnews.com",
        "ap.org",
    },
    "BBC_GROUP": {
        "bbc.com",
        "bbc.co.uk",
        "bbcgoodfood.com",
    },
    "WARNER_BROS_DISCOVERY": {
        "cnn.com",
        "bleacherreport.com",
        "hlntv.com",
    },
    "NEW_YORK_TIMES_COMPANY": {
        "nytimes.com",
        "theathletic.com",
    },
    "NEWS_CORP": {
        "wsj.com",
        "barrons.com",
        "marketwatch.com",
        "nypost.com",
        "thesun.co.uk",
        "thetimes.co.uk",
    },
    "TIMES_GROUP_BCCL": {
        "indiatimes.com",
        "timesofindia.indiatimes.com",
        "economictimes.indiatimes.com",
        "navbharattimes.indiatimes.com",
    },
    "THE_HINDU_GROUP": {
        "thehindu.com",
        "thehindubusinessline.com",
        "frontline.thehindu.com",
        "sportstar.thehindu.com",
    },
    "EXPRESS_GROUP": {
        "indianexpress.com",
        "financialexpress.com",
        "loksatta.com",
    },
    "NDTV_GROUP": {
        "ndtv.com",
        "ndtvprofit.com",
        "gadgets360.com",
    },
    "VOX_MEDIA": {
        "theverge.com",
        "vox.com",
        "polygon.com",
        "eater.com",
    },
    "YAHOO_INC": {
        "yahoo.com",
        "techcrunch.com",
        "engadget.com",
    },
    "AXEL_SPRINGER": {
        "politico.com",
        "businessinsider.com",
        "insider.com",
        "bild.de",
    },
    "GUARDIAN_MEDIA_GROUP": {
        "theguardian.com",
    },
}


class PublisherRegistry:
    """Resolves canonical publisher identities, corporate affiliations, and wire networks."""

    _instance: Optional[PublisherRegistry] = None

    def __init__(self, custom_registry: Optional[Dict[str, List[str]]] = None) -> None:
        self._groups: Dict[str, Set[str]] = dict(PUBLISHER_OWNERSHIP_GROUPS)
        if custom_registry:
            for group, aliases in custom_registry.items():
                if group in self._groups:
                    self._groups[group].update(a.lower().strip() for a in aliases)
                else:
                    self._groups[group] = set(a.lower().strip() for a in aliases)

    @classmethod
    def get_instance(cls) -> PublisherRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def resolve_publisher_group(self, canonical_domain: str, source_name: str = "") -> str:
        """
        Determines the corporate ownership or brand group for a given domain or display name.
        Returns the canonical group name (e.g. 'WARNER_BROS_DISCOVERY' or canonical domain).
        """
        d = canonical_domain.lower().strip()
        s = source_name.lower().strip()

        # Check domain membership across groups
        for group, domains in self._groups.items():
            if d in domains:
                return group
            # Check subdomain matches (e.g. edition.cnn.com belongs to cnn.com)
            for registered_d in domains:
                if d.endswith(f".{registered_d}") or registered_d.endswith(f".{d}"):
                    return group

        # Wire service checks
        wire = self.get_wire_service_name(s, d)
        if wire:
            return f"WIRE_{wire.upper().replace(' ', '_')}"

        return d if d else (s if s else "UNKNOWN_PUBLISHER")

    def are_publishers_affiliated(self, group_a: str, group_b: str) -> bool:
        """Checks if two publisher groups represent the exact same media parent entity."""
        if not group_a or not group_b:
            return False
        if group_a == "UNKNOWN_PUBLISHER" or group_b == "UNKNOWN_PUBLISHER":
            return False
        return group_a.upper().strip() == group_b.upper().strip()

    def are_independent_publishers(self, domain_a: str, domain_b: str) -> bool:
        """Returns True if two domains belong to distinct, non-affiliated media owners."""
        grp_a = self.resolve_publisher_group(domain_a)
        grp_b = self.resolve_publisher_group(domain_b)
        return not self.are_publishers_affiliated(grp_a, grp_b)

    def is_wire_agency(self, domain_or_name: str) -> bool:
        """Returns True if the domain or display name represents a syndicated news wire service."""
        return self.get_wire_service_name(domain_or_name, domain_or_name) is not None

    @staticmethod
    def get_wire_service_name(source_name: str, domain: str = "") -> Optional[str]:
        """Detects whether a source name or domain represents a syndicated wire agency."""
        s = source_name.lower().strip()
        d = domain.lower().strip()

        if s in WIRE_SERVICES:
            return WIRE_SERVICES[s]
        if d in WIRE_SERVICES:
            return WIRE_SERVICES[d]

        # Substring keyword check in display name
        for k, v in WIRE_SERVICES.items():
            if " " in k or len(k) >= 3:
                if k in s:
                    return v
        return None
