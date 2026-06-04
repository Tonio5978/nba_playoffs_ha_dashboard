from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import aiohttp
import async_timeout

from ..const import API_SCOREBOARD, LOGGER
from ..utils.parsing_live import parse_live_game


async def fetch_live_game(
    session: aiohttp.ClientSession,
    game_id: str,
) -> Dict[str, Any]:
    """Return parsed live data for game_id by fetching today's scoreboard.

    ESPN does not expose a dedicated single-game live endpoint in the public
    API, so we refetch the day's scoreboard and find the matching event by ID.
    This guarantees the response format is identical to what SeriesCoordinator
    parses, keeping both coordinators in sync.
    """
    if not game_id:
        return {}

    today = datetime.now().strftime("%Y%m%d")
    params = {"dates": today, "limit": 50}

    try:
        async with async_timeout.timeout(10):
            async with session.get(API_SCOREBOARD, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        events = data.get("events", [])
        for event in events:
            if str(event.get("id", "")) == str(game_id):
                parsed = parse_live_game(event)
                parsed["game_id"] = game_id
                return parsed

        LOGGER.debug("fetch_live_game: game_id=%s not found in today's scoreboard", game_id)
        return {}

    except Exception as err:
        LOGGER.error("fetch_live_game failed for game_id=%s: %s", game_id, err)
        return {}
