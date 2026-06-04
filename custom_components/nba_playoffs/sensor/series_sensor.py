from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN, SERIES_COORDINATOR
from ..series_coordinator import SeriesCoordinator
from ..utils.mapping_bracket import SERIES_MAP


async def _cleanup_old_entities(hass: HomeAssistant) -> None:
    """Remove any stale nba_playoffs sensor entities from previous installs."""
    registry = er.async_get(hass)

    OLD_ENTITY_PREFIXES = [
        "sensor.nba_series_",
        "sensor.nba_live_",
    ]
    OLD_UNIQUE_PREFIXES = [
        "nba_series_",
        "nba_live_",
        f"{DOMAIN}_series_",
        f"{DOMAIN}_live_",
        f"{DOMAIN}_",
    ]

    for entity_id, entity in list(registry.entities.items()):
        if entity.platform != DOMAIN:
            continue
        if any(entity_id.startswith(p) for p in OLD_ENTITY_PREFIXES):
            registry.async_remove(entity_id)
            continue
        if any(entity.unique_id.startswith(p) for p in OLD_UNIQUE_PREFIXES):
            registry.async_remove(entity_id)
            continue


class SeriesSensor(CoordinatorEntity, SensorEntity):
    """Static series data sensor — updates every 5 minutes via SeriesCoordinator."""

    _attr_icon = "mdi:basketball"

    def __init__(
        self,
        coordinator: SeriesCoordinator,
        series_key: str,
        meta: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._series_key = series_key
        self._meta = meta
        self._attr_unique_id = f"nba_series_{series_key}"
        self._attr_name = f"NBA Series {series_key.upper()}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        series = data.get(self._series_key, {})

        games = series.get("games", []) or []

        # Build games_list and games_dict for dashboard consumption
        games_list = []
        games_dict: dict[str, dict] = {}
        for g in games:
            game_id = g.get("game_id")
            if not game_id:
                continue
            item = {
                "game_id": game_id,
                "date": g.get("date"),
                "game_state": g.get("game_state"),
                "status_detail": g.get("status_detail"),
                "home_abbr": g.get("home_abbr"),
                "away_abbr": g.get("away_abbr"),
                "home_score": g.get("home_score"),
                "away_score": g.get("away_score"),
            }
            games_list.append(item)
            games_dict[str(game_id)] = item

        next_game = series.get("next_game")

        return {
            # Teams
            "team1_abbrev": series.get("team1_abbr", "TBD"),
            "team1_name": series.get("team1_name", "TBD"),
            "team1_logo": series.get("team1_logo", ""),
            "team1_seed": series.get("team1_seed", 0),
            "team1_wins": series.get("team1_wins", 0),
            "team2_abbrev": series.get("team2_abbr", "TBD"),
            "team2_name": series.get("team2_name", "TBD"),
            "team2_logo": series.get("team2_logo", ""),
            "team2_seed": series.get("team2_seed", 0),
            "team2_wins": series.get("team2_wins", 0),
            # Series info
            "series_status": series.get("series_status", "TBD"),
            "series_complete": series.get("series_complete", False),
            "round": self._meta["round"],
            "conference": self._meta["conference"],
            "series_letter": self._meta["series_letter"],
            # Games
            "games_list": games_list,
            "games_dict": games_dict,
            # Next game
            "next_game_id": next_game.get("game_id") if next_game else None,
            "next_game_time": next_game.get("date") if next_game else None,
            "next_game_home": next_game.get("home_abbr") if next_game else None,
            "next_game_away": next_game.get("away_abbr") if next_game else None,
            # Today
            "today_game_id": series.get("today_game_id"),
        }

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        return (data.get(self._series_key) or {}).get("series_status")
