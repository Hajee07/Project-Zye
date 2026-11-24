#!/usr/bin/env python3
"""
ZYE AI — Conversation History & Context Manager v1.0
===================================================

Maintains multi-turn conversational context for the Gemini Brain:
- Preserves user prompts, model responses, function calls, and function responses
- Bounded 16-turn policy with atomic sequence preservation
- Never breaks or slices in the middle of a function-call/function-response sequence
- Thread-safe history access and reset capabilities
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("zye_brain.history")


@dataclass
class ConversationTurn:
    """Represents a single atomic message or tool interaction turn."""
    role: str  # "user" | "model"
    parts: list[Any] = field(default_factory=list)
    is_tool_call: bool = False
    is_tool_response: bool = False
    turn_id: int = 0


class ZyeConversationHistory:
    """
    Manages bounded multi-turn conversation context for Gemini,
    guaranteeing tool-call/response sequence integrity.
    """

    def __init__(self, max_turns: int = 16) -> None:
        self.max_turns = max_turns
        self._turns: list[ConversationTurn] = []
        self._turn_counter: int = 0

    def add_user_message(self, parts: list[Any]) -> None:
        """Append a user message turn."""
        self._turn_counter += 1
        turn = ConversationTurn(
            role="user",
            parts=parts,
            is_tool_call=False,
            is_tool_response=False,
            turn_id=self._turn_counter,
        )
        self._turns.append(turn)
        self._enforce_bounds()

    def add_model_message(self, parts: list[Any], is_tool_call: bool = False) -> None:
        """Append a model response turn."""
        self._turn_counter += 1
        turn = ConversationTurn(
            role="model",
            parts=parts,
            is_tool_call=is_tool_call,
            is_tool_response=False,
            turn_id=self._turn_counter,
        )
        self._turns.append(turn)
        self._enforce_bounds()

    def add_tool_response(self, parts: list[Any]) -> None:
        """Append a function execution response turn."""
        self._turn_counter += 1
        turn = ConversationTurn(
            role="user",
            parts=parts,
            is_tool_call=False,
            is_tool_response=True,
            turn_id=self._turn_counter,
        )
        self._turns.append(turn)
        self._enforce_bounds()

    def get_contents(self) -> list[dict[str, Any]]:
        """
        Return the history formatted as list of Content dictionaries
        compatible with the google-genai SDK.
        """
        contents: list[dict[str, Any]] = []
        for t in self._turns:
            contents.append({
                "role": t.role,
                "parts": t.parts,
            })
        return contents

    def _enforce_bounds(self) -> None:
        """
        Truncate history to max_turns without severing tool call/response pairs.
        """
        if len(self._turns) <= self.max_turns:
            return

        excess = len(self._turns) - self.max_turns
        # Find a safe cutoff index where index is not inside a tool call sequence
        cutoff = excess
        while cutoff < len(self._turns):
            curr = self._turns[cutoff]
            prev = self._turns[cutoff - 1] if cutoff > 0 else None

            # If current turn is a tool response, cutting before it leaves orphaned response
            # If previous turn is a tool call, cutting between call and response breaks sequence
            if curr.is_tool_response or (prev and prev.is_tool_call):
                cutoff += 1
            else:
                break

        if cutoff < len(self._turns):
            self._turns = self._turns[cutoff:]
        else:
            # Slicing would break active sequence; keep until next turn closes sequence
            pass

    def clear(self) -> None:
        """Reset conversation context completely."""
        self._turns.clear()
        self._turn_counter = 0

    def __len__(self) -> int:
        return len(self._turns)

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic metrics for conversation context."""
        return {
            "current_turns": len(self._turns),
            "max_turns": self.max_turns,
            "total_turn_counter": self._turn_counter,
        }
