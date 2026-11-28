# Belib' Forecast — Progress

Forecasting the availability of Belib' EV charging points in Paris.
Goal: learn web development and MLOps through one end-to-end data science project.

**Started:** 25 Nov 2026 · **Target:** ~4 weeks · **Repo:** https://github.com/RimeAabil/belib-forecast

---

## Current status

| Part | Status |
|---|---|
| Data collection (24/7) | ✅ Running: cron-job.org → GitHub Actions → `data` branch, every 5 min |
| Backend (FastAPI) | ✅ Live endpoints: `/health`, `/points`, `/points/{id_pdc}`, `/stats`, `/arrondissements` |
| Frontend (React + Leaflet) | ✅ Map of live points · 🔄 stations + auto-refresh in progress |
| Database (Postgres) | ⬜ Not started |
| Docker | ⬜ Not started |
| Model | ⬜ Waiting for data (≥ 1 week needed) |
| Deployment & monitoring | ⬜ Not started |

---

## Roadmap

### Week 1 — Data collection, API, map
- [x] Explore the Belib' real-time API (`explore.py`)
- [x] Local collector with SQLite and event-based storage (`collector.py`)
- [x] Run-once collector writing CSVs (`collect_once.py`)
- [x] GitHub Actions workflow saving data to the `data` branch
- [x] External trigger every 5 min with cron-job.org (GitHub's own `schedule` never ran)
- [x] FastAPI backend: `/health`, `/points`, `/points/{id_pdc}`, `/stats`
- [x] `/arrondissements` endpoint tested and committed
- [x] CORS configured on the API (local frontend origins, GET only)
- [x] React + Leaflet map of live points
- [ ] `/stations` endpoint (points grouped by address)
- [ ] Map shows one circle per station ("3 / 5 available")
- [ ] Map refreshes every minute
- [ ] Code formatted with ruff

### Week 2 — Packaging, database, exploration
- [ ] Dockerfile for the API
- [ ] Dockerfile for the frontend
- [ ] `docker compose up` starts the whole app
- [ ] Postgres database on Neon (free plan, no card)
- [ ] Loading job: CSVs from the `data` branch → Postgres
- [ ] API reads from Postgres
- [ ] New endpoints: history of a point, occupancy by hour
- [ ] Notebook: load events, remove fake changes with `LAG`
- [ ] Events → state over time (`merge_asof`)
- [ ] Exploratory analysis:
  - [ ] Distribution of charging-session durations
  - [ ] Occupancy by hour and day of week (heatmap)
  - [ ] Occupancy by arrondissement (map)
  - [ ] Broken points: how many, for how long
  - [ ] Weekday vs weekend

### Week 3 — Modeling
- [ ] Define the target (likely: at least one point free at the station in 30 min)
- [ ] Training dataset (one row = one station at one moment)
- [ ] Train/test split **by time** (no leakage)
- [ ] Baseline 1: status in 30 min = status now
- [ ] Baseline 2: historical probability for this station at this hour
- [ ] LightGBM model beating both baselines
- [ ] Experiments tracked in MLflow
- [ ] Best model registered and served by the API (`/forecast`)

### Week 4 — Production
- [ ] Forecasts shown on the map
- [ ] Each forecast compared automatically with what actually happened
- [ ] Monitoring page: accuracy over time, data freshness, collector health
- [ ] Scheduled retraining
- [ ] Tests (pytest) for the API and the collector
- [ ] CI with GitHub Actions: lint, tests, build
- [ ] CD: automatic deploy on push
- [ ] App deployed online with a public URL
- [ ] README: architecture diagram, results, lessons learned
- [ ] Demo video
- [ ] Portfolio case study
- [ ] First blog post

### Stretch goals
- [ ] Add charger power (`puiss_max`) from the static Belib' dataset
- [ ] Show fast vs slow chargers on the map
- [ ] Add weather features
- [ ] Session-duration model ("when will this charger be free?")
- [ ] Extend to the national IRVE dataset

---

## Key numbers

| Metric | Value | Date |
|---|---|---|
| Charging points | 2,104 | 25 Nov |
| Points without a location | ~87 (probably planned chargers) | 26 Nov |
| Statuses at first look | 1,016 Disponible · 929 Occupé · 83 Mise en service planifiée · 50 En maintenance · 26 Inconnu | 25 Nov |
| New events per run, night (02:00–05:00 Paris) | 1–10 | 26 Nov |
| New events per run, morning peak (08:00–09:30 Paris) | 80–106 | 26 Nov |
| New events per run, daytime | 50–90 | 26 Nov |
| Real status changes vs same-status events (first test) | 296 vs 17 | 25 Nov |
| Workflow runs, first ~21 h | 263, all successful | 26 Nov |
| Number of stations | _to fill in after `/stations`_ | 27 Nov |
| GitHub token expires | **23 Feb 2027** (renew before) | — |

---

## Screenshots to keep (for README and blog)

- [ ] First green GitHub Actions run
- [ ] `runs.csv` showing the 03:35 UTC spike
- [ ] First map with all points
- [ ] Map with stations
- [ ] First EDA charts
- [ ] Model vs baselines results
- [ ] Monitoring page

---

## Learning log

Short reference definitions. Rewrite them in your own words when you can.

### Data engineering
- **Event sourcing:** store every change instead of only the current state; the state at any moment is rebuilt by replaying the events. Gives full history and less storage.
- **Idempotency:** running an operation twice gives the same result as running it once. Here, a primary key + `INSERT OR IGNORE` means a re-run never creates duplicates.
- **Primary key:** the column(s) that uniquely identify a row, e.g. `(id_pdc, last_updated, statut)`.
- **Window functions (`LAG ... OVER (PARTITION BY ... ORDER BY ...)`):** compute a value from other rows of the same group without collapsing them; `LAG` gives the previous row's value.
- **`executemany` and `?` placeholders:** run one SQL statement for many rows; values are sent separately from the SQL, which prevents SQL injection.
- **Static vs dynamic data:** static (address, coordinates) in one table, changing data (status over time) in another, joined by a key.
- **Data-quality log:** written record of anomalies found in the data and how they are handled.

### MLOps / infrastructure
- **cron and cron expressions:** run a task on a schedule; `*/5 * * * *` = every 5 minutes.
- **GitHub Actions:** GitHub runs a workflow (YAML) on temporary machines; triggers like `schedule` and `workflow_dispatch`; `concurrency` prevents overlapping runs.
- **Scheduler vs job:** the scheduler decides *when* (cron-job.org), the job decides *what* (the workflow + script). Same split as Airflow.
- **Git scraping:** collect data on a schedule and store it as files committed to a Git repo.
- **Orphan branch:** a branch with no shared history with `main`; used here to keep data separate from code.
- **Fine-grained tokens and least privilege:** a token limited to one repo and one permission (Actions: write); each piece gets only what it needs.
- **Configuration through environment variables:** paths and URLs come from the environment (`BELIB_DB`, `VITE_API_URL`) so the same code runs locally, on a server or in Docker.
- **Shell variable vs environment variable:** `read -s X` creates a variable for the current shell only; `export X` passes it to launched programs.

### Web
- **HTTP methods:** GET reads (safe, idempotent); POST creates or triggers an action (side effects, not idempotent).
- **HTTP status codes:** 200 OK · 204 OK with no content · 401 bad credentials · 404 not found (also used by GitHub to hide resources) · 422 invalid input · 503 service unavailable.
- **FastAPI routes:** `@app.get("/path")` maps a URL to a function.
- **Path vs query parameters:** `/points/{id_pdc}` (part of the path) vs `/points?statut=Disponible` (after `?`).
- **Pydantic models as an API contract:** describe and validate exactly what an endpoint returns; documented automatically in `/docs`.
- **Caching:** call the source at most once per minute whatever the traffic.
- **Graceful degradation:** if the source is down, serve the last known data instead of failing.
- **CORS:** browsers block a page from reading responses from another origin unless the server allows it; we allow only the frontend's origin and GET.
- **Map tiles:** the map is cut into small square images per zoom level; Leaflet downloads only those on screen.
- **Leaflet / react-leaflet:** Leaflet draws interactive maps; react-leaflet wraps it as React components.
- **React `useState` / `useEffect`:** state that re-renders the page when it changes; effects run side work like API calls.
- **Effect cleanup:** the function returned by `useEffect` runs when the component unmounts; used to `clearInterval`.
- **Loading / error / success states:** a good UI always handles all three.
- **Debugging a request:** API logs (did the request arrive?), browser F12 Console (error message) and Network tab (URL, status).

### Python
- **`collections.Counter`:** counts occurrences; a missing key returns 0.
- **`collections.defaultdict(list)`:** dictionary where a missing key starts as an empty list.
- **`sum(condition for x in items)`:** counts matches, since `True` = 1.
- **uv, `pyproject.toml`, `uv.lock`:** project metadata, dependencies and exact locked versions; `uv run` uses the right environment.
- **PEP 8 and ruff:** Python style conventions and a tool that checks and formats code.

---

## Daily log

### 25 Nov 2026
- Compared project ideas; chose Belib' EV charging availability forecasting.
- Explored the Belib' API: 2,104 points, fields and statuses.
- Built a local SQLite collector with event-based storage; checked the first 30 minutes of data with SQL (`LAG`).
- Moved collection to GitHub Actions with a `data` branch; GitHub's `schedule` didn't run, so added cron-job.org calling `workflow_dispatch` (tested with curl: 204).
- Started the FastAPI backend.

### 26 Nov 2026
- Checked the first day of data: 263 successful runs, clear daily pattern (quiet nights, morning peak 08:00–09:30 Paris).
- Found data-quality issues: mass update at 03:35 UTC, ~87 points without a location, "Paris centre" (see `NOTES.md`).
- Created `PROGRESS.md` and `NOTES.md`.
- Added `/arrondissements` and CORS.
- Built the React + Leaflet map; working end to end (Paris API → FastAPI → React).
- Debugged a "Failed to fetch": the page had loaded before the API was started.

### 27 Nov 2026
- Started grouping points into stations (`/stations`) and auto-refresh of the map.
- _Add what you finished today._