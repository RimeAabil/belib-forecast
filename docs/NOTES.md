# Belib' Forecast — Notes

Data source, data-quality issues, design decisions, open questions and infrastructure.
These notes feed the README, the cleaning step and future blog posts.

---

## Data source

- **Dataset:** Paris open data, `belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel`
- **Portal page:** https://opendata.paris.fr/explore/dataset/belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel/
- **Endpoint used:** `https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel/exports/json` (whole dataset, no pagination, no key)
- **Licence:** open data from the Ville de Paris; credit the source in the README and posts
- **One row = one charging point** (a plug), not a station

### Fields

| Field | Meaning | Notes |
|---|---|---|
| `id_pdc` | Charging point ID, e.g. `FR*V75*E9006*02*2` | Main key |
| `statut_pdc` | Current status | Target of the forecast |
| `last_updated` | When the point last reported | True event time |
| `adresse_station` | Station address | Used to group points into stations |
| `arrondissement` | e.g. `06e Arrondissement`, `Paris centre` | |
| `coordonneesxy` | `{lat, lon}` | Nested; flattened by the collector |
| `code_insee_commune` | `75056` (Paris) | |
| `url_description_pdc` | Link to the static dataset | Charger power, connector type |

### Statuses seen

Disponible · Occupé (en charge) · Mise en service planifiée · En maintenance · Inconnu
(Documented but not seen yet: Pas implémenté, En cours de mise en service, Supprimé, Réservé)

### Key facts

- **No history provided:** the feed only shows the current state, so we collect it ourselves.
- **Update rate:** points report within minutes; with 5-minute polling, `first_seen_at` is 1–5 min after `last_updated`.

---

## Data-quality log

| Date found | Issue | Impact | Handling |
|---|---|---|---|
| 25 Nov | Some points have a `last_updated` weeks old (e.g. `Inconnu` since 9 Oct) | Broken or unsupervised points | Flag stale points; exclude from training |
| 25 Nov | A few events repeat the same status with a new `last_updated` (17 of ~313 in the first test) | Not real transitions | Keep only events where status ≠ previous status (`LAG`) |
| 26 Nov | **Mass update at 03:35 UTC:** 2,048 of 2,104 points "changed" at once | ~2,000 fake events; would distort session counts and durations | Same `LAG` filter. Check whether it repeats |
| 26 Nov | ~87 points with no address, arrondissement or coordinates (IDs like `FR*V75*EPX18*65*6*1`) | Can't be mapped | Probably the "Mise en service planifiée" points (83 seen). Hidden on map, excluded from `/stations` and from training |
| 26 Nov | Arrondissements 1–4 appear as one value: "Paris centre" | `/arrondissements` returns one entry for them | Normal since 2020; kept as is |
| 26 Nov | Short sessions exist (e.g. 13 min, then a new car 4 min later) | Very short states can fall between two polls | Accept with 5-min polling; consider 2–3 min later if API limits allow |
| 26 Nov | Two extra rows in `runs.csv` (01:02, 09:22) | None | Manual runs; harmless |

---

## Design decisions

