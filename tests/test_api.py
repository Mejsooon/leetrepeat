from datetime import date

import pytest
from fastapi.testclient import TestClient

import main
from db import connect
from main import create_app
from runner import RuntimeMissing


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "t.db")


@pytest.fixture
def client(db_path):
    return TestClient(create_app(db_path), base_url="http://127.0.0.1:8000")


@pytest.fixture
def task_body():
    return {
        "title": "Odwróć listę", "language": "python", "kind": "function",
        "description": "Napisz `odwroc`", "starter_code": "def odwroc(l):\n    pass\n",
        "hint": "pętla", "solution": "def odwroc(l):\n    return l[::-1]\n",
        "tests": [{"input": "odwroc([1,2])", "expected": "[2,1]"}],
    }


@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(main, "today", lambda: date(2026, 11, 8))


def test_create_and_get(client, task_body):
    res = client.post("/api/tasks", json=task_body)
    assert res.status_code == 201
    task = client.get(f"/api/tasks/{res.json()['id']}").json()
    assert task["tests"] == [{"input": "odwroc([1,2])", "expected": "[2,1]"}]
    assert task["preview"] == {"again": 1, "partial": 1, "good": 3}
    assert task["last_reviewed_at"] is None
    assert task["title"] == "Odwróć listę"


def test_create_validation(client, task_body):
    no_title = {k: v for k, v in task_body.items() if k != "title"}
    assert client.post("/api/tasks", json=no_title).status_code == 422
    assert client.post("/api/tasks", json={**task_body, "tests": []}).status_code == 422
    assert client.post("/api/tasks", json={**task_body, "language": "java"}).status_code == 422


def test_list_filter_language(client, task_body):
    client.post("/api/tasks", json=task_body)
    client.post("/api/tasks", json={**task_body, "language": "csharp", "title": "C#"})
    tasks = client.get("/api/tasks?language=csharp").json()
    assert [t["title"] for t in tasks] == ["C#"]
    assert set(tasks[0]) == {"id", "title", "language", "kind", "due_date"}
    assert len(client.get("/api/tasks").json()) == 2


def test_update_replaces_tests_keeps_schedule(client, task_body):
    task_id = client.post("/api/tasks", json=task_body).json()["id"]
    client.post(f"/api/tasks/{task_id}/review", json={"rating": "good"})
    due_before = client.get(f"/api/tasks/{task_id}").json()["due_date"]
    two_tests = [{"input": "odwroc([])", "expected": "[]"}, {"input": "odwroc([1])", "expected": "[1]"}]
    assert client.put(f"/api/tasks/{task_id}", json={**task_body, "tests": two_tests}).status_code == 200
    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["tests"] == two_tests
    assert task["due_date"] == due_before


def test_delete_and_404(client, task_body):
    task_id = client.post("/api/tasks", json=task_body).json()["id"]
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    res = client.get(f"/api/tasks/{task_id}")
    assert res.status_code == 404 and res.json()["detail"] == "Nie ma takiego zadania"
    assert client.delete(f"/api/tasks/{task_id}").status_code == 404


def test_review_updates_due(client, task_body, fixed_today, db_path):
    task_id = client.post("/api/tasks", json=task_body).json()["id"]
    res = client.post(f"/api/tasks/{task_id}/review",
                      json={"rating": "good", "tests_passed": 1, "tests_total": 1, "hint_used": True})
    assert res.json() == {"interval_days": 3, "due_date": "2026-11-11"}
    assert client.get(f"/api/tasks/{task_id}").json()["last_reviewed_at"] is not None
    rows = connect(db_path).execute("SELECT * FROM reviews").fetchall()
    assert len(rows) == 1
    assert (rows[0]["tests_passed"], rows[0]["tests_total"], rows[0]["hint_used"]) == (1, 1, 1)


def test_review_unknown_task_404(client):
    assert client.post("/api/tasks/999/review", json={"rating": "good"}).status_code == 404


def test_due_and_summary_use_local_today(client, task_body, fixed_today):
    task_id = client.post("/api/tasks", json=task_body).json()["id"]
    assert client.get("/api/review/due").json() == [task_id]
    assert client.get("/api/review/due?language=python").json() == [task_id]
    assert client.get("/api/review/due?language=csharp").json() == []
    summary = client.get("/api/summary").json()
    assert summary == {"python": {"due": 1, "total": 1}, "csharp": {"due": 0, "total": 0}}
    client.post(f"/api/tasks/{task_id}/review", json={"rating": "again"})
    assert client.get("/api/review/due").json() == []
    assert client.get("/api/summary").json()["python"] == {"due": 0, "total": 1}


def test_run_endpoint(client):
    res = client.post("/api/run", json={"language": "python", "kind": "function",
                                        "code": "def f():\n    return 1\n",
                                        "tests": [{"input": "f()", "expected": "1"}]})
    assert res.json()["results"][0]["status"] == "pass"


def test_run_missing_runtime(client, monkeypatch):
    def missing(*args):
        raise RuntimeMissing("brak")
    monkeypatch.setattr(main, "run_tests", missing)
    res = client.post("/api/run", json={"language": "csharp", "kind": "program", "code": "",
                                        "tests": [{"input": "", "expected": ""}]})
    assert res.status_code == 400 and res.json()["detail"] == "brak"


def test_update_missing_task_404(client, task_body):    # przegląd: Important 4
    res = client.put("/api/tasks/9999", json=task_body)
    assert res.status_code == 404 and res.json()["detail"] == "Nie ma takiego zadania"


def test_rejects_foreign_host(client):                  # przegląd: Important 3 (DNS rebinding)
    res = client.post("/api/run", headers={"Host": "evil.example:8000"},
                      json={"language": "python", "kind": "program", "code": "print(1)",
                            "tests": [{"input": "", "expected": "1"}]})
    assert res.status_code == 400
    assert client.get("/api/summary", headers={"Host": "localhost:8000"}).status_code == 200
