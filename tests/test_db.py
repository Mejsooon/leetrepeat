from core.database import connect


def insert_task(con):
    cur = con.execute(
        "INSERT INTO tasks (title, language, kind, description, solution, created_at, due_date)"
        " VALUES ('T', 'python', 'function', 'opis', 'roz', '2026-11-08T10:00:00', '2026-11-08')"
    )
    return cur.lastrowid


def test_tables_created(tmp_path):
    con = connect(str(tmp_path / "t.db"))
    names = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"tasks", "tests", "reviews"} <= names


def test_delete_task_cascades(tmp_path):
    con = connect(str(tmp_path / "t.db"))
    task_id = insert_task(con)
    con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, 0, 'f()', '1')", (task_id,))
    con.execute(
        "INSERT INTO reviews (task_id, rating, reviewed_at, hint_used, solution_used)"
        " VALUES (?, 'good', '2026-11-08T10:00:00', 0, 0)", (task_id,))
    con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    assert con.execute("SELECT COUNT(*) FROM tests").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0


def test_connect_twice_keeps_data(tmp_path):
    path = str(tmp_path / "t.db")
    con = connect(path)
    insert_task(con)
    con.commit()
    con.close()
    con2 = connect(path)
    assert con2.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_migration_adds_prev_columns_once(tmp_path):
    import sqlite3
    path = str(tmp_path / "v1.db")
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, language TEXT NOT NULL, kind TEXT NOT NULL,
            description TEXT NOT NULL, starter_code TEXT NOT NULL DEFAULT '', hint TEXT NOT NULL DEFAULT '',
            solution TEXT NOT NULL, created_at TEXT NOT NULL, interval_days REAL NOT NULL DEFAULT 0, due_date TEXT NOT NULL);
        CREATE TABLE tests (id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, position INTEGER NOT NULL,
            input TEXT NOT NULL, expected TEXT NOT NULL);
        CREATE TABLE reviews (id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, rating TEXT NOT NULL,
            reviewed_at TEXT NOT NULL, tests_passed INTEGER, tests_total INTEGER,
            hint_used INTEGER NOT NULL, solution_used INTEGER NOT NULL);
    """)
    old.close()
    connect(path).close()
    con = connect(path)          # drugie połączenie nie może rzucić "duplicate column"
    columns = {row["name"] for row in con.execute("PRAGMA table_info(reviews)")}
    assert {"prev_interval_days", "prev_due_date"} <= columns
