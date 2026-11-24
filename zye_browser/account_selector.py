"""
Voice-Friendly Account Disambiguation Engine — Day 24.
Resolves browser profiles using Tamil, English, and Tanglish voice commands or text aliases.
"""

from __future__ import annotations

import difflib
import re
from typing import List, Optional

from zye_browser.browser_errors import BrowserAccountAmbiguousError, BrowserAccountSelectionRequiredError
from zye_browser.models import BrowserAccountSelection, BrowserProfileMetadata
from zye_browser.profile_registry import ProfileRegistry


class AccountSelector:
    """Matches user voice or text input to a specific browser profile."""

    def __init__(self, registry: ProfileRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        query: Optional[str] = None,
        account_type: Optional[str] = None,
        require_exact: bool = False,
    ) -> BrowserAccountSelection:
        """
        Disambiguate and select the best matching browser profile.
        If query is empty and only 1 profile exists, returns that profile.
        If query is empty and multiple exist, prompts user for selection.
        """
        profiles = self.registry.list_profiles()
        if not profiles:
            return BrowserAccountSelection(
                matched=False,
                candidates=[],
                match_strategy="none",
                confidence=0.0,
                selection_prompt="No browser profiles registered in Zye. Register a profile first.",
            )

        # 1. No query provided
        if not query or not query.strip():
            # If an active profile already exists in session, prefer it
            active = self.registry.get_active_profile()
            if active:
                return BrowserAccountSelection(
                    matched=True,
                    profile=active,
                    match_strategy="current_active",
                    confidence=1.0,
                )

            # If only 1 profile registered, auto-select it
            if len(profiles) == 1:
                return BrowserAccountSelection(
                    matched=True,
                    profile=profiles[0],
                    match_strategy="single_available",
                    confidence=1.0,
                )

            # Multiple exist, prompt user
            prompt_en = f"Multiple accounts found: {', '.join([p.display_name for p in profiles])}. Which account would you like to use?"
            prompt_ta = f"பல கணக்குகள் உள்ளன: {', '.join([p.display_name for p in profiles])}. எந்தக் கணக்கைத் திறக்க வேண்டும்?"
            return BrowserAccountSelection(
                matched=False,
                candidates=profiles,
                match_strategy="interactive_prompt",
                confidence=0.0,
                selection_prompt=f"{prompt_ta}\n{prompt_en}",
            )

        clean_query = query.strip().lower()

        # 2. Check exact profile_id match
        for p in profiles:
            if p.profile_id.lower() == clean_query:
                return BrowserAccountSelection(
                    matched=True,
                    profile=p,
                    match_strategy="exact_id",
                    confidence=1.0,
                )

        # 3. Check exact email match
        for p in profiles:
            if p.email and p.email.lower() == clean_query:
                return BrowserAccountSelection(
                    matched=True,
                    profile=p,
                    match_strategy="exact_email",
                    confidence=1.0,
                )

        # 4. Check email prefix or domain match
        for p in profiles:
            if p.email and clean_query in p.email.lower():
                return BrowserAccountSelection(
                    matched=True,
                    profile=p,
                    match_strategy="email_substring",
                    confidence=0.9,
                )

        # 5. Check display name match
        for p in profiles:
            if p.display_name.lower() == clean_query:
                return BrowserAccountSelection(
                    matched=True,
                    profile=p,
                    match_strategy="display_name_exact",
                    confidence=0.95,
                )

        # 6. Check Tamil aliases
        tamil_matches: List[BrowserProfileMetadata] = []
        for p in profiles:
            for ta in p.tamil_aliases:
                if ta.lower() in clean_query or clean_query in ta.lower():
                    tamil_matches.append(p)
                    break

        if len(tamil_matches) == 1:
            return BrowserAccountSelection(
                matched=True,
                profile=tamil_matches[0],
                match_strategy="tamil_alias_match",
                confidence=0.95,
            )
        elif len(tamil_matches) > 1:
            return self._build_ambiguous_result(tamil_matches, clean_query)

        # 7. Check English and Tanglish aliases
        alias_matches: List[BrowserProfileMetadata] = []
        for p in profiles:
            matched_alias = False
            for alias in p.aliases:
                # Match token boundary or inclusion
                if alias.lower() in clean_query or clean_query in alias.lower():
                    alias_matches.append(p)
                    matched_alias = True
                    break
            if not matched_alias and any(token in clean_query.split() for token in p.aliases):
                alias_matches.append(p)

        # Deduplicate
        alias_matches = list({p.profile_id: p for p in alias_matches}.values())

        if len(alias_matches) == 1:
            return BrowserAccountSelection(
                matched=True,
                profile=alias_matches[0],
                match_strategy="alias_match",
                confidence=0.88,
            )
        elif len(alias_matches) > 1:
            return self._build_ambiguous_result(alias_matches, clean_query)

        # 8. Fuzzy matching on display name or ID
        if not require_exact:
            names = [p.display_name.lower() for p in profiles]
            close = difflib.get_close_matches(clean_query, names, n=1, cutoff=0.6)
            if close:
                matched_p = next(p for p in profiles if p.display_name.lower() == close[0])
                return BrowserAccountSelection(
                    matched=True,
                    profile=matched_p,
                    match_strategy="fuzzy_name",
                    confidence=0.75,
                )

        # 9. No match found
        return BrowserAccountSelection(
            matched=False,
            candidates=profiles,
            match_strategy="no_match",
            confidence=0.0,
            selection_prompt=f"Account '{query}' not recognized. Available accounts: {', '.join([p.display_name for p in profiles])}",
        )

    def _build_ambiguous_result(self, candidates: List[BrowserProfileMetadata], query: str) -> BrowserAccountSelection:
        """Construct bilingual prompt for ambiguous account choices."""
        cand_names = [f"'{p.display_name}' ({p.email or p.profile_id})" for p in candidates]
        prompt_en = f"Multiple accounts match '{query}': {', '.join(cand_names)}. Please specify which account to use."
        prompt_ta = f"'{query}' என்ற பெயருக்கு பல கணக்குகள் பொருந்துகின்றன: {', '.join(cand_names)}. தயவுசெய்து எந்தக் கணக்கு என்று குறிப்பிடவும்."
        return BrowserAccountSelection(
            matched=False,
            candidates=candidates,
            match_strategy="ambiguous",
            confidence=0.5,
            selection_prompt=f"{prompt_ta}\n{prompt_en}",
        )
