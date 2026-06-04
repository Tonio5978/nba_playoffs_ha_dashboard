# 🏀 NBA Playoffs Dashboard
Home Assistant custom integration and Lovelace dashboard for NBA Playoffs tracking — with live game overlays, real-time scores, and a modern bracket layout.

---

# 📦 Repository Contents

- `custom_components/nba_playoffs/` — Home Assistant integration
- `custom_components/nhl_playoffs/` — Original NHL integration (kept for reference)
- `lovelace/nba_playoffs_dashboard.yaml` — NBA Lovelace dashboard
- `lovelace/nhl_playoffs_dashboard.yaml` — Original NHL dashboard
- `hacs.json` — HACS metadata

---

# ⚙️ Installation

## 🔧 Manual Install
1. Copy `custom_components/nba_playoffs/` into:
   ```
   config/custom_components/
   ```
2. Restart Home Assistant.
3. Install required Lovelace custom card via HACS:
   - `button-card`
4. Add the **NBA Playoffs** integration in **Settings → Devices & Services → Add Integration**.
5. Paste the dashboard YAML from:
   ```
   lovelace/nba_playoffs_dashboard.yaml
   ```

---

# 🧩 Integration Setup

After installation:

1. Go to **Settings → Devices & Services → Integrations**
2. Search for and add **NBA Playoffs**
3. Select your season mode:
   - **Current season** — auto-detects the year from today's date
   - **Manual season** — enter a year (e.g. `2025`) to test with historical data
4. The integration creates 30 sensors:
   - 15 series sensors (`sensor.nba_series_*`)
   - 15 live sensors (`sensor.nba_live_*`)

### 🔍 Test with Historical Data

To test without waiting for the next playoffs: choose **Manual season** mode and enter `2025` — this uses the 2025 playoffs data from the ESPN API.

---

# 📡 Sensor Naming

## Series Sensors
```
sensor.nba_series_r1_east_1    # (1) vs (8) Eastern
sensor.nba_series_r1_east_2    # (2) vs (7) Eastern
sensor.nba_series_r1_east_3    # (3) vs (6) Eastern
sensor.nba_series_r1_east_4    # (4) vs (5) Eastern
sensor.nba_series_r1_west_1    # (1) vs (8) Western
sensor.nba_series_r1_west_2    # (2) vs (7) Western
sensor.nba_series_r1_west_3    # (3) vs (6) Western
sensor.nba_series_r1_west_4    # (4) vs (5) Western
sensor.nba_series_r2_east_1    # Conference Semifinals Eastern
sensor.nba_series_r2_east_2
sensor.nba_series_r2_west_1    # Conference Semifinals Western
sensor.nba_series_r2_west_2
sensor.nba_series_r3_east_cf   # Conference Finals Eastern
sensor.nba_series_r3_west_cf   # Conference Finals Western
sensor.nba_series_r4_final     # NBA Finals
```

## Live Sensors
```
sensor.nba_live_r1_east_1
sensor.nba_live_r1_east_2
...
sensor.nba_live_r4_final
```

## Series Sensor Attributes
| Attribute | Description |
|-----------|-------------|
| `team1_abbrev` | Top-seed team abbreviation |
| `team1_name` | Full team name |
| `team1_logo` | ESPN CDN logo URL |
| `team1_seed` | Playoff seed number |
| `team1_wins` | Wins in the series |
| `team2_abbrev` | Bottom-seed team abbreviation |
| `team2_name` | Full team name |
| `team2_logo` | ESPN CDN logo URL |
| `team2_seed` | Playoff seed number |
| `team2_wins` | Wins in the series |
| `series_status` | e.g. `"BOS leads 2-1"` |
| `series_complete` | `true` once a team reaches 4 wins |
| `games_list` | List of all games in the series |
| `next_game_time` | ISO timestamp of next scheduled game |
| `today_game_id` | ESPN event ID of today's game |

