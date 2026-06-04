from __future__ import annotations

from typing import Any
import aiohttp
import async_timeout

from ..const import API_SCOREBOARD, LOGGER


async def _fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    params: dict | None = None,
) -> Any:
    async with async_timeout.timeout(15):
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_scoreboard(
    session: aiohttp.ClientSession,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch all NBA playoff events in a date range.

    start_date / end_date must be 'YYYYMMDD' strings.
    Returns the ESPN 'events' list (may be empty outside playoffs).
    """
    params = {
        "limit": 200,
        "dates": f"{start_date}-{end_date}",
    }
    try:
        data = await _fetch_json(session, API_SCOREBOARD, params=params)
        return data.get("events", [])
    except Exception as err:
        LOGGER.error("fetch_scoreboard failed (%s–%s): %s", start_date, end_date, err)
        return []


async def fetch_today_scoreboard(
    session: aiohttp.ClientSession,
    date_str: str,
) -> list[dict]:
    """Fetch events for a single day (date_str = 'YYYYMMDD')."""
    params = {
        "dates": date_str,
        "limit": 50,
    }
    try:
        data = await _fetch_json(session, API_SCOREBOARD, params=params)
        return data.get("events", [])
    except Exception as err:
        LOGGER.error("fetch_today_scoreboard failed (%s): %s", date_str, err)
        return []
