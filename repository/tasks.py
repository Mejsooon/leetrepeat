"""Repository: cały SQL aplikacji. Każda funkcja sama otwiera i zamyka połączenie z bazą."""
from core.database import connect


def list_tasks(db_path, language=None):
    con = connect(db_path)
    if language:
        rows = con.execute("SELECT id, title, language, kind, due_date, interval_days FROM tasks"
                           " WHERE language = ? ORDER BY due_date, id", (language,)).fetchall()
    else:
        rows = con.execute("SELECT id, title, language, kind, due_date, interval_days FROM tasks"
                           " ORDER BY due_date, id").fetchall()
    con.close()
    return [dict(row) for row in rows]


def get_task(db_path, task_id):
    """Zadanie z testami i datą ostatniej oceny albo None, gdy nie istnieje."""
    con = connect(db_path)
    row = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        con.close()
        return None
    task = dict(row)
    task["tests"] = [dict(t) for t in con.execute(
        "SELECT input, expected FROM tests WHERE task_id = ? ORDER BY position", (task_id,))]
    last = con.execute("SELECT reviewed_at, rating FROM reviews WHERE task_id = ?"
                       " ORDER BY reviewed_at DESC, id DESC LIMIT 1", (task_id,)).fetchone()
    task["last_reviewed_at"] = last["reviewed_at"] if last else None
    task["last_rating"] = last["rating"] if last else None
    con.close()
    return task


def create_task(db_path, task, created_at, due_date):
    """task: słownik z polami formularza (title, language, ..., tests). Zwraca id nowego zadania."""
    con = connect(db_path)
    with con:  # transakcja: zadanie i testy zapisują się razem albo wcale
        cur = con.execute(
            "INSERT INTO tasks (title, language, kind, description, starter_code, hint, solution,"
            " created_at, interval_days, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (task["title"], task["language"], task["kind"], task["description"], task["starter_code"],
             task["hint"], task["solution"], created_at, due_date))
        task_id = cur.lastrowid
        for position, test in enumerate(task["tests"]):
            con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, ?, ?, ?)",
                        (task_id, position, test["input"], test["expected"]))
    con.close()
    return task_id


def update_task(db_path, task_id, task):
    """Zmienia treść zadania i zastępuje testy; harmonogram zostaje. Zwraca False, gdy brak zadania."""
    con = connect(db_path)
    if con.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
        con.close()
        return False
    with con:
        con.execute(
            "UPDATE tasks SET title = ?, language = ?, kind = ?, description = ?, starter_code = ?,"
            " hint = ?, solution = ? WHERE id = ?",
            (task["title"], task["language"], task["kind"], task["description"], task["starter_code"],
             task["hint"], task["solution"], task_id))
        con.execute("DELETE FROM tests WHERE task_id = ?", (task_id,))
        for position, test in enumerate(task["tests"]):
            con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, ?, ?, ?)",
                        (task_id, position, test["input"], test["expected"]))
    con.close()
    return True


def delete_task(db_path, task_id):
    """Usuwa zadanie (testy i historia znikają przez ON DELETE CASCADE). Zwraca False, gdy brak zadania."""
    con = connect(db_path)
    with con:
        cur = con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    con.close()
    return cur.rowcount > 0


def due_task_ids(db_path, today, language=None):
    """Id zadań z terminem powtórki dziś lub wcześniej, najstarsze pierwsze."""
    con = connect(db_path)
    if language:
        rows = con.execute("SELECT id FROM tasks WHERE due_date <= ? AND language = ?"
                           " ORDER BY due_date, id", (today, language)).fetchall()
    else:
        rows = con.execute("SELECT id FROM tasks WHERE due_date <= ? ORDER BY due_date, id",
                           (today,)).fetchall()
    con.close()
    return [row["id"] for row in rows]


def count_tasks(db_path, language, today):
    """(ile do powtórki dziś, ile łącznie) dla jednego języka."""
    con = connect(db_path)
    total = con.execute("SELECT COUNT(*) FROM tasks WHERE language = ?", (language,)).fetchone()[0]
    due = con.execute("SELECT COUNT(*) FROM tasks WHERE language = ? AND due_date <= ?",
                      (language, today)).fetchone()[0]
    con.close()
    return due, total


