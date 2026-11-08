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
    assert "Zacznij powtórkę" in home and "theme-toggle" in home
    assert "Biblioteka" in client.get("/list.html").text


def test_form_served(client):
    form = client.get("/form.html").text
    assert "Nowe zadanie" in form and "Sprawdź rozwiązanie" in form


def test_task_page_served(client):
    page = client.get("/task.html").text
    assert "Uruchom testy" in page and "Nie pamiętam" in page and "Przywróć kod startowy" in page


def test_v2_assets_served(client):
    for name in ["latin-400", "latin-500", "latin-ext-400", "latin-ext-500"]:
        assert client.get(f"/vendor/fonts/ibm-plex-mono-{name}.woff2").status_code == 200
    css = client.get("/style.css").text
    for needle in ["--forgot", "backdrop-filter", "prefers-reduced-transparency", "IBM Plex Mono", ".sr-only"]:
        assert needle in css, needle


def test_today_page_served(client):
    page = client.get("/").text
    for needle in ["Zacznij powtórkę", "Najbliższe dwa tygodnie", "theme-toggle"]:
        assert needle in page, needle


def test_library_page_served(client):
    page = client.get("/list.html").text
    assert "Biblioteka" in page and "Szukaj po tytule" in page


def test_editor_page_served(client):
    page = client.get("/form.html").text
    for needle in ["Nowe zadanie", "Podgląd", "Sprawdź rozwiązanie"]:
        assert needle in page, needle


def test_session_page_served(client):
    page = client.get("/task.html").text
    for needle in ["Jak dobrze pamiętałeś to zadanie?", "Cofnij ocenę", "Uruchom testy"]:
        assert needle in page, needle
