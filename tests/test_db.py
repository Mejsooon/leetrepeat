from db import connect


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
