import glob
import json
import os
import subprocess
import sys

import pytest

from core.database import connect
from services.runner import run_tests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_FILES = sorted(glob.glob(os.path.join(ROOT, "seeds", "*.json")))


@pytest.mark.parametrize("seed_file", SEED_FILES, ids=os.path.basename)
def test_seed_solutions_pass_their_tests(seed_file):
    with open(seed_file, encoding="utf-8") as f:
        tasks = json.load(f)
    for task in tasks:
        results = run_tests(task["language"], task["kind"], task["solution"], task["tests"])
        assert [r["status"] for r in results] == ["pass"] * len(results), task["title"]


def test_import_is_idempotent(tmp_path):
    db_path = str(tmp_path / "t.db")
    seed = os.path.join(ROOT, "seeds", "python_variables.json")
    script = os.path.join(ROOT, "seeds", "import_tasks.py")
    first = subprocess.run([sys.executable, script, seed, "--db", db_path], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run([sys.executable, script, seed, "--db", db_path], capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    con = connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 10
    assert con.execute("SELECT COUNT(*) FROM tests").fetchone()[0] == 41
    assert "pominięto 10" in second.stdout
