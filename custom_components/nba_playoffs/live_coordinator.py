from __future__ import annotations

from typing import Any
import asyncio
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import aiohttp_client

from .const import (
    DOMAIN,
    LOGGER,
    SERIES_LETTERS,
)
from .api.live_api import fetch_live_game
from .utils.mapping_bracket import SERIES_MAP

# ---------------------------------------------------------------------------
# Polling intervals (seconds)
# ESPN API is polled — be respectful of rate limits.
# ---------------------------------------------------------------------------
LIVE_INTERVAL = 10           # game in progress (state == "in")
PRE_INTERVAL = 30            # pre-game (within 30 min of tip-off)
PREGAME_LT2H_INTERVAL = 300  # pre-game < 2 h away
PREGAME_GT2H_INTERVAL = 1800 # pre-game > 2 h away
POST_COOLDOWN_SECONDS = 120  # just finished → quick refresh then slow down
OFF_INTERVAL = 3600          # no game / off-day
DEFAULT_INTERVAL = 600


# Reverse lookup: series_letter → bracket_key
_LETTER_TO_KEY = {meta["series_letter"]: key for key, meta in SERIES_MAP.items()}


class LiveCoordinator:
    """Per-series live polling using the ESPN scoreboard endpoint.

    Unlike SeriesCoordinator (which uses DataUpdateCoordinator), this class
    manages its own asyncio tasks per series so each series can poll at its
    own cadence (10 s live vs. 30 min idle).
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        persisted = entry.options.get("live_state", {})

        # State is keyed by bracket_key (e.g. 'r1_east_1') for consistency with sensors.
        self.state: dict[str, dict] = {}
        for key in SERIES_MAP:
            prev = persisted.get(key, {})
            self.state[key] = {
                "game_id": None,
                "json": None,
                "state": None,
                "interval": prev.get("interval", PREGAME_GT2H_INTERVAL),
                "cooldown": prev.get("cooldown", 0),
            }

        self.tasks: dict[str, asyncio.Task] = {}
        self._listeners: list[callable] = []

    # -------------------------------------------------------------------------
    # Listener registration (sensors register here)
    # -------------------------------------------------------------------------
    def add_listener(self, cb):
        self._listeners.append(cb)

    def _notify_listeners(self):
        for cb in list(self._listeners):
            try:
                cb()
            except Exception as err:
                LOGGER.error("LiveCoordinator listener failed: %s", err)

    # -------------------------------------------------------------------------
    # Handoff from SeriesCoordinator
    # -------------------------------------------------------------------------
    @callback
    def attach_series_coordinator(self, series_coordinator):
        series_coordinator.async_add_listener(
            lambda: self.update_from_series(series_coordinator.data)
        )

    @callback
    def update_from_series(self, series_data: dict[str, Any]) -> None:
        """Receive game_id from SeriesCoordinator and store it for live polling."""
        for bracket_key, data in series_data.items():
            if bracket_key not in self.state:
                continue

            today = data.get("today_game")
            next_game = data.get("next_game")

            if today:
                self.state[bracket_key]["game_id"] = today.get("game_id")
                self.state[bracket_key]["json"] = None
                LOGGER.debug("SERIES→LIVE %s: TODAY game_id=%s", bracket_key, today.get("game_id"))
                continue

            if next_game:
                self.state[bracket_key]["game_id"] = next_game.get("game_id")
                self.state[bracket_key]["json"] = None
                LOGGER.debug("SERIES→LIVE %s: NEXT game_id=%s", bracket_key, next_game.get("game_id"))
                continue

            self.state[bracket_key]["game_id"] = None
            self.state[bracket_key]["json"] = None
            LOGGER.debug("SERIES→LIVE %s: NO GAME", bracket_key)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def get_series(self, bracket_key: str) -> dict[str, Any]:
        return self.state.get(bracket_key, {})

    async def async_start(self) -> None:
        for key in SERIES_MAP:
            if key not in self.tasks:
                self.tasks[key] = asyncio.create_task(self._poll_series(key))

    # -------------------------------------------------------------------------
    # Per-series polling loop
    # -------------------------------------------------------------------------
    async def _poll_series(self, bracket_key: str) -> None:
        session = aiohttp_client.async_get_clientsession(self.hass)

        while True:
            try:
                await self._update_series(bracket_key, session)
            except Exception as err:
                LOGGER.error("LiveCoordinator error for %s: %s", bracket_key, err)

            await asyncio.sleep(self.state[bracket_key]["interval"])

    async def _update_series(self, bracket_key: str, session) -> None:
        series_state = self.state[bracket_key]
        game_id = series_state["game_id"]

        if not game_id:
            series_state["json"] = None
            series_state["state"] = None
            series_state["interval"] = OFF_INTERVAL
            LOGGER.debug("LIVE POLL %s: no game_id → idle", bracket_key)
            self._persist()
            self._notify_listeners()
            return

        parsed = await fetch_live_game(session, game_id)
        if not parsed:
            series_state["interval"] = PREGAME_GT2H_INTERVAL
            LOGGER.debug("LIVE POLL %s: fetch failed game_id=%s", bracket_key, game_id)
            self._persist()
            self._notify_listeners()
            return

        game_state = parsed.get("game_state", "")
        series_state["json"] = parsed
        series_state["state"] = game_state
        series_state["interval"] = self._compute_interval(parsed)

        LOGGER.debug(
            "LIVE POLL %s: game_id=%s state=%s interval=%s",
            bracket_key, game_id, game_state, series_state["interval"],
        )

        self._persist()
        self._notify_listeners()

    # -------------------------------------------------------------------------
    # Interval logic (ESPN states: pre / in / post)
    # -------------------------------------------------------------------------
    def _compute_interval(self, live_json: dict[str, Any]) -> int:
        state = (live_json.get("game_state") or "").lower()
        start_str = live_json.get("start_time")

        if state == "in":
            return LIVE_INTERVAL

        if state == "post":
            return POST_COOLDOWN_SECONDS

        if state == "pre":
            if not start_str:
                return DEFAULT_INTERVAL
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                diff = (start_dt - now).total_seconds()
                diff = max(diff, 0)
                if diff > 2 * 3600:
                    return PREGAME_GT2H_INTERVAL
                if diff > 1800:
                    return PREGAME_LT2H_INTERVAL
                return PRE_INTERVAL
            except Exception:
                return DEFAULT_INTERVAL

        return DEFAULT_INTERVAL

    # -------------------------------------------------------------------------
    # Persistence (stores interval state across HA restarts)
    # -------------------------------------------------------------------------
    def _persist(self) -> None:
        new_options = dict(self.entry.options)
        new_options["live_state"] = self.state
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
