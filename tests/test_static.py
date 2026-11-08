import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "t.db")))


def test_vendor_and_shared_files_served(client):
    for path in ["/vendor/monaco/vs/loader.js", "/vendor/monaco/vs/editor/editor.main.js",
                 "/vendor/monaco/vs/basic-languages/python/python.js",
                 "/vendor/monaco/vs/basic-languages/csharp/csharp.js",
                 "/vendor/marked.umd.js", "/style.css", "/theme.js"]:
        assert client.get(path).status_code == 200, path
    css = client.get("/style.css").text
    assert ".lr-light" in css and "--accent" in css
    assert "leetrepeat-theme" in client.get("/theme.js").text
