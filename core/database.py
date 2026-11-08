"""Baza danych SQLite (spec §3). Tabele tworzą się same przy połączeniu."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    language      TEXT NOT NULL,              -- 'python' | 'csharp'
    kind          TEXT NOT NULL,              -- 'function' | 'program'
    description   TEXT NOT NULL,              -- treść w Markdown
    starter_code  TEXT NOT NULL DEFAULT '',
    hint          TEXT NOT NULL DEFAULT '',
    solution      TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,    -- 0 = nigdy nieocenione
    due_date      TEXT NOT NULL               -- YYYY-MM-DD
);

CREATE TABLE IF NOT EXISTS tests (
    id        INTEGER PRIMARY KEY,
    task_id   INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    input     TEXT NOT NULL,                  -- wywołanie funkcji albo stdin
    expected  TEXT NOT NULL                   -- JSON albo oczekiwany stdout
);

CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY,
    task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    rating        TEXT NOT NULL,              -- 'again' | 'partial' | 'good'
    reviewed_at   TEXT NOT NULL,
    tests_passed  INTEGER,
    tests_total   INTEGER,
    hint_used     INTEGER NOT NULL,
    solution_used INTEGER NOT NULL,
    prev_interval_days REAL,                  -- stan zadania sprzed oceny (do cofnięcia)
    prev_due_date      TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row                 # wiersze dostępne po nazwie kolumny
    con.execute("PRAGMA foreign_keys = ON")       # bez tego ON DELETE CASCADE nie działa
    con.executescript(SCHEMA)
    # Migracja baz z v1: dopisujemy kolumny, których jeszcze nie ma
    columns = [row["name"] for row in con.execute("PRAGMA table_info(reviews)")]
    if "prev_interval_days" not in columns:
        con.execute("ALTER TABLE reviews ADD COLUMN prev_interval_days REAL")
    if "prev_due_date" not in columns:
        con.execute("ALTER TABLE reviews ADD COLUMN prev_due_date TEXT")
    return con
