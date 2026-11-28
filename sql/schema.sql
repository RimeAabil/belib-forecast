-- Static information about each charging point
CREATE TABLE IF NOT EXISTS points (
    id_pdc          TEXT PRIMARY KEY,
    adresse_station TEXT,
    arrondissement  TEXT,
    code_insee      TEXT,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION
);

-- Every status change seen by the collector (event sourcing)
CREATE TABLE IF NOT EXISTS events (
    id_pdc        TEXT        NOT NULL,
    statut        TEXT        NOT NULL,
    last_updated  TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id_pdc, last_updated, statut)
);

-- Speeds up queries filtered by time ("events between X and Y")
CREATE INDEX IF NOT EXISTS events_time_idx ON events (last_updated);

-- Log of every collector run
CREATE TABLE IF NOT EXISTS runs (
    run_at       TIMESTAMPTZ PRIMARY KEY,
    n_points     INTEGER,
    n_new_events INTEGER,
    error        TEXT
);