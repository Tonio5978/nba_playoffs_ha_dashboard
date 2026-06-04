from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.util.dt import get_time_zone

from .const import (
    DOMAIN,
    LOGGER,
    UPDATE_INTERVAL,
    CONF_SEASON_MODE,
    CONF_MANUAL_SEASON,
    SEASON_MODE_CURRENT,
    SEASON_MODE_MANUAL,
    TEAM_CONFERENCES,
    ROUND_NAME_MAP,
)
from .utils.season import get_current_season, get_playoffs_dates
from .utils.mapping_bracket import SERIES_MAP
from .utils.parsing_live import _parse_score, _get_logo
from .api.fetcher import fetch_scoreboard


class SeriesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches all NBA playoff games from ESPN and maps them to bracket slots."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        data = entry.data
        options = entry.options

        self.season_mode = options.get(
            CONF_SEASON_MODE,
            data.get(CONF_SEASON_MODE, SEASON_MODE_CURRENT),
        )
        self.manual_season = options.get(
            CONF_MANUAL_SEASON,
            data.get(CONF_MANUAL_SEASON, ""),
        )

        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_series",
            update_interval=UPDATE_INTERVAL,
        )

    # -------------------------------------------------------------------------
    # Main update
    # -------------------------------------------------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.season_mode == SEASON_MODE_MANUAL and self.manual_season:
                year = int(self.manual_season)
            else:
                year = get_current_season()

            start_date, end_date = get_playoffs_dates(year)
            session = aiohttp_client.async_get_clientsession(self.hass)

            events = await fetch_scoreboard(session, start_date, end_date)

            LOGGER.warning(
                "NBA SeriesCoordinator: %d raw events received for year=%d (dates %s–%s)",
                len(events), year, start_date, end_date,
            )

            if events:
                # Log first event structure to help diagnose season.type format
                first = events[0]
                LOGGER.warning(
                    "NBA first event sample: id=%s season=%s name=%s",
                    first.get("id"), first.get("season"), first.get("name"),
                )

            # Filter to playoff games only (season.type == 3).
            # ESPN may return the type as int 3 or string "3" — accept both.
            playoff_events = [
                e for e in events
                if str(e.get("season", {}).get("type", "")) == "3"
            ]

            LOGGER.warning(
                "NBA SeriesCoordinator: %d playoff events after type-3 filter",
                len(playoff_events),
            )

            series_by_key = self._build_series_from_events(playoff_events)

            LOGGER.warning(
                "NBA SeriesCoordinator: %d series detected → keys: %s",
                len(series_by_key), list(series_by_key.keys()),
            )

            return self._build_data(series_by_key)

        except Exception as err:
            raise UpdateFailed(f"Error updating NBA Playoffs data: {err}") from err

    # -------------------------------------------------------------------------
    # Group events into series and map to bracket keys
    # -------------------------------------------------------------------------
    def _build_series_from_events(self, events: list[dict]) -> dict[str, dict]:
        """
        Groups ESPN events by team matchup, determines round/conference/slot,
        and returns a dict keyed by bracket key (e.g. 'r1_east_1').
        """
        # Step 1 — group events by canonical team pair
        raw_series: dict[frozenset, list[dict]] = {}
        for event in events:
            competition = (event.get("competitions") or [{}])[0]
            competitors = competition.get("competitors", [])
            if len(competitors) < 2:
                continue
            home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            home_abbr = home_comp.get("team", {}).get("abbreviation", "")
            away_abbr = away_comp.get("team", {}).get("abbreviation", "")
            if not home_abbr or not away_abbr:
                continue
            pair = frozenset({home_abbr, away_abbr})
            raw_series.setdefault(pair, []).append(event)

        LOGGER.warning("NBA _build_series: %d unique matchups found", len(raw_series))

        # Step 2 — infer round numbers from bracket structure.
        # ESPN does not include series.title in the scoreboard response, so we
        # deduce the round by counting how many series each team appears in:
        # a team that wins R1 appears in 2 series, R2 winner in 3, Finals in 4.
        # The round of a matchup = min(appearances of team A, appearances of team B).
        round_map = self._infer_rounds_from_bracket(raw_series)
        LOGGER.warning(
            "NBA _build_series: inferred rounds = %s",
            {str(sorted(k)): v for k, v in round_map.items()},
        )

        # Step 3 — extract metadata for each series
        series_list: list[dict] = []
        for pair, games in raw_series.items():
            inferred_round = round_map.get(pair, 0)
            info = self._extract_series_info(pair, games, inferred_round)
            if info:
                series_list.append(info)
            else:
                LOGGER.warning(
                    "NBA _build_series: matchup %s skipped (round=%s)",
                    sorted(pair), inferred_round,
                )

        # Step 4 — assign bracket keys
        return self._assign_bracket_keys(series_list)

    # -------------------------------------------------------------------------
    # Bracket-based round inference
    # -------------------------------------------------------------------------
    @staticmethod
    def _infer_rounds_from_bracket(
        raw_series: dict[frozenset, list],
    ) -> dict[frozenset, int]:
        """Deduce each series' round from how many series each team has played.

        In a 16-team single-elimination bracket every team that wins round N
        appears in one additional series.  The round of a matchup between A
        and B equals min(total series count of A, total series count of B).

        Examples (2026 playoffs from logs):
          TOR  → 1 series   (lost R1)
          DET  → 2 series   (lost R2)
          OKC  → 3 series   (lost R3)
          NY   → 4 series   (Finals)
          DEN-MIN: min(count(DEN)=1, count(MIN)=2) = 1  → Round 1  ✓
          MIN-SA:  min(count(MIN)=2, count(SA)=4)  = 2  → Round 2  ✓
          OKC-SA:  min(count(OKC)=3, count(SA)=4)  = 3  → Round 3  ✓
          NY-SA:   min(count(NY)=4,  count(SA)=4)  = 4  → Round 4  ✓
        """
        # Count the number of series each team participates in
        team_count: dict[str, int] = {}
        for pair in raw_series:
            for team in pair:
                team_count[team] = team_count.get(team, 0) + 1

        round_map: dict[frozenset, int] = {}
        for pair in raw_series:
            teams = list(pair)
            round_map[pair] = min(
                team_count.get(teams[0], 1),
                team_count.get(teams[1], 1),
            )
        return round_map

    @staticmethod
    def _detect_round_from_event(event: dict) -> int:
        """Try to read round number from ESPN event metadata fields.

        ESPN sometimes includes round info in:
          - event.notes[].type.text
          - competitions[].notes[].headline
          - competitors[].series.title
        Returns 0 if nothing is found.
        """
        # 1. Event-level notes
        for note in event.get("notes") or []:
            text = (
                (note.get("type") or {}).get("text", "")
                or note.get("headline", "")
            ).lower()
            for name, num in ROUND_NAME_MAP.items():
                if name in text:
                    return num

        # 2. Competition-level notes
        comp = (event.get("competitions") or [{}])[0]
        for note in comp.get("notes") or []:
            text = (note.get("headline") or (note.get("type") or {}).get("text", "")).lower()
            for name, num in ROUND_NAME_MAP.items():
                if name in text:
                    return num

        # 3. competitors[].series.title
        for c in comp.get("competitors") or []:
            title = ((c.get("series") or {}).get("title") or "").lower()
            for name, num in ROUND_NAME_MAP.items():
                if name in title:
                    return num

        return 0

    def _extract_series_info(
        self, pair: frozenset, games: list[dict], inferred_round: int = 0
    ) -> dict | None:
        """Build a structured series dict from a group of games with the same matchup."""
        teams = list(pair)
        if len(teams) != 2:
            return None

        # Use the latest game as reference for team metadata
        ref_game = max(games, key=lambda e: e.get("date", ""))
        ref_comp = (ref_game.get("competitions") or [{}])[0]
        ref_competitors = ref_comp.get("competitors", [])

        # Try to get round from ESPN series/notes fields first (future-proof)
        round_num = self._detect_round_from_event(ref_game)

        # Fall back to bracket inference (primary path when ESPN omits series data)
        if not round_num:
            round_num = inferred_round

        if not round_num:
            return None

        # Determine conference
        if round_num == 4:
            conference = "Finals"
        else:
            conf_a = TEAM_CONFERENCES.get(teams[0], "")
            conf_b = TEAM_CONFERENCES.get(teams[1], "")
            if conf_a and conf_a == conf_b:
                conference = conf_a
            elif conf_a:
                conference = conf_a
            else:
                conference = conf_b or "Unknown"

        # Gather team data (abbr, name, logo) and seeds
        team_data: dict[str, dict] = {}
        for comp in ref_competitors:
            t = comp.get("team", {})
            abbr = t.get("abbreviation", "")
            if not abbr:
                continue
            seed = (comp.get("curatedRank") or {}).get("current") or 99
            team_data[abbr] = {
                "abbr": abbr,
                "name": t.get("displayName") or t.get("name") or abbr,
                "logo": _get_logo(t),
                "seed": seed,
            }

        # Count wins per team from completed games
        wins: dict[str, int] = {t: 0 for t in teams}
        games_list: list[dict] = []
        for event in sorted(games, key=lambda e: e.get("date", "")):
            comp0 = (event.get("competitions") or [{}])[0]
            comps = comp0.get("competitors", [])
            status = comp0.get("status", {})
            state = status.get("type", {}).get("state", "")

            home_comp = next((c for c in comps if c.get("homeAway") == "home"), {})
            away_comp = next((c for c in comps if c.get("homeAway") == "away"), {})

            home_abbr = home_comp.get("team", {}).get("abbreviation", "")
            away_abbr = away_comp.get("team", {}).get("abbreviation", "")

            # Count wins for completed games
            if state == "post":
                for comp in comps:
                    if comp.get("winner"):
                        abbr = comp.get("team", {}).get("abbreviation", "")
                        if abbr in wins:
                            wins[abbr] += 1

            games_list.append({
                "game_id": event.get("id"),
                "date": event.get("date"),
                "game_state": state,
                "status_detail": status.get("type", {}).get("shortDetail", ""),
                "home_abbr": home_abbr,
                "away_abbr": away_abbr,
                "home_score": _parse_score(home_comp.get("score")),
                "away_score": _parse_score(away_comp.get("score")),
            })

        # Identify team1 (lower seed / higher-seeded = lower number) and team2
        seed_a = team_data.get(teams[0], {}).get("seed", 99)
        seed_b = team_data.get(teams[1], {}).get("seed", 99)
        if seed_a <= seed_b:
            team1_abbr, team2_abbr = teams[0], teams[1]
        else:
            team1_abbr, team2_abbr = teams[1], teams[0]

        t1 = team_data.get(team1_abbr, {"abbr": team1_abbr, "name": team1_abbr, "logo": "", "seed": 99})
        t2 = team_data.get(team2_abbr, {"abbr": team2_abbr, "name": team2_abbr, "logo": "", "seed": 99})

        return {
            "team1_abbr": team1_abbr,
            "team1_name": t1["name"],
            "team1_logo": t1["logo"],
            "team1_seed": t1["seed"],
            "team1_wins": wins.get(team1_abbr, 0),
            "team2_abbr": team2_abbr,
            "team2_name": t2["name"],
            "team2_logo": t2["logo"],
            "team2_seed": t2["seed"],
            "team2_wins": wins.get(team2_abbr, 0),
            "round": round_num,
            "conference": conference,
            "games": games_list,
            # min_seed used for slot ordering within a round/conference group
            "_min_seed": min(t1["seed"], t2["seed"]),
            "_pair": pair,
        }

    def _assign_bracket_keys(self, series_list: list[dict]) -> dict[str, dict]:
        """
        Assign bracket keys (r1_east_1 etc.) to each series.

        Slot ordering within a round/conference group uses the minimum seed
        (1v8 → slot 1, 2v7 → slot 2, 3v6 → slot 3, 4v5 → slot 4).
        Falls back to alphabetical team order when seeds are unavailable.
        """
        # Group by (round, conference)
        groups: dict[tuple, list[dict]] = {}
        for series in series_list:
            key = (series["round"], series["conference"])
            groups.setdefault(key, []).append(series)

        result: dict[str, dict] = {}

        for (round_num, conference), group in groups.items():
            group.sort(key=lambda s: (s["_min_seed"], s["team1_abbr"]))

            for slot_idx, series in enumerate(group, 1):
                if round_num == 4:
                    bracket_key = "r4_final"
                elif round_num == 3:
                    bracket_key = "r3_east_cf" if conference == "Eastern" else "r3_west_cf"
                elif round_num == 2:
                    conf_abbr = "east" if conference == "Eastern" else "west"
                    bracket_key = f"r2_{conf_abbr}_{slot_idx}"
                elif round_num == 1:
                    conf_abbr = "east" if conference == "Eastern" else "west"
                    bracket_key = f"r1_{conf_abbr}_{slot_idx}"
                else:
                    continue

                if bracket_key in SERIES_MAP:
                    result[bracket_key] = series

        return result

    # -------------------------------------------------------------------------
    # Build the final data dict consumed by sensors
    # -------------------------------------------------------------------------
    def _build_data(self, series_by_key: dict[str, dict]) -> dict[str, Any]:
        local_tz = get_time_zone(self.hass.config.time_zone)
        now_utc = datetime.now(timezone.utc)

        data: dict[str, Any] = {}

        # Populate from detected series
        for bracket_key, series in series_by_key.items():
            t1_wins = series["team1_wins"]
            t2_wins = series["team2_wins"]
            t1 = series["team1_abbr"]
            t2 = series["team2_abbr"]

            if t1 == "TBD" or t2 == "TBD" or (t1_wins == 0 and t2_wins == 0):
                series_status = "TBD"
            elif t1_wins == 4 or t2_wins == 4:
                if t1_wins > t2_wins:
                    series_status = f"{t1} wins {t1_wins}-{t2_wins}"
                else:
                    series_status = f"{t2} wins {t2_wins}-{t1_wins}"
            elif t1_wins > t2_wins:
                series_status = f"{t1} leads {t1_wins}-{t2_wins}"
            elif t2_wins > t1_wins:
                series_status = f"{t2} leads {t2_wins}-{t1_wins}"
            else:
                series_status = f"Tied {t1_wins}-{t2_wins}"

            series_complete = t1_wins == 4 or t2_wins == 4

            today_game = self._compute_today_game(series["games"], local_tz)
            next_game = self._compute_next_game(series["games"], now_utc)

            data[bracket_key] = {
                **{k: v for k, v in series.items() if not k.startswith("_")},
                "series_status": series_status,
                "series_complete": series_complete,
                "today_game": today_game,
                "today_game_id": today_game.get("game_id") if today_game else None,
                "next_game": next_game,
                "next_game_id": next_game.get("game_id") if next_game else None,
                "next_game_time": next_game.get("date") if next_game else None,
            }

        # Ensure all bracket keys exist (even for TBD series not yet started)
        for meta_key in SERIES_MAP:
            if meta_key not in data:
                data[meta_key] = self._empty_series(meta_key)

        return data

    # -------------------------------------------------------------------------
    # Today's game / next game helpers
    # -------------------------------------------------------------------------
    def _compute_today_game(self, games: list[dict], local_tz) -> dict | None:
        if not games:
            return None

        today = datetime.now(local_tz).date()

        # Live game takes priority
        for g in games:
            if g.get("game_state") == "in":
                return g

        # Game scheduled for today (pre or live)
        for g in games:
            date_str = g.get("date")
            if not date_str:
                continue
            try:
                dt_utc = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                dt_local = dt_utc.astimezone(local_tz)
                if dt_local.date() == today and g.get("game_state") in ("pre", "in"):
                    return g
            except Exception:
                continue

        return None

    def _compute_next_game(self, games: list[dict], now_utc: datetime) -> dict | None:
        if not games:
            return None

        future: list[tuple[datetime, dict]] = []
        for g in games:
            if g.get("game_state") != "pre":
                continue
            date_str = g.get("date")
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if dt > now_utc:
                    future.append((dt, g))
            except Exception:
                continue

        if not future:
            return None
        future.sort(key=lambda x: x[0])
        return future[0][1]

    @staticmethod
    def _empty_series(bracket_key: str) -> dict[str, Any]:
        meta = SERIES_MAP.get(bracket_key, {})
        return {
            "team1_abbr": "TBD",
            "team1_name": "TBD",
            "team1_logo": "",
            "team1_seed": 0,
            "team1_wins": 0,
            "team2_abbr": "TBD",
            "team2_name": "TBD",
            "team2_logo": "",
            "team2_seed": 0,
            "team2_wins": 0,
            "round": meta.get("round", 0),
            "conference": meta.get("conference", ""),
            "games": [],
            "series_status": "TBD",
            "series_complete": False,
            "today_game": None,
            "today_game_id": None,
            "next_game": None,
            "next_game_id": None,
            "next_game_time": None,
        }
