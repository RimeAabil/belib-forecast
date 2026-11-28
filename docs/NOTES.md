# Belib' Forecast — Notes

Data source, data-quality issues, analysis findings, design decisions, open questions and infrastructure.
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
- **Update rate:** points report within minutes; with 5-minute polling, `first_seen_at` is 1–5 minutes after `last_updated`.
- **Time zone:** times are stored in UTC; analyses use Paris time (`Europe/Paris`).

---

## Data-quality log

| Date found | Issue | Impact | Handling |
|---|---|---|---|
| 25 Nov | Some points have a `last_updated` weeks old (e.g. `Inconnu` since 9 Oct) | Broken or unsupervised points | Flag stale points; exclude from training |
| 25 Nov | Some events repeat the same status with a new `last_updated` | Not real transitions | Keep only events whose status differs from the previous one (`LAG` in SQL, `groupby` + `shift` in pandas) |
| 26 Nov | Mass update at 03:35 UTC: 2,048 of 2,104 points "changed" at once | About 2,000 fake events per occurrence | Same filter. Check whether it repeats every night |
| 26 Nov | About 87 points with no address, arrondissement or coordinates (IDs like `FR*V75*EPX18*65*6*1`) | Cannot be mapped | Probably the "Mise en service planifiée" points. Hidden on the map, excluded from `/stations` and from analysis |
| 26 Nov | Arrondissements 1–4 appear as one value: "Paris centre" | `/arrondissements` returns one entry for them | Normal since 2020; kept as is |
| 26 Nov | Short states exist (e.g. a 13-minute session, then a new car 4 minutes later) | Very short states can fall between two polls | Accepted with 5-minute polling |
| 26 Nov | Two extra rows in `runs.csv` (01:02, 09:22) | None | Manual runs; harmless |
| 28 Nov | **22% of events are same-status noise** (9,114 of 41,612) | Without cleaning, sessions would be split and durations distorted | Removed in the notebook before any analysis |
| 28 Nov | Event times can be months before collection started (first event of stale points) | A time-based analysis starting at the first event shows months of meaningless data | Every time-based analysis starts at the first collector run (`runs.csv`) |
| 28 Nov | Sessions of 0 minutes; a peak of sessions under 10 minutes | Not real charges: glitches or failed attempts | Sessions under 2 minutes treated as glitches; investigate further |
| 28 Nov | Longest session about 42 hours | Car left for two days, or point stuck on "Occupé" | Investigate; consider capping or flagging |

---

## Analysis findings (first pass, 25–28 Nov)

Data window: Wed 25 Nov evening → Sat 28 Nov midday (about 2.5 days). Notebook: `notebooks/01_eda.ipynb`.

### Charging sessions
- 13,772 complete sessions (sessions running at the start of collection or still running now are excluded).
- Median 2 h 26; mean 3 h 55 (pulled up by long stays).
- Three groups: under 10 minutes (glitches or failed attempts), 30 minutes to 3 hours (normal charges, peak around 1 hour), over 10 hours (about 11%, probably cars left overnight).

### Occupancy (share of working points occupied, every 15 minutes)
| Time (Paris) | Occupancy | Interpretation |
|---|---|---|
| 00:00 – 07:00 | flat, about 45–48% | Cars charging overnight |
| around 08:00 | lowest, 41–45% | Overnight cars leave before new drivers arrive |
| 12:00 – 13:00 | highest, 60–63% | Daytime activity |
| around 17:00 – 18:00 | dip, about 45–47% | Daytime drivers leave |
| 20:00 – 21:00 | second peak, 56–60% | Residents come home |

- The daily low is in the morning, not at night.
- Saturday morning reached about 35%, lower than weekday mornings (one observation; to confirm).
- Occupancy never dropped below about 35%.

### Reliability
- About 2,017 located points: 1,690 never broken (about 84%), 66 broken more than half the time, 50 broken the whole time.
- The 50 always-broken points match the 50 "En maintenance" points seen on the first day.

### Implications for the model
- Forecasting "at least one point free at a station in 30 minutes" makes sense: with a median of 2 h 26, a charge rarely starts and ends within 30 minutes.
- Promising features: current status, time already spent in that status, hour of day, day of week, recent reliability of the point.
- Exclude points without a location and points broken the whole time.

---

## Design decisions