## Live Sensor Attributes
| Attribute | Description |
|-----------|-------------|
| `game_state` | `pre` / `in` / `post` |
| `home_team` / `away_team` | Full team name |
| `home_abbr` / `away_abbr` | Team abbreviation |
| `home_score` / `away_score` | Current score |
| `quarter` | Current period number (1–4, 5=OT…) |
| `quarter_display` | `Q1`–`Q4`, `OT`, `2OT`… |
| `time_remaining` | Clock display, e.g. `"5:23"` |
| `venue` | Arena name |
| `broadcasts` | List of broadcast networks |
| `start_time` | ISO timestamp of tip-off |

---

# 🖥️ Dashboard Installation

## Prerequisites
- `button-card` installed via HACS
- NBA Playoffs integration configured

## Method 1: UI Dashboard Editor (Recommended)
1. Create a new dashboard in **Settings → Dashboards**
2. Open **Raw Configuration Editor**
3. Paste the contents of `lovelace/nba_playoffs_dashboard.yaml`
4. Save and exit.

## Method 2: YAML Mode
1. Enable YAML mode in `configuration.yaml`:
   ```yaml
   lovelace:
     mode: yaml
   ```
2. Add the dashboard YAML to your Lovelace config.
3. Restart Home Assistant.

---

# 🧱 Dashboard Layout

The dashboard uses a **5-column bracket layout**:

- Column 1 → Western Conference Round 1
- Column 2 → Western Conference Semifinals + Conference Finals
- Column 3 → NBA Finals (center)
- Column 4 → Eastern Conference Semifinals + Conference Finals
- Column 5 → Eastern Conference Round 1

Each series card:
- Shows team logos, seed numbers, team names, series wins
- Rotates between series status and next game time
- **Switches automatically to a live overlay** when a game is in progress (score, quarter, clock)

### Live Card States
- `pre` → Shows tip-off time
- `in` → Shows live score, quarter, and time remaining
- `post` → Shows final score

---

# 🛠 Architecture Notes

### API Source
Data comes from the **ESPN NBA public API** (no API key required):
```
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard
```

### Series Detection
The integration fetches all playoff games for the season's date range, groups them by team matchup, then assigns each series to a bracket slot using seed numbers. Conference is determined from a built-in team→conference mapping.

### Coordinators
- `series_coordinator.py` → polls every 5 minutes for series-level data (wins, schedule, team info)
- `live_coordinator.py` → per-series adaptive polling: 10s live, 30s pre-game, up to 30min idle

### Polling Intervals
| Game State | Interval |
|------------|----------|
| Live (`in`) | 10 seconds |
| Pre-game < 30 min | 30 seconds |
| Pre-game < 2 hours | 5 minutes |
| Pre-game > 2 hours | 30 minutes |
| Post-game / no game | 1 hour |

---

# 🔍 Debug & Troubleshooting

### Enable Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.nba_playoffs: debug
```

### Common Issues
| Problem | Solution |
|---------|----------|
| Sensors show "TBD" | Playoffs haven't started yet, or try Manual season `2025` |
| Logos not loading | ESPN CDN URLs — check your HA instance can reach the internet |
| Series in wrong bracket slot | Seeds may be unavailable; series fall back to alphabetical ordering |
| Integration not found | Verify the folder is `custom_components/nba_playoffs/` and restart HA |

---

# 🔄 Differences: NHL vs NBA

| Aspect | NHL | NBA |
|--------|-----|-----|
| API | `api-web.nhle.com` | `site.api.espn.com` |
| Game periods | 3 periods + OT | 4 quarters + OT |
| Game states | `LIVE`, `PRE`, `FINAL`, `OFF` | `in`, `pre`, `post` |
| Series mapping | Explicit letters (A–O) from API | Inferred from team matchups |
| Live interval | 5 seconds | 10 seconds |

---

# 📜 License
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
