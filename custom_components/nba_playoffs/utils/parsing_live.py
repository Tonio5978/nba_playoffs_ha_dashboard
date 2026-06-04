from __future__ import annotations

from typing import Any, Dict


def _quarter_display(period: int | None) -> str:
    """Convert ESPN period number to display string (Q1–Q4, OT, 2OT…)."""
    if not period:
        return ""
    if period <= 4:
        return f"Q{period}"
    ot = period - 4
    return "OT" if ot == 1 else f"{ot}OT"


def parse_live_game(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an ESPN scoreboard event into a stable HA-friendly structure."""
    if not event:
        return _empty_game()

    competition = (event.get("competitions") or [{}])[0]
    status = competition.get("status", {})
    status_type = status.get("type", {})

    # ESPN states: "pre" | "in" | "post"
    game_state = status_type.get("state", "")
    status_detail = status_type.get("shortDetail", "")

    competitors = competition.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})

    home_team = home.get("team", {})
    away_team = away.get("team", {})

    home_abbr = home_team.get("abbreviation", "")
    away_abbr = away_team.get("abbreviation", "")

    home_score = _parse_score(home.get("score"))
    away_score = _parse_score(away.get("score"))

    period = status.get("period", 0) or 0
    clock = status.get("displayClock", "") or ""

    # Determine winner for completed games
    winner = None
    if game_state == "post":
        if home_score > away_score:
            winner = home_abbr
        elif away_score > home_score:
            winner = away_abbr

    # Logos — ESPN CDN fallback
    home_logo = _get_logo(home_team)
    away_logo = _get_logo(away_team)

    # Broadcast names
    broadcasts = []
    for b in competition.get("broadcasts", []):
        names = b.get("names") or b.get("market", {}).get("names", [])
        if isinstance(names, list):
            broadcasts.extend(names)
        elif isinstance(names, str):
            broadcasts.append(names)

    venue = competition.get("venue", {}).get("fullName", "")

    return {
        "game_id": event.get("id"),
        "game_state": game_state,
        "status_detail": status_detail,
        "home_team": home_team.get("displayName") or home_abbr,
        "home_abbr": home_abbr,
        "home_score": home_score,
        "home_logo": home_logo,
        "away_team": away_team.get("displayName") or away_abbr,
        "away_abbr": away_abbr,
        "away_score": away_score,
        "away_logo": away_logo,
        "quarter": period,
        "quarter_display": _quarter_display(period),
        "time_remaining": clock,
        "winner": winner,
        "venue": venue,
        "broadcasts": broadcasts,
        "start_time": event.get("date"),
    }


def _parse_score(score_str) -> int:
    try:
        return int(score_str)
    except (ValueError, TypeError):
        return 0


def _get_logo(team_data: dict) -> str:
    # Try logos array first (highest resolution), then direct logo field
    logos = team_data.get("logos") or []
    if logos and isinstance(logos, list):
        return logos[0].get("href", "") or logos[0].get("url", "")
    logo = team_data.get("logo", "")
    if logo:
        return logo
    abbr = team_data.get("abbreviation", "").lower()
    if abbr:
        return f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr}.png"
    return ""


def _empty_game() -> Dict[str, Any]:
    return {
        "game_id": None,
        "game_state": "",
        "status_detail": "",
        "home_team": "",
        "home_abbr": "",
        "home_score": 0,
        "home_logo": None,
        "away_team": "",
        "away_abbr": "",
        "away_score": 0,
        "away_logo": None,
        "quarter": 0,
        "quarter_display": "",
        "time_remaining": "",
        "winner": None,
        "venue": "",
        "broadcasts": [],
        "start_time": None,
    }
