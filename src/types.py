from __future__ import annotations

from typing import TypedDict


class GameDict(TypedDict, total=False):
    title: str
    url: str
    final_url: str  # after GamerPower redirects
    app_id: str  # Steam
    game_id: str
    platform: str  # android, ios
    label: str
    source: str  # steamdb, gamerpower, ...
    status: str
    code: str  # GOG key from Prime
    store: str
