from __future__ import annotations

# Maps human-readable bracket keys to series metadata.
# Letter assignment mirrors the NHL convention (A–O, 15 series total):
#   A–D  = Round 1 Eastern (1v8, 2v7, 3v6, 4v5)
#   E–H  = Round 1 Western
#   I–J  = Round 2 Eastern (Conference Semifinals)
#   K–L  = Round 2 Western
#   M    = Conference Finals Eastern
#   N    = Conference Finals Western
#   O    = NBA Finals

SERIES_MAP = {
    # ------------------------------------------------------------------
    # ROUND 1 — EASTERN
    # ------------------------------------------------------------------
    "r1_east_1": {
        "name": "R1_EAST_1",
        "series_letter": "A",
        "round": 1,
        "conference": "Eastern",
    },
    "r1_east_2": {
        "name": "R1_EAST_2",
        "series_letter": "B",
        "round": 1,
        "conference": "Eastern",
    },
    "r1_east_3": {
        "name": "R1_EAST_3",
        "series_letter": "C",
        "round": 1,
        "conference": "Eastern",
    },
    "r1_east_4": {
        "name": "R1_EAST_4",
        "series_letter": "D",
        "round": 1,
        "conference": "Eastern",
    },

    # ------------------------------------------------------------------
    # ROUND 1 — WESTERN
    # ------------------------------------------------------------------
    "r1_west_1": {
        "name": "R1_WEST_1",
        "series_letter": "E",
        "round": 1,
        "conference": "Western",
    },
    "r1_west_2": {
        "name": "R1_WEST_2",
        "series_letter": "F",
        "round": 1,
        "conference": "Western",
    },
    "r1_west_3": {
        "name": "R1_WEST_3",
        "series_letter": "G",
        "round": 1,
        "conference": "Western",
    },
    "r1_west_4": {
        "name": "R1_WEST_4",
        "series_letter": "H",
        "round": 1,
        "conference": "Western",
    },

    # ------------------------------------------------------------------
    # ROUND 2 — CONFERENCE SEMIFINALS
    # ------------------------------------------------------------------
    "r2_east_1": {
        "name": "R2_EAST_1",
        "series_letter": "I",
        "round": 2,
        "conference": "Eastern",
    },
    "r2_east_2": {
        "name": "R2_EAST_2",
        "series_letter": "J",
        "round": 2,
        "conference": "Eastern",
    },
    "r2_west_1": {
        "name": "R2_WEST_1",
        "series_letter": "K",
        "round": 2,
        "conference": "Western",
    },
    "r2_west_2": {
        "name": "R2_WEST_2",
        "series_letter": "L",
        "round": 2,
        "conference": "Western",
    },

    # ------------------------------------------------------------------
    # ROUND 3 — CONFERENCE FINALS
    # ------------------------------------------------------------------
    "r3_east_cf": {
        "name": "R3_EAST_CF",
        "series_letter": "M",
        "round": 3,
        "conference": "Eastern",
    },
    "r3_west_cf": {
        "name": "R3_WEST_CF",
        "series_letter": "N",
        "round": 3,
        "conference": "Western",
    },

    # ------------------------------------------------------------------
    # ROUND 4 — NBA FINALS
    # ------------------------------------------------------------------
    "r4_final": {
        "name": "R4_FINAL",
        "series_letter": "O",
        "round": 4,
        "conference": "Finals",
    },
}
