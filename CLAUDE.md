# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Home Assistant custom integration (`nhl_playoffs`) that tracks NHL Stanley Cup Playoffs. It creates two sensor types per playoff series:
- `sensor.nhl_series_*` — static series data (teams, wins, schedule)
- `sensor.nhl_live_*` — real-time game state (score, period, PP, EN)

The Lovelace dashboard YAML in [lovelace/nhl_playoffs_dashboard.yaml](lovelace/nhl_playoffs_dashboard.yaml) uses `button-card` to display a 5-column bracket layout.

## Development Setup

This is a Home Assistant integration — there is no local dev server or test runner. Development workflow:
1. Copy `custom_components/nhl_playoffs/` to a running HA instance's `config/custom_components/`
2. Restart HA or reload the integration via **Settings → Devices & Services**
3. Enable debug logging in HA: add `logger: default: warning` + `logs: custom_components.nhl_playoffs: debug` to `configuration.yaml`

To test a specific season without waiting for playoffs: in integration options, switch to `Manual season` mode and enter `20232024` (the default good full-data test season).

## Architecture

### Coordinator Split

Two coordinators serve different polling cadences:

**[series_coordinator.py](custom_components/nhl_playoffs/series_coordinator.py)** — polls every 5 minutes via `DataUpdateCoordinator`. Fetches from three NHL endpoints in parallel: bracket, carousel, and per-series schedule. Computes `today_game` and `next_game` for each series letter (A–O) and stores them in a merged dict keyed by series letter.

**[live_coordinator.py](custom_components/nhl_playoffs/live_coordinator.py)** — independent asyncio task per series (not a `DataUpdateCoordinator`). Adapts its poll interval dynamically: 5s when LIVE/CRIT, 30s when PRE/OVER, 3600s when FUT >3h, 3600s when OFF. Gets `game_pk` from `SeriesCoordinator` via listener callback. The `LiveCoordinator` does NOT inherit from `DataUpdateCoordinator` — it manages its own tasks and notifies sensors via `add_listener()`.

### Init Sequence (critical ordering)

In [__init__.py](custom_components/nhl_playoffs/__init__.py):
1. `SeriesCoordinator` does its first refresh synchronously
2. `LiveCoordinator.update_from_series()` is called immediately (populates `game_pk`)
3. `attach_series_coordinator()` is called to register the update listener
4. `async_start()` is deferred until `homeassistant_started` fires — prevents polling before HA is fully up

This ordering matters: the initial sync in step 2 must happen before the listener (step 3) to avoid overwriting with `None`.

### Series Letter Mapping

[utils/mapping_bracket.py](custom_components/nhl_playoffs/utils/mapping_bracket.py) defines `SERIES_MAP` which maps human-readable keys (`r1_east_1`, `r4_final`) to NHL API series letters (A–O). Round 1 East = A–D, Round 1 West = E–H, Round 2 East = I–J, Round 2 West = K–L, Conference Finals = M–N, Stanley Cup Final = O.

Sensor unique IDs use the human-readable key: `nhl_series_r1_east_1`, `nhl_live_r4_final`, etc.

### NHL API Endpoints

Defined in [const.py](custom_components/nhl_playoffs/const.py):
- `API_BRACKET` — bracket structure (teams per series)
- `API_CAROUSEL` — active series summary
- `API_SCHEDULE` — full series details including `games[]` list (used as authoritative source for game_pk, scores, and timestamps)
- `API_LIVE_GAME` — real-time play-by-play with `situation` block (PP, EN, strength)

### Live Data Parsing

[utils/parsing_live.py](custom_components/nhl_playoffs/utils/parsing_live.py) normalizes the NHL play-by-play JSON. Key normalization: `CRIT` → `LIVE` (CRIT is NHL's name for close-game final minutes). Power play and empty net are read from `situation.homeTeam/awayTeam.situationDescriptions` (`"PP"`, `"EN"`) — not inferred from strength values.

### Sensor Cleanup on Setup

Both sensor files ([sensor/series_sensor.py](custom_components/nhl_playoffs/sensor/series_sensor.py), [sensor/live_series_sensor.py](custom_components/nhl_playoffs/sensor/live_series_sensor.py)) run `_cleanup_old_entities()` on setup to remove sensors from previous naming conventions. This handles migration from older versions.

## Key Files

| File | Purpose |
|------|---------|
| `const.py` | All constants, NHL API URLs, intervals |
| `utils/mapping_bracket.py` | Series letter ↔ sensor key mapping |
| `utils/parsing_live.py` | Normalizes NHL play-by-play JSON |
| `utils/season.py` | Auto-detects current season year |
| `api/fetcher.py` | HTTP helpers for bracket/carousel/schedule |
| `api/live_api.py` | HTTP fetch + parse for live games |
| `lovelace/nhl_playoffs_dashboard.yaml` | Full dashboard YAML using `button-card` |

## Dashboard

Requires `button-card` (HACS). Place team logo images at `config/www/nhl/` — `tbd.png` must exist for placeholder display. Dashboard references sensors by entity ID (`sensor.nhl_series_r1_east_1`, etc.) and reads attributes like `team1_abbrev`, `team1_logo`, `series_status`, `games_list`.
