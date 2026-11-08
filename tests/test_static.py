import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "t.db")), base_url="http://127.0.0.1:8000")


def test_vendor_and_shared_files_served(client):
    for path in ["/vendor/monaco/vs/loader.js", "/vendor/monaco/vs/editor/editor.main.js",
                 "/vendor/monaco/vs/basic-languages/python/python.js",
                 "/vendor/monaco/vs/basic-languages/csharp/csharp.js",
                 "/vendor/marked.umd.js", "/style.css", "/theme.js"]:
        assert client.get(path).status_code == 200, path
    css = client.get("/style.css").text
    assert ".lr-light" in css and "--accent" in css
    assert "leetrepeat-theme" in client.get("/theme.js").text


def test_pages_served(client):
    home = client.get("/").text
    assert "Do powtórki dziś" in home and "theme-toggle" in home
    assert "Wszystkie zadania" in client.get("/list.html").text


def test_form_served(client):
    form = client.get("/form.html").text
    assert "Nowe zadanie" in form and "Sprawdź rozwiązanie na testach" in form


def test_task_page_served(client):
    page = client.get("/task.html").text
    assert "Uruchom testy" in page and "Nie pamiętam" in page and "Przywróć kod startowy" in page
