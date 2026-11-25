import os
import sqlite3
import time
from datetime import datetime, timezone

import requests

URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel/"
    "exports/json"
)
DB_PATH = os.getenv("BELIB_DB", "belib.db")
INTERVAL_SECONDS = 300  # 5 minutes


SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    id_pdc          TEXT PRIMARY KEY,
    adresse_station TEXT,
    arrondissement  TEXT,
    code_insee      TEXT,
    lat             REAL,
    lon             REAL
);

CREATE TABLE IF NOT EXISTS status_events (
    id_pdc        TEXT NOT NULL,
    statut        TEXT NOT NULL,
    last_updated  TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    PRIMARY KEY (id_pdc, last_updated, statut)
);

CREATE TABLE IF NOT EXISTS collection_runs (
    run_at       TEXT PRIMARY KEY,
    n_points     INTEGER,
    n_new_events INTEGER,
    error        TEXT
);
"""


def fetch_records():
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    return response.json()


def collect(conn):
    now = datetime.now(timezone.utc).isoformat()
    records = fetch_records()

    point_rows, event_rows = [], []
    for r in records:
        coords = r.get("coordonneesxy") or {}
        point_rows.append((
            r["id_pdc"], r.get("adresse_station"), r.get("arrondissement"),
            r.get("code_insee_commune"), coords.get("lat"), coords.get("lon"),
        ))
        
        if r.get("statut_pdc") and r.get("last_updated"):
            event_rows.append((r["id_pdc"], r["statut_pdc"], r["last_updated"], now))

    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO status_events VALUES (?, ?, ?, ?)", event_rows
    )
    n_new = conn.total_changes - before

    conn.executemany(
        "INSERT OR REPLACE INTO points VALUES (?, ?, ?, ?, ?, ?)", point_rows
    )
    conn.execute(
        "INSERT INTO collection_runs VALUES (?, ?, ?, NULL)", (now, len(records), n_new)
    )
    conn.commit()
    print(f"{now}  {len(records)} points, {n_new} new events")


def log_error(conn, error):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO collection_runs VALUES (?, NULL, NULL, ?)", (now, str(error))
    )
    conn.commit()
    print(f"{now}  ERROR: {error}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    print(f"Collecting into {DB_PATH} every {INTERVAL_SECONDS}s. Ctrl+C to stop.")
    while True:
        try:
            collect(conn)
        except Exception as e:  # one failed request must never stop the collector
            log_error(conn, e)
        time.sleep(INTERVAL_SECONDS)