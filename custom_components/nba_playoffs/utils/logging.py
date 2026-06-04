from __future__ import annotations

from ..const import LOGGER, CONF_DEBUG


def debug_enabled(entry) -> bool:
    return bool(entry.options.get(CONF_DEBUG, False))


def log_debug(entry, msg: str, *args) -> None:
    if debug_enabled(entry):
        LOGGER.debug(msg, *args)
