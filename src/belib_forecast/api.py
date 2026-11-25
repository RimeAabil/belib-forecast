import time
from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from belib_forecast.collect_once import fetch_records

app = FastAPI(title="Belib' Forecast API")

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
        except Exception:
            if _cache["points"]:  # the source is down: serve the last known data
                return _cache["points"]
            raise HTTPException(status_code=503, detail="Belib' data source unavailable")
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