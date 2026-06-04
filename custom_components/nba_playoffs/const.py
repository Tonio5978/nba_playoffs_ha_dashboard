from __future__ import annotations

import logging
from datetime import timedelta

# ---------------------------------------------------------------------------
# Domain + Logging
# ---------------------------------------------------------------------------
DOMAIN = "nba_playoffs"
LOGGER = logging.getLogger(f"custom_components.{DOMAIN}")

# ---------------------------------------------------------------------------
# Config Options
# ---------------------------------------------------------------------------
CONF_SEASON_MODE = "season_mode"
CONF_MANUAL_SEASON = "manual_season"
CONF_DEBUG = "debug"

SEASON_MODE_CURRENT = "current"
SEASON_MODE_MANUAL = "manual"

DEFAULT_SEASON_MODE = SEASON_MODE_CURRENT
DEFAULT_MANUAL_SEASON = "2025"  # Full-data test season

# ---------------------------------------------------------------------------
# Coordinator update intervals
# ---------------------------------------------------------------------------
UPDATE_INTERVAL = timedelta(minutes=5)

# ---------------------------------------------------------------------------
# Coordinator Keys
# ---------------------------------------------------------------------------
SERIES_COORDINATOR = "series"
LIVE_COORDINATOR = "live"

# ---------------------------------------------------------------------------
# Series Letters (A–O) — identical structure to NHL (15 series)
# ---------------------------------------------------------------------------
SERIES_LETTERS = [
    "A", "B", "C", "D",
    "E", "F", "G", "H",
    "I", "J", "K", "L",
    "M", "N", "O",
]

# ---------------------------------------------------------------------------
# ESPN NBA API Endpoints
# ---------------------------------------------------------------------------
API_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

# ---------------------------------------------------------------------------
# NBA round name → round number
# ---------------------------------------------------------------------------
ROUND_NAME_MAP = {
    "first round": 1,
    "conference semifinals": 2,
    "conference finals": 3,
    "nba finals": 4,
}

# ---------------------------------------------------------------------------
# NBA team abbreviation → conference (stable mapping)
# ---------------------------------------------------------------------------
TEAM_CONFERENCES = {
    # Eastern Conference
    "ATL": "Eastern", "BOS": "Eastern", "BKN": "Eastern", "CHA": "Eastern",
    "CHI": "Eastern", "CLE": "Eastern", "DET": "Eastern", "IND": "Eastern",
    "MIA": "Eastern", "MIL": "Eastern", "NYK": "Eastern", "ORL": "Eastern",
    "PHI": "Eastern", "TOR": "Eastern", "WAS": "Eastern",
    # Western Conference
    "DAL": "Western", "DEN": "Western", "GSW": "Western", "HOU": "Western",
    "LAC": "Western", "LAL": "Western", "MEM": "Western", "MIN": "Western",
    "NOP": "Western", "OKC": "Western", "PHX": "Western", "POR": "Western",
    "SAC": "Western", "SAS": "Western", "UTA": "Western",
    # Alternative abbreviations used by ESPN
    "GS":  "Western", "NO":  "Western", "NY":  "Eastern", "SA":  "Western",
    "BK":  "Eastern",
}
