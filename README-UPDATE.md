# 🏀 NBA Playoffs Dashboard — Notes de développement

Ce document décrit les décisions d'architecture et les adaptations effectuées pour créer l'intégration NBA à partir du projet NHL d'origine.

Pour l'installation et la documentation complète, voir le README principal :
👉 [README.md](README.md)

---

## 🔄 Origine du projet

Ce projet est une adaptation de [nhl_playoffs_ha_dashboard](https://github.com/astlgit/nhl_playoffs_ha_dashboard).  
L'architecture (coordinateurs, sensors, dashboard Lovelace) est identique ; seuls l'API source, le parsing des données, et quelques détails de logique métier ont changé.

---

## 🆕 Nouveautés — Intégration NBA (v1.0)

### Intégration Home Assistant (`custom_components/nba_playoffs/`)

- **API ESPN** — remplace l'API NHL. Un seul endpoint retourne tous les matchs playoffs.
- **Détection automatique des séries** — les séries sont reconstruites dynamiquement en groupant les matchs par paire d'équipes, puis assignées aux slots du bracket par numéro de tête de série.
- **Quarters NBA** — affichage Q1–Q4, OT, 2OT au lieu des périodes NHL.
- **États ESPN** — `pre` / `in` / `post` remplacent `FUT` / `LIVE` / `FINAL` / `OFF`.
- **Intervals adaptatifs** — 10 s en direct, 30 s pré-match, 5 min / 30 min hors match.
- **Saison par année** — la config utilise un entier (`2025`, `2026`) au lieu du format `20232024`.

### Dashboard Lovelace (`lovelace/nba_playoffs_dashboard.yaml`)

- Même layout 5 colonnes que le dashboard NHL.
- Couleurs NBA : bleu Lakers/Clippers (Western), rouge Bulls/Heat (Eastern), or (NBA Finals).
- Live card adapté aux quarters : affiche `Q3 · 5:23` au lieu de `2nd · 5:23`.
- Plus d'indicateurs PP/EN (hockey uniquement).
- Bascule automatique entre `nba_series_card` et `nba_live_card` selon l'état du sensor.

---

## 🏗 Différences architecturales clés

### Récupération des données

| Aspect | NHL | NBA |
|--------|-----|-----|
| Endpoint bracket | `api-web.nhle.com/v1/playoff-bracket/{year}` | — |
| Endpoint série | `api-web.nhle.com/v1/schedule/playoff-series/{season}/{letter}` | — |
| Endpoint scoreboard | `api-web.nhle.com/v1/schedule/now` | `site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=...` |
| Lettres de série | Fournies explicitement par l'API (A–O) | Déduites du matchup d'équipes |

### Détection des séries (NBA)

L'API ESPN ne fournit pas de structure bracket explicite. La `SeriesCoordinator` :

1. Récupère tous les matchs playoffs de la fenêtre de dates (`YYYYMMDD-YYYYMMDD`)
2. Groupe les matchs par paire d'équipes (`frozenset` d'abréviations)
3. Extrait le round depuis le champ `series.title` (`"First Round"`, `"Conference Semifinals"`, …)
4. Détermine la conférence via un mapping statique `abbrev → Eastern/Western`
5. Trie les séries dans un round/conférence par numéro de tête de série (`curatedRank.current`)
6. Assigne les clés de bracket (`r1_east_1`, `r1_east_2`, …) dans cet ordre

### Données live (NBA)

ESPN n'expose pas d'endpoint single-game live public. La `LiveCoordinator` refetch le scoreboard du jour et filtre par `game_id`. Cela garantit un format de réponse identique à celui que parse la `SeriesCoordinator`.

---

## 📡 Sensors créés

### Series Sensors (15)
```
sensor.nba_series_r1_east_1 … sensor.nba_series_r4_final
```
État = `series_status` (ex. `"BOS leads 2-1"`).

### Live Sensors (15)
```
sensor.nba_live_r1_east_1 … sensor.nba_live_r4_final
```
État = `normal` / `live` / `final` / `pre`.

---

## 🔧 Debug

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.nba_playoffs: debug
```

---

## 📌 Améliorations futures

- Bracket endpoint ESPN dédié (si disponible publiquement) pour éviter l'inférence des séries
- Stats par joueur (points, rebonds, passes)
- Notification automatique sur changement de score
- Vue compacte mobile
- Sélecteur multi-saison dans le dashboard
