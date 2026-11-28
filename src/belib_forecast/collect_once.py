import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel/"
    "exports/json"
)
EVENT_FIELDS = ["id_pdc", "statut", "last_updated", "first_seen_at"]
STATE_FIELDS = ["id_pdc", "statut", "last_updated"]
POINT_FIELDS = [
    "id_pdc",
    "adresse_station",
    "arrondissement",
    "code_insee",
    "lat",
    "lon",
]
RUN_FIELDS = ["run_at", "n_points", "n_new_events", "error"]


def fetch_records():
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    return response.json()


def load_state(path):
    """Last known (statut, last_updated) of each point, from the previous run."""
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {
            r["id_pdc"]: (r["statut"], r["last_updated"]) for r in csv.DictReader(f)
        }


def write_rows(path, fields, rows, mode):
    """mode='a' appends to the file, mode='w' replaces it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = mode == "w" or not path.exists()
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if needs_header:
            writer.writeheader()
        writer.writerows(rows)


def main(data_dir):
    now = datetime.now(UTC)
    now_iso = now.isoformat(timespec="seconds")
    runs_path = data_dir / "runs.csv"

    try:
        records = fetch_records()
    except (requests.RequestException, ValueError) as e:
        write_rows(
            runs_path,
            RUN_FIELDS,
            [{"run_at": now_iso, "n_points": "", "n_new_events": "", "error": str(e)}],
            "a",
        )
        print(f"{now_iso}  ERROR: {e}")
        return

    state_path = data_dir / "state" / "latest.csv"
    state = load_state(state_path)

    new_events, points = [], []
    for r in records:
        pid, statut, updated = (
            r.get("id_pdc"),
            r.get("statut_pdc"),
            r.get("last_updated"),
        )
        if not (pid and statut and updated):
            continue
        if state.get(pid) != (statut, updated):  # something changed since last run
            new_events.append(
                {
                    "id_pdc": pid,
                    "statut": statut,
                    "last_updated": updated,
                    "first_seen_at": now_iso,
                }
            )
        state[pid] = (statut, updated)

        coords = r.get("coordonneesxy") or {}
        points.append(
            {
                "id_pdc": pid,
                "adresse_station": r.get("adresse_station"),
                "arrondissement": r.get("arrondissement"),
                "code_insee": r.get("code_insee_commune"),
                "lat": coords.get("lat"),
                "lon": coords.get("lon"),
            }
        )

    # one events file per day keeps files small and easy to load
    write_rows(
        data_dir / "events" / f"{now:%Y-%m-%d}.csv", EVENT_FIELDS, new_events, "a"
    )
    write_rows(
        state_path,
        STATE_FIELDS,
        [
            {"id_pdc": k, "statut": s, "last_updated": u}
            for k, (s, u) in sorted(state.items())
        ],
        "w",
    )
    # sorted output: the file only changes when a point really changes,
    # instead of every time the API returns the points in a different order
    points.sort(key=lambda p: p["id_pdc"])
    write_rows(data_dir / "points.csv", POINT_FIELDS, points, "w")
    write_rows(
        runs_path,
        RUN_FIELDS,
        [
            {
                "run_at": now_iso,
                "n_points": len(records),
                "n_new_events": len(new_events),
                "error": "",
            }
        ],
        "a",
    )
    print(f"{now_iso}  {len(records)} points, {len(new_events)} new events")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "data"))