| Date | Decision | Why |
|---|---|---|
| 25 Nov | Belib' EV charging instead of Vélib' or a paper recommender | Little existing work; no users needed; real-time data; useful topic |
| 25 Nov | Event-based storage (store changes, not snapshots) | About 14k rows/day instead of about 600k; full history can be rebuilt |
| 25 Nov | Primary key `(id_pdc, last_updated, statut)` + `INSERT OR IGNORE` | Idempotent collection, no duplicates |
| 25 Nov | `runs.csv` log of every collector run | First monitoring: detect errors and silent stops |
| 25 Nov | Poll every 5 minutes | Compromise between missing short states and API call limits |
| 25 Nov | Use `last_updated` as event time, not `first_seen_at` | `first_seen_at` includes the polling delay |
| 25 Nov | uv for environments and dependencies | Fast, lock file, standard in modern projects |
| 25 Nov | Collection on GitHub Actions, data on an orphan `data` branch | Free, no server, no card; code and data separated |
| 25 Nov | Run-once script + external scheduler (instead of a `while True` loop) | Scheduler decides when, job decides what |
| 25 Nov | One events file per day (`events/YYYY-MM-DD.csv`) | Small files, easy to load |
| 25 Nov | Trigger from cron-job.org via `workflow_dispatch` | GitHub's `schedule` never ran |
| 25 Nov | Public repository | Unlimited Actions minutes; portfolio project |
| 26 Nov | API cache of 60 s + serve last known data if the source fails | Protects the source; graceful degradation |
| 26 Nov | CORS allows only the frontend's origins and GET | Least privilege |
| 26 Nov | React + Vite + Leaflet with OpenStreetMap tiles | Free, light, standard |
| 27 Nov | Group points into stations by `adresse_station` | Drivers care about a station; stacked circles hid information; less data sent |
| 27 Nov | Keep `/points` alongside `/stations` | Points differ (power, connector); detail still needed |
| 27 Nov | Station color: green if at least one free, red if all working points busy, grey if none working | Answers the driver's question at a glance |
| 27 Nov | Circle radius proportional to the square root of the number of points | Circle area grows proportionally to station size |
| 27 Nov | Grouping done in the backend | One place for the logic; reusable by other clients |
| 28 Nov | CORS origins read from `CORS_ORIGINS` | Same code works locally (port 5173) and in Docker (port 8080) |
| 28 Nov | API image built with uv and `--frozen`; dependencies copied before code | Reproducible installs; fast rebuilds through layer caching |
| 28 Nov | Frontend image: multi-stage build, served by nginx | Small final image without Node |
| 28 Nov | `VITE_API_URL` passed as a build argument | Frontend configuration is fixed at build time |
| 28 Nov | Project layout: `src/`, `scripts/`, `notebooks/`, `docs/`, `tests/`, `frontend/` | Separates the app, one-off scripts, analysis and documentation |
| 28 Nov | `data` branch opened as a Git worktree (`~/projects/belib-data`) | Code and data side by side without switching branches |
| 28 Nov | Analyses in Paris time | Behaviour follows local time |
| 28 Nov | State rebuilt every 15 minutes with `merge_asof` | Turns events into regular snapshots for occupancy analysis |
| 28 Nov | Occupancy computed among working points only | Broken points are neither free nor occupied |
| 28 Nov | Exclude censored sessions (running at start of collection or still running) | Their durations are unknown and would bias statistics downwards |
| 28 Nov | Absolute paths in the notebook (built from `Path.home()`) | Figures saved in the right place wherever the notebook runs |
| 28 Nov | Likely forecast target: at least one point free at the station in 30 minutes | Useful to drivers, less noisy than a single point, consistent with session durations |

---

## Open questions

- [ ] Does the mass update happen every night? At what time?
  - 26 Nov: yes, 03:35 UTC (2,048 events)
  - 27 and 28 Nov: check `runs.csv` around 03:30–03:40 UTC
- [ ] Are the points without a location exactly the "Mise en service planifiée" ones? (check one ID in `state/latest.csv`)
- [x] How are points grouped into stations? By `adresse_station` (same coordinates)
- [ ] Do all points at an address belong to one station? (two stations at the same address?)
- [ ] Are short sessions (under 15 minutes) fast charges or failed attempts? (needs charger power from the static dataset)
- [ ] What explains sessions of 0 minutes and the 42-hour session?
- [x] How many points stay broken for long periods? 50 the whole time, 66 more than half the time
- [ ] Which forecast horizon is most useful: 15, 30 or 60 minutes?
- [ ] Weekday vs weekend: how different are the patterns? (rerun on Mon 30 Nov)
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

Local copy: `~/projects/belib-data` (Git worktree). Update with `git -C ~/projects/belib-data pull`.

### Project structure

```
belib-forecast/
├── .github/workflows/collect.yml   data collection
├── docs/                           NOTES.md, PROGRESS.md, img/
├── frontend/                       React app + Dockerfile
├── notebooks/                      01_eda.ipynb
├── scripts/                        explore.py
├── src/belib_forecast/             api.py, collect_once.py
├── tests/
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── README.md
└── uv.lock
```

### Running the app locally

| Mode | Command | URL |
|---|---|---|
| Development: API | `uv run fastapi dev src/belib_forecast/api.py` | http://127.0.0.1:8000 (docs: `/docs`) |
| Development: frontend | `cd frontend && npm run dev` | http://localhost:5173 |
| Docker: whole app | `docker compose up --build` | http://localhost:8080 (API on port 8000) |
| Notebook | `uv run jupyter lab` | http://localhost:8888 |

### Configuration

| Variable | Used by | Read at | Default / value |
|---|---|---|---|
| `CORS_ORIGINS` | API | Run time | `http://localhost:5173,http://127.0.0.1:5173`; `http://localhost:8080` in Docker |
| `VITE_API_URL` | Frontend | Build time | `http://127.0.0.1:8000`; `http://localhost:8000` in Docker |

### Token

- Fine-grained, repository `belib-forecast` only, permission Actions: read and write.
- Expires 23 Feb 2027. Renew a few days before and update the header on cron-job.org.
- Never commit it or show it in screenshots.

### Weekly check

- `runs.csv` has recent rows, about every 5 minutes
- the `error` column is empty
- `n_new_events` is not stuck at 0
- cron-job.org history shows 204 responses