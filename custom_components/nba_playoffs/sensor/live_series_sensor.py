from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN, LOGGER, SERIES_COORDINATOR, LIVE_COORDINATOR
from ..utils.mapping_bracket import SERIES_MAP


async def _cleanup_old_live_entities(hass: HomeAssistant) -> None:
    """Remove stale nba_playoffs live sensor entities."""
    registry = er.async_get(hass)

    OLD_ENTITY_PREFIXES = [
        "sensor.nba_live_",
        "sensor.nba_series_",
    ]
    OLD_UNIQUE_PREFIXES = [
        "nba_live_",
        "nba_series_",
        f"{DOMAIN}_live_",
        f"{DOMAIN}_series_",
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


class LiveSeriesSensor(SensorEntity):
    """Real-time game sensor — event-driven, updated by LiveCoordinator."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        series_key: str,
        meta: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.series_key = series_key
        self._meta = meta

        self._attr_unique_id = f"nba_live_{series_key}"
        self._attr_name = f"NBA Live {series_key.upper()}"
        self._attr_icon = "mdi:basketball"

        data = hass.data[DOMAIN][entry.entry_id]
        self.series_coordinator = data[SERIES_COORDINATOR]
        self.live_coordinator = data[LIVE_COORDINATOR]

        self._state = "normal"
        self._attr_extra_state_attributes: Dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        self.live_coordinator.add_listener(
            lambda: self.hass.async_create_task(self._handle_update())
        )
        self.series_coordinator.async_add_listener(
            lambda: self.hass.async_create_task(self._handle_update())
        )
        await self._handle_update()

    async def _handle_update(self) -> None:
        try:
            live_state = self.live_coordinator.get_series(self.series_key)

            base_attrs: Dict[str, Any] = {}
            if live_state:
                base_attrs["game_id"] = live_state.get("game_id")

            self._attr_extra_state_attributes = base_attrs

            if not live_state or live_state.get("json") is None:
                await self._fallback_to_series()
                self.async_write_ha_state()
                return

            raw = live_state.get("json")
            if raw:
                self._attr_extra_state_attributes.update(raw)
                game_state = raw.get("game_state", "")
                if game_state == "in":
                    self._state = "live"
                elif game_state == "post":
                    self._state = "final"
                else:
                    self._state = "normal"
                self.async_write_ha_state()
                return

            await self._fallback_to_series()
            self.async_write_ha_state()

        except Exception as err:
            LOGGER.error("LiveSeriesSensor update failed for %s: %s", self.series_key, err)

    async def _fallback_to_series(self) -> None:
        """Use series coordinator data when no live feed is available."""
        series_data = (self.series_coordinator.data or {}).get(self.series_key, {})

        today = series_data.get("today_game")
        next_game = series_data.get("next_game")

        if today:
            self._state = today.get("game_state") or "normal"
            self._attr_extra_state_attributes.update(today)
            return

        if next_game:
            self._state = "pre"
            self._attr_extra_state_attributes.update(next_game)
            return

        self._state = "normal"

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attr_extra_state_attributes