def save_review(db_path, task_id, review, interval_days, due_date, reviewed_at, prev_interval_days, prev_due_date):
    """Zapisuje nowy termin zadania i wpis w historii ocen (jedna transakcja).
    prev_*: termin sprzed oceny — potrzebny, żeby dało się ją cofnąć."""
    con = connect(db_path)
    with con:
        con.execute("UPDATE tasks SET interval_days = ?, due_date = ? WHERE id = ?",
                    (interval_days, due_date, task_id))
        con.execute(
            "INSERT INTO reviews (task_id, rating, reviewed_at, tests_passed, tests_total, hint_used,"
            " solution_used, prev_interval_days, prev_due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, review["rating"], reviewed_at, review["tests_passed"], review["tests_total"],
             int(review["hint_used"]), int(review["solution_used"]), prev_interval_days, prev_due_date))
    con.close()


def undo_last_review(db_path, task_id):
    """Usuwa najnowszą ocenę zadania i przywraca termin sprzed niej.
    Zwraca {interval_days, due_date} albo None, gdy nie ma czego cofnąć (brak ocen lub stara ocena bez prev_*)."""
    con = connect(db_path)
    last = con.execute("SELECT id, prev_interval_days, prev_due_date FROM reviews WHERE task_id = ?"
                       " ORDER BY reviewed_at DESC, id DESC LIMIT 1", (task_id,)).fetchone()
    if last is None or last["prev_interval_days"] is None or last["prev_due_date"] is None:
        con.close()
        return None
    with con:
        con.execute("DELETE FROM reviews WHERE id = ?", (last["id"],))
        con.execute("UPDATE tasks SET interval_days = ?, due_date = ? WHERE id = ?",
                    (last["prev_interval_days"], last["prev_due_date"], task_id))
    con.close()
    return {"interval_days": last["prev_interval_days"], "due_date": last["prev_due_date"]}


# Najnowsza ocena zadania (data i ocena) — wspólny fragment SQL dla kolejki
LAST_REVIEW = ("(SELECT {col} FROM reviews r WHERE r.task_id = t.id"
               " ORDER BY r.reviewed_at DESC, r.id DESC LIMIT 1)")


def queue(db_path, today, language=None):
    """Zadania do powtórki dziś (kolejność jak due_task_ids) z datą i oceną ostatniej powtórki."""
    con = connect(db_path)
    sql = ("SELECT t.id, t.title, t.language, t.kind, t.description, "
           + LAST_REVIEW.format(col="reviewed_at") + " AS last_reviewed_at, "
           + LAST_REVIEW.format(col="rating") + " AS last_rating "
           "FROM tasks t WHERE t.due_date <= ?")
    params = [today]
    if language:
        sql += " AND t.language = ?"
        params.append(language)
    rows = con.execute(sql + " ORDER BY t.due_date, t.id", params).fetchall()
    con.close()
    return [dict(row) for row in rows]


def due_counts_between(db_path, start, end, language=None):
    """{data: liczba zadań} dla terminów do `end`; zaległe (przed `start`) liczą się do `start`."""
    con = connect(db_path)
    sql = ("SELECT CASE WHEN due_date < ? THEN ? ELSE due_date END AS day, COUNT(*) AS n "
           "FROM tasks WHERE due_date <= ?")
    params = [start, start, end]
    if language:
        sql += " AND language = ?"
        params.append(language)
    rows = con.execute(sql + " GROUP BY day", params).fetchall()
    con.close()
    return {row["day"]: row["n"] for row in rows}


def last_session(db_path):
    """Ostatni dzień z ocenami i liczba różnych zadań ocenionych tego dnia, albo None."""
    con = connect(db_path)
    row = con.execute("SELECT substr(reviewed_at, 1, 10) AS day, COUNT(DISTINCT task_id) AS n FROM reviews"
                      " GROUP BY day ORDER BY day DESC LIMIT 1").fetchone()
    con.close()
    return {"date": row["day"], "count": row["n"]} if row else None