| Date | Decision | Why |
|---|---|---|
| 25 Nov | Belib' EV charging instead of Vélib' or a paper recommender | Little existing work; no users needed; real-time data; useful topic |
| 25 Nov | **Event-based storage** (store changes, not snapshots) | ~14k rows/day instead of ~600k; full history can be rebuilt |
| 25 Nov | Primary key `(id_pdc, last_updated, statut)` + `INSERT OR IGNORE` | Idempotent collection, no duplicates |
| 25 Nov | `collection_runs` / `runs.csv` log of every run | First monitoring: detect errors and silent stops |
| 25 Nov | Poll every **5 minutes** | Compromise between missing short states and API call limits |
| 25 Nov | Use `last_updated` as event time, not `first_seen_at` | `first_seen_at` includes our polling delay |
| 25 Nov | uv for environments and dependencies | Fast, lock file, standard in modern projects |
| 25 Nov | Collection on **GitHub Actions**, data on an orphan **`data` branch** | Free, no server, no card; code and data separated |
| 25 Nov | Run-once script + external scheduler (instead of a `while True` loop) | Scheduler decides when, job decides what |
| 25 Nov | One events file per day (`events/YYYY-MM-DD.csv`) | Small files, easy to load |
| 25 Nov | Trigger from **cron-job.org** via `workflow_dispatch` | GitHub's `schedule` never ran |
| 25 Nov | Public repo | Unlimited Actions minutes; portfolio project |
| 26 Nov | API cache of 60 s + serve last known data if the source fails | Protects the source; graceful degradation |
| 26 Nov | CORS allows only the frontend's origin and GET | Least privilege |
| 26 Nov | React + Vite + Leaflet with OpenStreetMap tiles | Free, light, standard |
| 27 Nov | Group points into **stations** by `adresse_station` | Drivers care about a station; stacked circles hid information; less data sent |
| 27 Nov | Keep `/points` alongside `/stations` | Points differ (power, connector); detail still needed |
| 27 Nov | Station color: green if ≥1 free, red if all working points busy, grey if none working | Answers the driver's question at a glance |
| 27 Nov | Circle radius ∝ √(number of points) | Circle area grows proportionally to station size |
| 27 Nov | Grouping done in the backend, not the frontend | One place for the logic; reusable by other clients |
| 27 Nov | Likely forecast target: "at least one point free at this station in 30 min" | More useful to drivers and less noisy than a single point |

---

## Open questions

- [ ] Does the mass update happen every night? At what time?
  - 26 Nov: yes, 03:35 UTC (2,048 events)
  - 27 Nov: _check `runs.csv` around 03:30–03:40 UTC_
- [ ] Are the points without a location exactly the "Mise en service planifiée" ones? (check one ID in `state/latest.csv`)
- [x] How are points grouped into stations? → by `adresse_station` (same coordinates)
- [ ] Do all points at an address really belong to one station? (two stations at the same address?)
- [ ] Distribution of charging-session durations: are short sessions (~13 min) fast chargers or failed attempts?
- [ ] How many points stay broken (`En maintenance`, `Inconnu`) for long periods?
- [ ] Which forecast horizon is most useful: 15, 30 or 60 minutes?
- [ ] Weekday vs weekend: how different are the patterns?
- [ ] Does the Paris API have call limits? (matters if polling becomes more frequent)

---

## Infrastructure

### Collection pipeline

```
cron-job.org (every 5 min)
  → POST GitHub API workflow_dispatch (token)
    → .github/workflows/collect.yml
      → src/belib_forecast/collect_once.py
        → Paris open-data API
      → commit CSVs to the `data` branch
```

### Files on the `data` branch

| File | Content | Written |
|---|---|---|
| `events/YYYY-MM-DD.csv` | New events: `id_pdc, statut, last_updated, first_seen_at` | Appended each run |
| `state/latest.csv` | Last known status of each point | Rewritten each run |
| `points.csv` | Static info: address, arrondissement, coordinates | Rewritten each run |
| `runs.csv` | Run log: time, points fetched, new events, error | Appended each run |

### Local app

| Part | Command | URL |
|---|---|---|
| API | `uv run fastapi dev src/belib_forecast/api.py` | http://127.0.0.1:8000 (docs: `/docs`) |
| Frontend | `cd frontend && npm run dev` | http://localhost:5173 |

### Token

- Fine-grained, repo `belib-forecast` only, permission Actions: read and write
- **Expires 23 Feb 2027.** Renew a few days before and update the header on cron-job.org.
- Never commit it or show it in screenshots.

### Weekly check

- `runs.csv` has recent rows, about every 5 minutes
- the `error` column is empty
- `n_new_events` is not stuck at 0
- cron-job.org history shows 204 responses