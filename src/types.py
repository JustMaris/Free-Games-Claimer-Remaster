"""Type definitions for the Free Games Claimer Remaster project.

This module contains type hints and TypedDict definitions used throughout
the codebase for better type safety and IDE support.
"""

from __future__ import annotations

from typing import TypedDict, NotRequired


class GameDict(TypedDict, total=False):
    """Represents a game to be claimed or that has been claimed."""
    title: str
    url: str
    final_url: NotRequired[str]  # URL after redirects (GamerPower)
    app_id: NotRequired[str]  # Steam app ID
    game_id: NotRequired[str]  # Store-specific game identifier
    platform: NotRequired[str]  # Platform (android, ios, etc.)
    label: NotRequired[str]  # Platform label
    source: NotRequired[str]  # Source of the game (steamdb, gamerpower, etc.)
    status: NotRequired[str]  # Claim status (claimed, failed, etc.)
    code: NotRequired[str]  # Redemption code (GOG, etc.)
    store: NotRequired[str]  # Store name


class StoreResultDict(TypedDict, total=False):
    """Result from a store claimer."""
    store: str
    user: str
    games: list[GameDict]


class ClaimedGameDict(TypedDict, total=False):
    """Database record for a claimed game."""
    id: int
    store: str
    user: str
    game_id: str
    title: str
    url: str | None
    status: str
    code: str | None
    extra: str | None
    created_at: str
    updated_at: str
