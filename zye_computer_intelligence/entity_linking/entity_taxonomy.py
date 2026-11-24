"""
Entity Taxonomy and Classification Definitions.
Defines 9 supported entity categories, taxonomies, keywords, and patterns:
PERSON, ORGANIZATION, PROJECT, PRODUCT, LOCATION, TECHNICAL_ENTITY,
IDENTIFIER, CONTACT_INFO, TEMPORAL_ENTITY.
"""

from __future__ import annotations

import re
from typing import Dict, List, Pattern, Set

from zye_computer_intelligence.schemas.entity_schemas import EntityType

# Common organizational suffixes
ORG_SUFFIXES = {
    "inc", "inc.", "corp", "corp.", "corporation", "ltd", "ltd.", "limited",
    "llc", "pvt", "pvt.", "private limited", "gmbh", "technologies", "tech",
    "solutions", "group", "holdings", "systems", "foundation", "institute",
    "university", "labs", "laboratories", "co", "co.", "company"
}

# Known Technical Entities (languages, frameworks, DBs, protocols)
KNOWN_TECH_ENTITIES: Set[str] = {
    "python", "javascript", "typescript", "rust", "golang", "c++", "c#", "java",
    "duckdb", "sqlite", "postgresql", "mysql", "mongodb", "redis", "pandas",
    "numpy", "scipy", "sympy", "fastmcp", "fastapi", "flask", "django", "pydantic",
    "react", "angular", "vue", "next.js", "docker", "kubernetes", "git", "linux",
    "windows", "gemini", "gemini live", "openai", "claude", "azure", "aws", "gcp"
}

# Regex patterns for deterministic extraction
REGEX_EMAIL: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
)

REGEX_PHONE: Pattern[str] = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

REGEX_URL: Pattern[str] = re.compile(
    r"\bhttps?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?\b"
)

REGEX_UUID: Pattern[str] = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

REGEX_GIT_HASH: Pattern[str] = re.compile(
    r"\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{7,8}\b"
)

REGEX_PROJECT_ID: Pattern[str] = re.compile(
    r"\b(?:PROJECT|PROJ|TASK|ISSUE|PRJ)[-_][A-Z0-9]{2,10}\b", re.IGNORECASE
)

REGEX_ISO_DATE: Pattern[str] = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?\b"
)

REGEX_DATE_READABLE: Pattern[str] = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s+\d{4})?\b",
    re.IGNORECASE,
)

REGEX_QUARTER: Pattern[str] = re.compile(
    r"\bQ[1-4][-_ ]?(?:20\d{2}|\d{2})\b|\b(?:20\d{2}|\d{2})[-_ ]?Q[1-4]\b", re.IGNORECASE
)

# Honorifics indicating PERSON entity
PERSON_HONORIFICS = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", "prof", "prof.",
    "sir", "madam", "shri", "smt", "er", "er."
}

# Common Tamil and South Asian name prefixes / titles
TAMIL_TITLES = {"திரு", "திருமதி", "செல்வி", "மருத்துவர்", "பேராசிரியர்"}
