"""Load the collector's CSV files (from the `data` branch) into Postgres.

Usage:
    uv run src/belib_forecast/load_to_db.py ~/projects/belib-data
    uv run src/belib_forecast/load_to_db.py ~/projects/belib-data --days 2

Safe to run any number of times: rows already in the database are skipped.
"""

import argparse
import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"

POINT_COLUMNS = [
    "id_pdc",
    "adresse_station",
    "arrondissement",
    "code_insee",
    "lat",
    "lon",
]
EVENT_COLUMNS = ["id_pdc", "statut", "last_updated", "first_seen_at"]
RUN_COLUMNS = ["run_at", "n_points", "n_new_events", "error"]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def none_if_empty(value):
    """CSV stores missing values as empty strings; the database needs NULL."""
    return value if value not in ("", None) else None


def stage_and_insert(cur, table, columns, rows, conflict_clause) -> int:
    """Copy rows into a temporary table, then insert them into the real table.

    COPY is Postgres's fastest way to load many rows. The temporary staging table
    lets us use ON CONFLICT, so rows already in the database are skipped or updated.
    Returns the number of rows inserted or updated in the real table.
    """
    cols = ", ".join(columns)
    stage = f"{table}_stage"
    cur.execute(
        f"CREATE TEMP TABLE {stage} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP"
    )
    with cur.copy(f"COPY {stage} ({cols}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row([none_if_empty(row[c]) for c in columns])
    cur.execute(
        f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {stage} {conflict_clause}"
    )
    return cur.rowcount


def main(data_dir: Path, days: int | None = None) -> None:
    load_dotenv()
    database_url = os.environ["DATABASE_URL"]

    points = read_csv(data_dir / "points.csv")
    runs = read_csv(data_dir / "runs.csv")
    # Events are stored in one file per day. With --days N, only the N most recent
    # files are read (incremental load); without it, the whole history is loaded.
    event_files = sorted((data_dir / "events").glob("*.csv"))
    if days is not None:
        event_files = event_files[-days:]
    events = []
    for f in event_files:
        events.extend(read_csv(f))

    # One transaction: committed when the `with` block ends, rolled back on any error
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_FILE.read_text())

        n_points = stage_and_insert(
            cur,
            "points",
            POINT_COLUMNS,
            points,
            """ON CONFLICT (id_pdc) DO UPDATE SET
                   adresse_station = EXCLUDED.adresse_station,
                   arrondissement  = EXCLUDED.arrondissement,
                   code_insee      = EXCLUDED.code_insee,
                   lat             = EXCLUDED.lat,
                   lon             = EXCLUDED.lon""",
        )
        n_events = stage_and_insert(
            cur, "events", EVENT_COLUMNS, events, "ON CONFLICT DO NOTHING"
        )
        n_runs = stage_and_insert(
            cur, "runs", RUN_COLUMNS, runs, "ON CONFLICT DO NOTHING"
        )

    print(f"Points upserted: {n_points:,} (of {len(points):,} read)")
    print(f"New events:      {n_events:,} (of {len(events):,} read)")
    print(f"Event files:     {len(event_files)}")
    print(f"New runs:        {n_runs:,} (of {len(runs):,} read)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_dir", type=Path, help="folder of the `data` branch")
    parser.add_argument(
        "--days", type=int, default=None, help="only load the N most recent event files"
    )
    args = parser.parse_args()
    main(args.data_dir.expanduser(), args.days)