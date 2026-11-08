"""Import zadań z pliku JSON do bazy LeetRepeat.

Użycie (z głównego folderu projektu):
    python seeds/import_tasks.py seeds/python_variables.json
    python seeds/import_tasks.py seeds/python_variables.json --db inna_baza.db

Zadanie o tym samym tytule i języku, które już jest w bazie, zostaje pominięte —
skrypt można bezpiecznie uruchomić kilka razy.
"""
import json
import os
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from db import connect  # noqa: E402

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

seed_file = sys.argv[1]
db_path = os.environ.get("LEETREPEAT_DB", os.path.join(ROOT, "leetrepeat.db"))
if "--db" in sys.argv:
    db_path = sys.argv[sys.argv.index("--db") + 1]

with open(seed_file, encoding="utf-8") as f:
    tasks = json.load(f)

con = connect(db_path)
added = 0
skipped = 0
with con:  # wszystko w jednej transakcji
    for task in tasks:
        exists = con.execute("SELECT id FROM tasks WHERE title = ? AND language = ?",
                             (task["title"], task["language"])).fetchone()
        if exists:
            skipped += 1
            continue
        # Nowe zadanie: do powtórki od dziś, jak przy dodaniu przez formularz
        cur = con.execute(
            "INSERT INTO tasks (title, language, kind, description, starter_code, hint, solution,"
            " created_at, interval_days, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (task["title"], task["language"], task["kind"], task["description"], task.get("starter_code", ""),
             task.get("hint", ""), task["solution"], datetime.now().isoformat(timespec="seconds"),
             date.today().isoformat()))
        for position, test in enumerate(task["tests"]):
            con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, ?, ?, ?)",
                        (cur.lastrowid, position, test["input"], test["expected"]))
        added += 1
con.close()

print(f"Baza: {db_path}")
print(f"Dodano {added}, pominięto {skipped} (już były w bazie).")
