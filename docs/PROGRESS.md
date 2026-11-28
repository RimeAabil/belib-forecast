# Belib' Forecast — Progress

Forecasting the availability of Belib' EV charging points in Paris.
Goal: learn web development and MLOps through one end-to-end data science project.

**Started:** 25 Nov 2026 · **Target:** about 4 weeks · **Repo:** https://github.com/RimeAabil/belib-forecast

---

## Current status

| Part | Status | Details |
|---|---|---|
| Data collection (24/7) | Done | cron-job.org → GitHub Actions → `data` branch, every 5 minutes |
| Backend (FastAPI) | Done | `/health`, `/points`, `/points/{id_pdc}`, `/stats`, `/arrondissements` |
| Frontend (React + Leaflet) | In progress | Live map working; station grouping and auto-refresh to confirm |
| Docker | In progress | Dockerfiles and `compose.yaml` written; full `docker compose up` run to confirm |
| Exploratory analysis | Done (first pass) | `notebooks/01_eda.ipynb`; rerun with a full weekend on Mon 30 Nov |
| Database (Postgres) | Not started | Next step |
| Model | Not started | Needs at least one full week of data (from Wed 2 Dec) |
| Deployment and monitoring | Not started | Week 4 |

---

## Roadmap

### Week 1 — Data collection, API, map
- [x] Explore the Belib' real-time API (`scripts/explore.py`)
- [x] Local collector with SQLite and event-based storage (prototype, since removed)
- [x] Run-once collector writing CSVs (`src/belib_forecast/collect_once.py`)
- [x] GitHub Actions workflow saving data to the `data` branch
- [x] External trigger every 5 minutes with cron-job.org (GitHub's own `schedule` never ran)
- [x] FastAPI backend: `/health`, `/points`, `/points/{id_pdc}`, `/stats`
- [x] `/arrondissements` endpoint
- [x] CORS configured on the API (frontend origins only, GET only)
- [x] React + Leaflet map of live points
- [ ] `/stations` endpoint (points grouped by address)
- [ ] Map shows one circle per station ("3 / 5 available")
- [ ] Map refreshes every minute
- [ ] Code formatted with ruff

### Week 2 — Packaging, database, exploration
- [x] CORS origins configurable through the `CORS_ORIGINS` environment variable
- [x] Dockerfile for the API (uv, locked dependencies, cached layers)
- [x] Dockerfile for the frontend (multi-stage: Node build, nginx serve)
- [x] `compose.yaml` for the whole app
- [ ] `docker compose up --build` verified end to end (http://localhost:8080)
- [x] Project structure cleaned up (`docs/`, `scripts/`, `notebooks/`, `tests/`)
- [x] Data branch checked out locally as a Git worktree (`~/projects/belib-data`)
- [x] Notebook: load events, remove same-status events
- [x] Events to state over time every 15 minutes (`merge_asof`)
- [x] Exploratory analysis, first pass:
  - [x] Distribution of charging-session durations
  - [x] Occupancy over time
  - [x] Broken points: how many, for how long
  - [ ] Occupancy by hour and day of week (heatmap)
  - [ ] Occupancy by arrondissement (map)
  - [ ] Weekday vs weekend (Mon 30 Nov, with a full weekend)
- [ ] Postgres database on Neon (free plan, no card)
- [ ] Loading job: CSVs from the `data` branch → Postgres
- [ ] API reads from Postgres
- [ ] New endpoints: history of a point, occupancy by hour

### Week 3 — Modeling
- [ ] Define the target (likely: at least one point free at the station in 30 minutes)
- [ ] Training dataset (one row = one station at one moment)
- [ ] Train/test split by time (no leakage)
- [ ] Baseline 1: status in 30 minutes = status now
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

### Collection

| Metric | Value | Date |
|---|---|---|
| Charging points | 2,104 | 25 Nov |
| Points with a location | about 2,017 | 28 Nov |
| Points without a location | about 87 (probably planned chargers) | 26 Nov |
| Statuses at first look | 1,016 Disponible · 929 Occupé · 83 Mise en service planifiée · 50 En maintenance · 26 Inconnu | 25 Nov |
| New events per run, night (02:00–05:00 Paris) | 1–10 | 26 Nov |
| New events per run, morning (08:00–09:30 Paris) | 80–106 | 26 Nov |
| New events per run, daytime | 50–90 | 26 Nov |
| Workflow runs, first ~21 hours | 263, all successful | 26 Nov |
| Number of stations | to fill in after `/stations` | — |

### First exploratory analysis (Wed 25 Nov evening → Sat 28 Nov midday)

| Metric | Value |
|---|---|
| Events loaded (located points) | 41,612 |
| Same-status events removed | 9,114 (22%) |
| Complete charging sessions | 13,772 |
| Session duration, 10th percentile | 24 min |
| Session duration, 25th percentile | 1 h 05 |
| Session duration, median | 2 h 26 |
| Session duration, mean | 3 h 55 |
| Session duration, 75th percentile | 5 h 16 |
| Session duration, 90th percentile | 10 h 12 |
| Sessions longer than 10 hours | about 11% |
| Longest session | about 42 h |
| Occupancy, daily high | 60–63% around 12:00–13:00 |
| Occupancy, evening peak | 56–60% around 20:00–21:00 |
| Occupancy, daily low | 41–45% around 08:00 (35% on Saturday morning) |
| Points never broken | 1,690 (about 84%) |
| Points broken more than half the time | 66 |
| Points broken the whole time | 50 |

### Reminders

| Item | Date |
|---|---|
| GitHub token expires (renew a few days before) | 23 Feb 2027 |

---

## Screenshots and figures (for README and blog)

- [ ] First green GitHub Actions run
- [ ] `runs.csv` showing the 03:35 UTC spike
- [ ] First map with all points
- [ ] Map with stations
- [x] Session duration histogram (`docs/img/session_durations.png`)
- [x] Occupancy over time (`docs/img/occupancy_over_time.png`)
- [ ] Model vs baselines results
- [ ] Monitoring page

---

## Learning log

Short reference definitions. Rewrite them in your own words when you can.

### Data engineering
- **Event sourcing:** store every change instead of only the current state; the state at any moment is rebuilt by replaying the events. Gives full history with less storage.
- **Idempotency:** running an operation twice gives the same result as running it once. A primary key with `INSERT OR IGNORE` means a re-run never creates duplicates.
- **Primary key:** the column or columns that uniquely identify a row, e.g. `(id_pdc, last_updated, statut)`.
- **Window functions (`LAG ... OVER (PARTITION BY ... ORDER BY ...)`):** compute a value from other rows of the same group without collapsing them; `LAG` gives the previous row's value.
- **`executemany` and `?` placeholders:** run one SQL statement for many rows; values are sent separately from the SQL, which prevents SQL injection.
- **Static vs dynamic data:** static data (address, coordinates) in one table, changing data (status over time) in another, joined by a key.
- **Data-quality log:** a written record of anomalies found in the data and how they are handled.

### Data analysis (pandas)
- **`groupby(...).shift(1)` / `shift(-1)`:** previous or next value within each group; the pandas equivalent of `LAG` / `LEAD`.
- **`groupby(...).cumcount()`:** numbers the rows of each group 0, 1, 2…; `== 0` marks the first row.
- **`merge_asof`:** for each row of one table, takes the last matching row of another table at or before a given time; used to rebuild the state of every point every 15 minutes.
- **Censored data:** observations whose start or end is unknown (sessions running when collection started, or still running now); excluded so durations aren't biased.
- **Median vs mean:** the median is robust to extreme values; here the mean is pulled up by long overnight stays.
- **Percentiles:** the value below which a given share of observations falls.
- **Time zones:** data stored in UTC, analysed in local time (`Europe/Paris`) because behaviour follows local time.
- **`clip`:** caps extreme values so one outlier doesn't stretch a chart.

### Visualization
- **seaborn:** a matplotlib-based library with cleaner default styles (`sns.set_theme`).
- **Readable charts:** title on the left, units on the axes (hours, percentages), reference lines (median), annotations, shading for context (nights), `despine()`.
- **Saving figures:** `fig.savefig(path, dpi=150)` for the README and blog.

### Notebooks and project hygiene
- **Execution order:** a notebook must run from top to bottom; "Restart & Run All" is the test. A `NameError` means a cell defining the variable is missing or placed below.
- **Imports and settings in the first cell:** defined once, in a standard order (standard library first, then third-party packages).
- **Relative vs absolute paths:** relative paths depend on where the code runs; absolute paths (built from `Path.home()`) are reliable.
- **Project layout:** `src/` for the app, `scripts/` for one-off scripts, `notebooks/` for analysis, `docs/` for documentation, `tests/` for tests.
- **`tree -I '...'`:** shows the project structure while hiding heavy folders.

### MLOps / infrastructure
- **cron and cron expressions:** run a task on a schedule; `*/5 * * * *` means every 5 minutes.
- **GitHub Actions:** GitHub runs a workflow (YAML) on temporary machines; triggers such as `schedule` and `workflow_dispatch`; `concurrency` prevents overlapping runs.
- **Scheduler vs job:** the scheduler decides when (cron-job.org), the job decides what (the workflow and script). Same split as Airflow.
- **Git scraping:** collect data on a schedule and store it as files committed to a Git repository.
- **Orphan branch:** a branch with no shared history with `main`; used to keep data separate from code.
- **Git worktree:** a second working folder for the same repository, here used to open the `data` branch next to the code.
- **Fine-grained tokens and least privilege:** a token limited to one repository and one permission (Actions: write); each component gets only what it needs.
- **Configuration through environment variables:** paths, URLs and allowed origins come from the environment (`BELIB_DB`, `CORS_ORIGINS`, `VITE_API_URL`), so the same code runs locally, on a server or in Docker.
- **Shell variable vs environment variable:** `read -s X` creates a variable for the current shell only; `export X` passes it to launched programs.

### Docker
- **Image vs container:** an image is a frozen package (code, dependencies, system); a container is a running instance of it.
- **Dockerfile:** the recipe used to build an image.
- **Layers and caching:** each instruction creates a cached layer; copying dependency files before the code makes rebuilds fast.
- **Locked installs:** `uv sync --frozen` and `npm ci` install exactly the versions in the lock files.
- **Multi-stage build:** build with Node, then keep only the static files served by nginx; a much smaller final image.
- **`.dockerignore`:** keeps unneeded files (`.venv`, `node_modules`, `.git`, data) out of the image.
- **Listening on `0.0.0.0`:** inside a container, `127.0.0.1` only accepts connections from the container itself.
- **Port mapping (`"8080:80"`):** connects a port on the host to a port in the container.
- **Docker Compose:** builds and starts several containers with one command.
- **Build-time vs run-time configuration:** `VITE_API_URL` is baked into the frontend at build time; `CORS_ORIGINS` is read by the API when it starts.
- **Browser vs container networking:** frontend code runs in the browser, so it calls the API through the host's published port (`localhost:8000`), not the Compose service name (`api`).

### Web
- **HTTP methods:** GET reads (safe, idempotent); POST creates or triggers an action (side effects, not idempotent).
- **HTTP status codes:** 200 OK · 204 OK with no content · 401 bad credentials · 404 not found (also used by GitHub to hide resources) · 422 invalid input · 503 service unavailable.
- **FastAPI routes:** `@app.get("/path")` maps a URL to a function.
- **Path vs query parameters:** `/points/{id_pdc}` (part of the path) vs `/points?statut=Disponible` (after `?`).
- **Pydantic models as an API contract:** describe and validate exactly what an endpoint returns; documented automatically in `/docs`.
- **Caching:** call the source at most once per minute whatever the traffic.
- **Graceful degradation:** if the source is down, serve the last known data instead of failing.
- **CORS:** browsers block a page from reading responses from another origin unless the server allows it.
- **Map tiles:** the map is cut into small square images per zoom level; Leaflet downloads only those on screen.
- **Leaflet / react-leaflet:** Leaflet draws interactive maps; react-leaflet wraps it as React components.
- **React `useState` / `useEffect`:** state that re-renders the page when it changes; effects run side work such as API calls.
- **Effect cleanup:** the function returned by `useEffect` runs when the component unmounts; used to `clearInterval`.
- **Loading / error / success states:** a good interface always handles all three.
- **Debugging a request:** API logs (did the request arrive?), browser Console (error message) and Network tab (URL, status).

### Python
- **`collections.Counter`:** counts occurrences; a missing key returns 0.
- **`collections.defaultdict(list)`:** a dictionary where a missing key starts as an empty list.
- **`sum(condition for x in items)`:** counts matches, since `True` equals 1.
- **uv, `pyproject.toml`, `uv.lock`:** project metadata, dependencies and exact locked versions; `uv run` uses the right environment; `--dev` for development-only tools.
- **PEP 8 and ruff:** Python style conventions and a tool that checks and formats code.

---

## Daily log

### 25 Nov 2026
- Compared project ideas; chose Belib' EV charging availability forecasting.
- Explored the Belib' API: 2,104 points, fields and statuses.
- Built a local SQLite collector with event-based storage; checked the first 30 minutes of data with SQL (`LAG`).
- Moved collection to GitHub Actions with a `data` branch; GitHub's `schedule` did not run, so added cron-job.org calling `workflow_dispatch` (tested with curl: 204).
- Started the FastAPI backend.

### 26 Nov 2026
- Checked the first day of data: 263 successful runs, clear daily pattern (quiet nights, morning peak 08:00–09:30 Paris).
- Found data-quality issues: mass update at 03:35 UTC, about 87 points without a location, "Paris centre" (see `NOTES.md`).
- Created `PROGRESS.md` and `NOTES.md`.
- Added `/arrondissements` and CORS.
- Built the React + Leaflet map; working end to end (Paris API → FastAPI → React).
- Debugged a "Failed to fetch": the page had loaded before the API was started.

### 27 Nov 2026
- Worked on grouping points into stations (`/stations`) and on refreshing the map every minute.

### 28 Nov 2026
- Wrote the Docker setup: API image (uv), frontend image (Node build + nginx), `compose.yaml`, `.dockerignore` files; made CORS origins configurable.
- Cleaned up the project structure: `docs/`, `scripts/`, `notebooks/`, `tests/`; removed the old loop collector and the Vite template assets.
- Checked out the `data` branch as a Git worktree.
- First exploratory analysis (`notebooks/01_eda.ipynb`):
  - 22% of events were same-status noise and were removed.
  - 13,772 complete sessions; median 2 h 26; about 11% longer than 10 hours.
  - Daily occupancy cycle with peaks at 12:00–13:00 and 20:00–21:00 and a low at 08:00.
  - 50 points broken the whole time; about 84% never broken.
- Fixed notebook issues: analysis window starting at the first collector run, missing cells (`NameError`), figures saved outside the project (switched to absolute paths).
- Saved two figures in `docs/img/`.