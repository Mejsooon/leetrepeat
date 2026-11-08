"""LeetRepeat — serwer FastAPI (spec §6). Start: python main.py → http://127.0.0.1:8000"""
import os
from datetime import date, datetime
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from db import connect
from runner import RuntimeMissing, run_tests
from scheduler import next_review, preview

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def today() -> date:
    # Lokalna data komputera ("dziś" dla powtórek). Testy podmieniają tę funkcję.
    return date.today()


# --- Modele danych przychodzących z frontendu ---

class TestIn(BaseModel):
    input: str
    expected: str


class TaskIn(BaseModel):
    title: str = Field(min_length=1)
    language: Literal["python", "csharp"]
    kind: Literal["function", "program"]
    description: str = Field(min_length=1)
    starter_code: str = ""
    hint: str = ""
    solution: str = Field(min_length=1)
    tests: list[TestIn] = Field(min_length=1)


class RunIn(BaseModel):
    language: Literal["python", "csharp"]
    kind: Literal["function", "program"]
    code: str
    tests: list[TestIn] = Field(min_length=1)


class ReviewIn(BaseModel):
    rating: Literal["again", "partial", "good"]
    tests_passed: int | None = None
    tests_total: int | None = None
    hint_used: bool = False
    solution_used: bool = False


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="LeetRepeat")

    @app.get("/api/tasks")
    def list_tasks(language: str | None = None):
        con = connect(db_path)
        if language:
            rows = con.execute("SELECT id, title, language, kind, due_date FROM tasks"
                               " WHERE language = ? ORDER BY due_date, id", (language,)).fetchall()
        else:
            rows = con.execute("SELECT id, title, language, kind, due_date FROM tasks"
                               " ORDER BY due_date, id").fetchall()
        con.close()
        return [dict(row) for row in rows]

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: int):
        con = connect(db_path)
        row = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            con.close()
            raise HTTPException(404, "Nie ma takiego zadania")
        task = dict(row)
        task["tests"] = [dict(t) for t in con.execute(
            "SELECT input, expected FROM tests WHERE task_id = ? ORDER BY position", (task_id,))]
        last = con.execute("SELECT MAX(reviewed_at) FROM reviews WHERE task_id = ?", (task_id,)).fetchone()[0]
        con.close()
        task["last_reviewed_at"] = last
        task["preview"] = preview(task["interval_days"])
        return task

    @app.post("/api/tasks", status_code=201)
    def create_task(body: TaskIn):
        con = connect(db_path)
        with con:  # transakcja: zadanie i testy zapisują się razem albo wcale
            cur = con.execute(
                "INSERT INTO tasks (title, language, kind, description, starter_code, hint, solution,"
                " created_at, interval_days, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (body.title, body.language, body.kind, body.description, body.starter_code, body.hint,
                 body.solution, datetime.now().isoformat(timespec="seconds"), today().isoformat()))
            task_id = cur.lastrowid
            for position, test in enumerate(body.tests):
                con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, ?, ?, ?)",
                            (task_id, position, test.input, test.expected))
        con.close()
        return {"id": task_id}

    @app.put("/api/tasks/{task_id}")
    def update_task(task_id: int, body: TaskIn):
        con = connect(db_path)
        with con:
            cur = con.execute(
                "UPDATE tasks SET title = ?, language = ?, kind = ?, description = ?, starter_code = ?,"
                " hint = ?, solution = ? WHERE id = ?",
                (body.title, body.language, body.kind, body.description, body.starter_code, body.hint,
                 body.solution, task_id))
            if cur.rowcount == 0:
                con.close()
                raise HTTPException(404, "Nie ma takiego zadania")
            # Testy zastępujemy w całości; harmonogram (interval_days, due_date) zostaje bez zmian
            con.execute("DELETE FROM tests WHERE task_id = ?", (task_id,))
            for position, test in enumerate(body.tests):
                con.execute("INSERT INTO tests (task_id, position, input, expected) VALUES (?, ?, ?, ?)",
                            (task_id, position, test.input, test.expected))
        con.close()
        return {"id": task_id}

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        con = connect(db_path)
        with con:
            cur = con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))  # testy i historia: CASCADE
        con.close()
        if cur.rowcount == 0:
            raise HTTPException(404, "Nie ma takiego zadania")
        return Response(status_code=204)

    @app.get("/api/review/due")
    def due_tasks(language: str | None = None):
        con = connect(db_path)
        if language:
            rows = con.execute("SELECT id FROM tasks WHERE due_date <= ? AND language = ?"
                               " ORDER BY due_date, id", (today().isoformat(), language)).fetchall()
        else:
            rows = con.execute("SELECT id FROM tasks WHERE due_date <= ? ORDER BY due_date, id",
                               (today().isoformat(),)).fetchall()
        con.close()
        return [row["id"] for row in rows]

    @app.get("/api/summary")
    def summary():
        con = connect(db_path)
        result = {}
        for language in ("python", "csharp"):
            total = con.execute("SELECT COUNT(*) FROM tasks WHERE language = ?", (language,)).fetchone()[0]
            due = con.execute("SELECT COUNT(*) FROM tasks WHERE language = ? AND due_date <= ?",
                              (language, today().isoformat())).fetchone()[0]
            result[language] = {"due": due, "total": total}
        con.close()
        return result

    @app.post("/api/run")
    def run(body: RunIn):
        # Zwykła funkcja (nie async): FastAPI uruchamia ją w osobnym wątku, więc serwer nie blokuje się
        try:
            results = run_tests(body.language, body.kind, body.code, [t.model_dump() for t in body.tests])
        except RuntimeMissing as e:
            raise HTTPException(400, str(e))
        return {"results": results}

    @app.post("/api/tasks/{task_id}/review")
    def review(task_id: int, body: ReviewIn):
        con = connect(db_path)
        row = con.execute("SELECT interval_days FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            con.close()
            raise HTTPException(404, "Nie ma takiego zadania")
        new_interval, due = next_review(row["interval_days"], body.rating, today())
        with con:
            con.execute("UPDATE tasks SET interval_days = ?, due_date = ? WHERE id = ?",
                        (new_interval, due.isoformat(), task_id))
            con.execute(
                "INSERT INTO reviews (task_id, rating, reviewed_at, tests_passed, tests_total, hint_used,"
                " solution_used) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, body.rating, datetime.now().isoformat(timespec="seconds"), body.tests_passed,
                 body.tests_total, int(body.hint_used), int(body.solution_used)))
        con.close()
        return {"interval_days": new_interval, "due_date": due.isoformat()}

    # Frontend (pliki z static/) — montowany na końcu, żeby nie zasłaniał tras /api
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app(os.environ.get("LEETREPEAT_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                              "leetrepeat.db")))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
