import os
import time
from collections import Counter, defaultdict

import psycopg
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from belib_forecast.collect_once import fetch_records

load_dotenv()  # reads .env locally; in production the platform sets the variables
DATABASE_URL = os.getenv("DATABASE_URL_POOLED") or os.getenv("DATABASE_URL")

app = FastAPI(title="Belib' Forecast API")

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Allow only the local frontend (Vite dev server), and only read requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

CACHE_SECONDS = 60
_cache = {"fetched_at": 0.0, "points": []}


class Point(BaseModel):
    id_pdc: str
    statut: str
    last_updated: str
    adresse_station: str | None = None
    arrondissement: str | None = None
    lat: float | None = None
    lon: float | None = None


class ArrondissementStats(BaseModel):
    arrondissement: str
    free_points: int
    total_points: int


class Station(BaseModel):
    adresse: str
    arrondissement: str | None = None
    lat: float
    lon: float
    total: int
    available: int
    occupied: int
    out_of_service: int


class HourlyActivity(BaseModel):
    hour: int
    avg_arrivals: float


# Average number of cars plugging in, per hour of the day (Paris time), at one
# station. An arrival = a real change to "Occupé (en charge)" (same-status noise
# is removed with LAG). Averaged over the number of days covered by the collector.
HOURLY_ACTIVITY_SQL = """
WITH changes AS (
    SELECT e.statut, e.last_updated,
           LAG(e.statut) OVER (PARTITION BY e.id_pdc ORDER BY e.last_updated) AS prev
    FROM events e
    JOIN points p USING (id_pdc)
    WHERE p.adresse_station = %(adresse)s
),
arrivals AS (
    SELECT EXTRACT(HOUR FROM last_updated AT TIME ZONE 'Europe/Paris') AS hour
    FROM changes
    WHERE prev IS NOT NULL AND prev <> statut AND statut = 'Occupé (en charge)'
),
period AS (
    SELECT GREATEST(EXTRACT(EPOCH FROM MAX(run_at) - MIN(run_at)) / 86400, 1) AS days
    FROM runs
)
SELECT h AS hour,
       ROUND((COUNT(a.hour) / (SELECT days FROM period))::numeric, 2)::float
           AS avg_arrivals
FROM generate_series(0, 23) AS h
LEFT JOIN arrivals a ON a.hour = h
GROUP BY h
ORDER BY h
"""


def to_point(r: dict) -> Point:
    coords = r.get("coordonneesxy") or {}
    return Point(
        id_pdc=r["id_pdc"],
        statut=r.get("statut_pdc") or "Inconnu",
        last_updated=r.get("last_updated") or "",
        adresse_station=r.get("adresse_station"),
        arrondissement=r.get("arrondissement"),
        lat=coords.get("lat"),
        lon=coords.get("lon"),
    )


def get_points() -> list[Point]:
    """Return the live points, calling the Belib' API at most once per minute."""
    if time.time() - _cache["fetched_at"] > CACHE_SECONDS:
        try:
            records = fetch_records()
        except (requests.RequestException, ValueError):
            if _cache["points"]:  # the source is down: serve the last known data
                return _cache["points"]
            raise HTTPException(
                status_code=503, detail="Belib' data source unavailable"
            ) from None
        _cache["points"] = [to_point(r) for r in records if r.get("id_pdc")]
        _cache["fetched_at"] = time.time()
    return _cache["points"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/points", response_model=list[Point])
def list_points(statut: str | None = None, arrondissement: str | None = None):
    points = get_points()
    if statut:
        points = [p for p in points if p.statut == statut]
    if arrondissement:
        points = [p for p in points if p.arrondissement == arrondissement]
    return points


@app.get("/points/{id_pdc}", response_model=Point)
def get_point(id_pdc: str):
    for p in get_points():
        if p.id_pdc == id_pdc:
            return p
    raise HTTPException(status_code=404, detail=f"Point {id_pdc} not found")


@app.get("/stats")
def stats():
    points = get_points()
    return {"total": len(points), "by_statut": Counter(p.statut for p in points)}


@app.get("/arrondissements", response_model=list[ArrondissementStats])
def list_arrondissements():
    points = [p for p in get_points() if p.arrondissement]
    total = Counter(p.arrondissement for p in points)
    free = Counter(p.arrondissement for p in points if p.statut == "Disponible")
    return [
        ArrondissementStats(
            arrondissement=a, free_points=free[a], total_points=total[a]
        )
        for a in sorted(total)
    ]


@app.get("/stations", response_model=list[Station])
def list_stations():
    groups: dict[str, list[Point]] = defaultdict(list)
    for p in get_points():
        if p.adresse_station and p.lat is not None and p.lon is not None:
            groups[p.adresse_station].append(p)

    stations = []
    for adresse, pts in groups.items():
        available = sum(p.statut == "Disponible" for p in pts)
        occupied = sum(p.statut == "Occupé (en charge)" for p in pts)
        stations.append(
            Station(
                adresse=adresse,
                arrondissement=pts[0].arrondissement,
                lat=pts[0].lat,
                lon=pts[0].lon,
                total=len(pts),
                available=available,
                occupied=occupied,
                out_of_service=len(pts) - available - occupied,
            )
        )
    return sorted(stations, key=lambda s: s.adresse)


@app.get("/stations/activity", response_model=list[HourlyActivity])
def station_activity(adresse: str):
    """Typical arrivals per hour of the day at one station (history in Postgres)."""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM points WHERE adresse_station = %(adresse)s LIMIT 1",
                {"adresse": adresse},
            )
            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=404, detail=f"Station {adresse} not found"
                )
            cur.execute(HOURLY_ACTIVITY_SQL, {"adresse": adresse})
            rows = cur.fetchall()
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return [HourlyActivity(hour=h, avg_arrivals=v) for h, v in rows]