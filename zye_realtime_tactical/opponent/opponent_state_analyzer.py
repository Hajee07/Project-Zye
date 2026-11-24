"""
Opponent State Analyzer.
Extracts the opponent's current state, last observed action, and recent sequence context.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class OpponentStateAnalyzer:
    """Analyzes the latest sequential actions to identify the current context."""

    @classmethod
    def get_current_state(cls, actions: List[str]) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
        """Returns tuple of (last_action, (second_to_last, last_action)) if available."""
        if not actions:
            return None, None
        last_act = actions[-1]
        pair = (actions[-2], actions[-1]) if len(actions) >= 2 else None
        return last_act, pair

    @classmethod
    def format_state_string(cls, state_tuple: Any) -> Optional[str]:
        """Formats current state tuple into a human-readable representation."""
        if not state_tuple:
            return None
        if isinstance(state_tuple, tuple):
            if len(state_tuple) == 2 and isinstance(state_tuple[1], tuple):
                pair = state_tuple[1]
                return f"{pair[0]} -> {pair[1]}"
            elif len(state_tuple) == 2 and isinstance(state_tuple[0], str) and isinstance(state_tuple[1], str):
                return f"{state_tuple[0]} -> {state_tuple[1]}"
            elif len(state_tuple) >= 1 and isinstance(state_tuple[0], str):
                return state_tuple[0]
        elif isinstance(state_tuple, str):
            return state_tuple
        return None

    @classmethod
    def analyze_current_state(cls, actions: List[str]) -> Dict[str, Any]:
        """
        Extracts last action, last two actions, and formatted state string.
        """
        if not actions:
            return {
                "last_action": None,
                "last_two_actions": [],
                "current_state": None,
            }

        last_act = actions[-1]
        if len(actions) == 1:
            return {
                "last_action": last_act,
                "last_two_actions": [last_act],
                "current_state": last_act,
            }

        last_two = [actions[-2], actions[-1]]
        state_str = f"{actions[-2]} -> {actions[-1]}"
        return {
            "last_action": last_act,
            "last_two_actions": last_two,
            "current_state": state_str,
        }
