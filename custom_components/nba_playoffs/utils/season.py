from __future__ import annotations

from datetime import datetime


def get_current_season() -> int:
    """Return the year of the current or upcoming NBA playoffs.

    NBA Playoffs run April–June. If today is Oct–Dec, we're in the season
    whose playoffs happen next year.
    """
    now = datetime.now()
    month = now.month
    year = now.year

    if month >= 10:
        return year + 1
    return year


def get_playoffs_dates(year: int) -> tuple[str, str]:
    """Return (start_date, end_date) in YYYYMMDD format for the given playoffs year.

    NBA Playoffs start around April 15 and end around June 25.
    Using a wide window ensures we catch all games.
    """
    return (f"{year}0401", f"{year}0630")
