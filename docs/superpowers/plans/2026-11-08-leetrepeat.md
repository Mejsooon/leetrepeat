# LeetRepeat — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lokalna aplikacja webowa z zadaniami programistycznymi (Python i C#), automatycznymi testami i powtórkami rozłożonymi w czasie.

**Architecture:** FastAPI serwuje API (`/api/...`) i statyczny frontend (czysty HTML/CSS/JS). Dane w pliku SQLite przez moduł `sqlite3`. Kod użytkownika uruchamiany przez `subprocess` (`sys.executable` dla Pythona, `dotnet run plik.cs` dla C#) w katalogu tymczasowym.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, uvicorn, pytest, httpx (TestClient); .NET 10 SDK; Monaco Editor 0.52.2 i marked 15 (lokalnie w `static/vendor/`).

**Spec:** `docs/superpowers/specs/2026-11-07-leetrepeat-design.md` — wykonawca czyta spec i plan razem. Wygląd ekranów: artefakt Design „LeetRepeat — makiety ekranów” (kolory, układ i teksty z makiet przenieść 1:1).

## Global Constraints

- Serwer nasłuchuje tylko na `127.0.0.1`, port `8000`.
- Plik bazy: zmienna środowiskowa `LEETREPEAT_DB`, domyślnie `leetrepeat.db` w katalogu projektu; dopisany do `.gitignore`.
- Języki: dokładnie `'python'` i `'csharp'`; typy: `'function'` i `'program'`; oceny: `'again'`, `'partial'`, `'good'`.
- Daty: `due_date` jako ISO `YYYY-MM-DD`, liczona od **lokalnej** daty komputera (`date.today()`), datetime jako ISO bez strefy (`datetime.now().isoformat(timespec="seconds")`).
- Limity czasu: Python 5 s na proces; C# 20 s na każde `dotnet run`.
- Cały interfejs po polsku, teksty jak na makietach.
- Styl kodu (prośba użytkownika): liniowy, czytelny od góry do dołu, **bez rozbijania na wiele małych funkcji pomocniczych**. Publiczne funkcje modułów są tylko te wymienione w blokach *Interfaces*.
- Frontend bez frameworka i kroku budowania; brak zasobów z internetu w czasie działania (Monaco i marked z `static/vendor/`).
- Motyw: zmienne CSS w `.lr-dark` / `.lr-light` na `<html>`, wartości kolorów skopiowane z makiet; klucz `localStorage` `leetrepeat-theme` (`'ciemny'`/`'jasny'`); domyślnie `prefers-color-scheme`, inaczej ciemny; Monaco `vs-dark` / `vs`.

## Review Focus

1. **Polskie znaki w kodzie i wyjściu** (`print("zażółć")`, `Console.WriteLine("gęś")`) — na Windows konsola domyślnie nie jest UTF-8; oczekiwane: poprawne porównanie. → test w Task 3 i Task 4 (env `PYTHONIOENCODING=utf-8`, `Console.OutputEncoding = UTF8` dopisywane w harnessie C#, `encoding="utf-8"` w `subprocess.run`).
2. **Program czyta więcej wejścia niż podano** (`input()` dwa razy przy jednej linii) — oczekiwane: status `error` z `EOFError`, nie zawieszenie. → test w Task 3.
3. **`print` do debugowania w zadaniu `function`** — oczekiwane: linie bez prefiksu `@@` ignorowane, test nadal `pass`. → test w Task 3.
4. **„Dziś” tuż po północy** — oczekiwane: zadanie z `due_date` = dzisiejsza data lokalna jest „do powtórki”; endpointy przyjmują datę lokalną, nie UTC. → `today` jako parametr w scheduler i nadpisywalny w API (Task 5, test z `monkeypatch`).
5. **Zadanie usunięte w trakcie sesji** — oczekiwane: sesja pomija je i idzie dalej zamiast pokazać błąd. → obsługa 404 w Task 9 (sprawdzenie ręczne w scenariuszu).

---

## Struktura plików

```
leetrepeat/
├── main.py            # Task 5 — FastAPI: endpointy, start serwera
├── db.py              # Task 2 — schemat i połączenie SQLite
├── runner.py          # Task 3–4 — uruchamianie kodu i porównanie
├── scheduler.py       # Task 1 — harmonogram powtórek
├── requirements.txt   # Task 1
├── pytest.ini         # Task 1
├── static/
│   ├── style.css      # Task 6 — motywy + wspólne style
│   ├── theme.js       # Task 6 — przełącznik motywu
│   ├── index.html     # Task 7 — Start
│   ├── list.html      # Task 7 — Lista
│   ├── form.html      # Task 8 — Formularz
│   ├── task.html      # Task 9 — Zadanie / sesja
│   └── vendor/        # Task 6 — monaco/vs/**, marked.umd.js
├── tests/
│   ├── test_scheduler.py, test_db.py, test_runner_python.py,
│   ├── test_runner_csharp.py, test_api.py, test_static.py
└── README.md          # Task 10
```

---

### Task 1: Szkielet projektu i harmonogram

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `scheduler.py`, `tests/test_scheduler.py`
- Modify: `.gitignore` (dopisać `leetrepeat.db`, `.venv/`)

**Interfaces:**
- Produces:
  - `next_review(interval_days: float, rating: str, today: date) -> tuple[float, date]` — nowy odstęp (bez zaokrąglenia) i `due_date = today + timedelta(days=round(nowy))`.
  - `preview(interval_days: float) -> dict[str, int]` — `{"again": n, "partial": n, "good": n}`, liczba dni po zaokrągleniu, wyliczona przez `next_review`.

- [ ] **Step 1:** `requirements.txt`: `fastapi`, `uvicorn`, `pydantic>=2`, `pytest`, `httpx`. `pytest.ini`: `[pytest]` + `testpaths = tests`. Utworzyć `.venv`, zainstalować.
- [ ] **Step 2: Testy (najpierw czerwone)** w `tests/test_scheduler.py`, `today = date(2026, 11, 8)`:

```python
@pytest.mark.parametrize("interval, rating, new_interval, due", [
    (0, "again", 1, date(2026, 11, 9)),
    (0, "partial", 1, date(2026, 11, 9)),
    (0, "good", 3, date(2026, 11, 11)),
    (6, "again", 1, date(2026, 11, 9)),
    (6, "partial", 7.2, date(2026, 11, 15)),
    (1, "partial", 2, date(2026, 11, 10)),     # max(1.2, 1+1)
    (6, "good", 15, date(2026, 11, 23)),
])
def test_next_review(interval, rating, new_interval, due):
    got_interval, got_due = next_review(interval, rating, today)
    assert got_interval == pytest.approx(new_interval)
    assert got_due == due

def test_preview_new_task():
    assert preview(0) == {"again": 1, "partial": 1, "good": 3}

def test_preview_existing():
    assert preview(6) == {"again": 1, "partial": 7, "good": 15}

def test_unknown_rating_raises():
    with pytest.raises(ValueError):
        next_review(1, "maybe", today)
```

- [ ] **Step 3:** `pytest tests/test_scheduler.py -v` → FAIL (brak modułu).
- [ ] **Step 4:** Zaimplementować `scheduler.py` wg tabeli ze spec §5.
- [ ] **Step 5:** `pytest tests/test_scheduler.py -v` → PASS.
- [ ] **Step 6:** Commit `feat: scheduler i szkielet projektu`.

---

### Task 2: Baza danych

**Files:**
- Create: `db.py`, `tests/test_db.py`

**Interfaces:**
- Produces:
  - `connect(path: str) -> sqlite3.Connection` — `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`, przy każdym połączeniu `CREATE TABLE IF NOT EXISTS` dla `tasks`, `tests`, `reviews` dokładnie wg spec §3 (z `position` w `tests`, `tests_total` w `reviews`, `ON DELETE CASCADE`).

- [ ] **Step 1: Testy** w `tests/test_db.py` (na `tmp_path / "t.db"`):
  - `test_tables_created` — `sqlite_master` zawiera `tasks`, `tests`, `reviews`.
  - `test_delete_task_cascades` — wstawić zadanie + 1 test + 1 review, `DELETE FROM tasks`, oba pozostałe `COUNT(*) == 0`.
  - `test_connect_twice_keeps_data` — zapis, zamknięcie, ponowne `connect`, wiersz istnieje.
- [ ] **Step 2:** `pytest tests/test_db.py -v` → FAIL.
- [ ] **Step 3:** Zaimplementować `db.py`.
- [ ] **Step 4:** `pytest tests/test_db.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: schemat SQLite`.

---

### Task 3: Runner — Python

**Files:**
- Create: `runner.py`, `tests/test_runner_python.py`

**Interfaces:**
- Produces:
  - `class RuntimeMissing(Exception)` — komunikat po polsku, np. `"Nie znaleziono dotnet — zainstaluj .NET 10 SDK (instrukcja w README)"`.
  - `run_tests(language: str, kind: str, code: str, tests: list[dict]) -> list[dict]` — `tests` to `[{"input": str, "expected": str}]`; zwraca listę w tej samej kolejności: `{"status": "pass"|"fail"|"error"|"timeout", "input": str, "expected": str, "actual": str|None, "message": str|None}`.

Zasady (spec §4): katalog `tempfile.TemporaryDirectory()`; `subprocess.run([sys.executable, "main.py"], cwd=tmp, input=..., capture_output=True, text=True, encoding="utf-8", timeout=5, env={**os.environ, "PYTHONIOENCODING": "utf-8"})`.
- `function`: jeden proces; do kodu użytkownika dopisać `import json` oraz dla każdego testu `i`:

```python
try:
    __r = <input>
    print("@@<i> OK " + json.dumps(__r, separators=(",", ":"), ensure_ascii=False))
except Exception as __e:
    print("@@<i> ERR " + type(__e).__name__ + ": " + str(__e))
```

  Parsowanie: linie zaczynające się od `@@`; `OK` → porównać `json.loads(expected) == json.loads(actual)`; brak linii dla testu lub niezerowy kod wyjścia bez linii → `error` z ostatnimi liniami stderr. `expected` niebędący JSON-em → `error`, `message = "Niepoprawny JSON w polu expected"`.
- `program`: jeden proces na test, `input` na stdin; porównanie po normalizacji (`\r\n`→`\n`, `rstrip()` każdej linii, usunięcie pustych linii na końcu); niezerowy kod wyjścia → `error` ze stderr.
- `TimeoutExpired` → `timeout` dla wszystkich testów tego procesu.
- Python nieznaleziony (gdy `sys.executable` pusty) → `RuntimeMissing`.

- [ ] **Step 1: Testy** w `tests/test_runner_python.py` (wszystkie wywołują `run_tests("python", ...)`):

```python
REV = "def odwroc(l):\n    return l[::-1]\n"

def test_function_pass_and_json_spacing():
    r = run_tests("python", "function", REV, [{"input": "odwroc([1,2,3])", "expected": "[3, 2, 1]"}])
    assert r[0]["status"] == "pass"

def test_function_fail_shows_actual():
    r = run_tests("python", "function", REV, [{"input": "odwroc([1,2])", "expected": "[1,2]"}])
    assert r[0]["status"] == "fail" and r[0]["actual"] == "[2,1]"

def test_function_exception_is_error_per_test():
    code = REV + "def boom():\n    raise ValueError('x')\n"
    r = run_tests("python", "function", code, [
        {"input": "boom()", "expected": "1"}, {"input": "odwroc([1])", "expected": "[1]"}])
    assert r[0]["status"] == "error" and "ValueError" in r[0]["message"]
    assert r[1]["status"] == "pass"

def test_syntax_error_marks_all_error():
    r = run_tests("python", "function", "def x(:\n", [{"input": "x()", "expected": "1"}] * 2)
    assert [t["status"] for t in r] == ["error", "error"]

def test_debug_print_ignored():                      # Review Focus 3
    code = "def f():\n    print('debug')\n    return 5\n"
    assert run_tests("python", "function", code, [{"input": "f()", "expected": "5"}])[0]["status"] == "pass"

def test_bad_expected_json():
    r = run_tests("python", "function", REV, [{"input": "odwroc([])", "expected": "nie json"}])
    assert r[0]["status"] == "error"

def test_program_pass_with_trailing_whitespace():
    code = "x = int(input())\nprint(x * 2, ' ')\nprint()\n"
    r = run_tests("python", "program", code, [{"input": "4", "expected": "8"}])
    assert r[0]["status"] == "pass"

def test_program_crlf_expected():
    r = run_tests("python", "program", "print('a')\nprint('b')\n", [{"input": "", "expected": "a\r\nb\r\n"}])
    assert r[0]["status"] == "pass"

def test_program_polish_chars():                     # Review Focus 1
    r = run_tests("python", "program", "print(input() + ' gęś')\n", [{"input": "zażółć", "expected": "zażółć gęś"}])
    assert r[0]["status"] == "pass"

def test_program_reads_too_much_input():             # Review Focus 2
    r = run_tests("python", "program", "input()\ninput()\n", [{"input": "1", "expected": ""}])
    assert r[0]["status"] == "error" and "EOFError" in r[0]["message"]

def test_timeout():
    r = run_tests("python", "program", "while True:\n    pass\n", [{"input": "", "expected": ""}])
    assert r[0]["status"] == "timeout"
```

- [ ] **Step 2:** `pytest tests/test_runner_python.py -v` → FAIL.
- [ ] **Step 3:** Zaimplementować gałąź Pythona w `runner.py`.
- [ ] **Step 4:** `pytest tests/test_runner_python.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: runner dla Pythona`.

---

### Task 4: Runner — C#

**Files:**
- Modify: `runner.py`
- Create: `tests/test_runner_csharp.py`

**Interfaces:**
- Consumes: `run_tests`, `RuntimeMissing` z Task 3 (ta sama sygnatura i format wyniku).

Zasady: `shutil.which("dotnet") is None` → `RuntimeMissing("Nie znaleziono dotnet — zainstaluj .NET 10 SDK (instrukcja w README)")`. Plik `main.cs` w katalogu tymczasowym, `subprocess.run(["dotnet", "run", "main.cs"], ..., encoding="utf-8", timeout=20, env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"})`.
- Linie `using ...;` z kodu użytkownika (dopasowanie `^\s*using\s+[\w.]+\s*;` na początku linii) przenieść na górę pliku.
- `function`: plik = przeniesione `using` + `using System.Text.Json;` + `Console.OutputEncoding = System.Text.Encoding.UTF8;` + dla każdego testu `try { Console.WriteLine("@@<i> OK " + JsonSerializer.Serialize(<input>)); } catch (Exception __e) { Console.WriteLine("@@<i> ERR " + __e.GetType().Name + ": " + __e.Message); }` + reszta kodu użytkownika. Parsowanie wyników jak w Task 3.
- `program`: plik = przeniesione `using` + `Console.OutputEncoding = System.Text.Encoding.UTF8; Console.InputEncoding = System.Text.Encoding.UTF8;` + kod użytkownika; `dotnet run main.cs` raz na test z `input` na stdin.
- Błąd kompilacji (niezerowy kod wyjścia, brak linii `@@`) → `error` dla wszystkich testów z komunikatem z stdout+stderr (dotnet wypisuje błędy kompilacji na stdout), przyciętym do linii zawierających `error CS`.

- [ ] **Step 1: Testy** w `tests/test_runner_csharp.py`, cały moduł z `pytestmark = pytest.mark.skipif(shutil.which("dotnet") is None, reason="brak dotnet")`:

```python
REV = "static int[] Odwroc(int[] a) { var r = (int[])a.Clone(); Array.Reverse(r); return r; }"

def test_function_pass():
    r = run_tests("csharp", "function", REV, [{"input": "Odwroc(new[]{1,2,3})", "expected": "[3,2,1]"}])
    assert r[0]["status"] == "pass"

def test_function_fail():
    r = run_tests("csharp", "function", REV, [{"input": "Odwroc(new[]{1,2})", "expected": "[1,2]"}])
    assert r[0]["status"] == "fail" and r[0]["actual"] == "[2,1]"

def test_function_static_class_and_using():
    code = "using System.Linq;\nstatic class S { public static int Suma(int[] a) => a.Sum(); }"
    r = run_tests("csharp", "function", code, [{"input": "S.Suma(new[]{1,2,3})", "expected": "6"}])
    assert r[0]["status"] == "pass"

def test_function_exception():
    code = "static int Dziel(int a, int b) => a / b;"
    r = run_tests("csharp", "function", code, [{"input": "Dziel(1, 0)", "expected": "0"}])
    assert r[0]["status"] == "error" and "DivideByZeroException" in r[0]["message"]

def test_compile_error_all_error():
    r = run_tests("csharp", "function", "static int X( { }", [{"input": "X()", "expected": "1"}] * 2)
    assert [t["status"] for t in r] == ["error", "error"] and "CS" in r[0]["message"]

def test_program_pass_polish():                      # Review Focus 1
    code = "var x = Console.ReadLine();\nConsole.WriteLine(x + \" gęś\");"
    r = run_tests("csharp", "program", code, [{"input": "zażółć", "expected": "zażółć gęś"}])
    assert r[0]["status"] == "pass"

def test_program_two_tests():
    code = "int x = int.Parse(Console.ReadLine());\nConsole.WriteLine(x * 2);"
    r = run_tests("csharp", "program", code, [{"input": "4", "expected": "8"}, {"input": "5", "expected": "11"}])
    assert [t["status"] for t in r] == ["pass", "fail"]
```

  Plus test bez skipif: `test_missing_dotnet_raises` — `monkeypatch.setattr(shutil, "which", lambda _: None)`, `pytest.raises(RuntimeMissing)`.
- [ ] **Step 2:** `pytest tests/test_runner_csharp.py -v` → FAIL (lub SKIP, jeśli brak dotnet — wtedy zainstalować .NET 10 SDK, jeśli to możliwe, albo zaznaczyć w raporcie, że testy C# nie zostały uruchomione).
- [ ] **Step 3:** Zaimplementować gałąź C# w `runner.py`.
- [ ] **Step 4:** `pytest tests/test_runner_csharp.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: runner dla C#`.

---

### Task 5: API (FastAPI)

**Files:**
- Create: `main.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `db.connect`, `scheduler.next_review`, `scheduler.preview`, `runner.run_tests`, `runner.RuntimeMissing`.
- Produces:
  - `create_app(db_path: str) -> FastAPI`; moduł ma `app = create_app(os.environ.get("LEETREPEAT_DB", "leetrepeat.db"))` i `if __name__ == "__main__": uvicorn.run(app, host="127.0.0.1", port=8000)`.
  - `today() -> date` na poziomie modułu (zwraca `date.today()`); endpointy wołają `main.today()`, żeby test mógł go podmienić (Review Focus 4).
  - Modele Pydantic: `TestIn{input: str, expected: str}`; `TaskIn{title: str (min 1), language: Literal["python","csharp"], kind: Literal["function","program"], description: str (min 1), starter_code: str = "", hint: str = "", solution: str (min 1), tests: list[TestIn] (min 1)}`; `RunIn{language, kind, code: str, tests: list[TestIn] (min 1)}`; `ReviewIn{rating: Literal["again","partial","good"], tests_passed: int | None = None, tests_total: int | None = None, hint_used: bool = False, solution_used: bool = False}`.
  - Kształty odpowiedzi (używane przez frontend):
    - `GET /api/tasks?language=` → `[{id, title, language, kind, due_date}]` posortowane `due_date, id`.
    - `GET /api/tasks/{id}` → wszystkie kolumny `tasks` + `tests: [{input, expected}]` (wg `position`) + `preview: {again, partial, good}` + `last_reviewed_at: str | None`.
    - `POST /api/tasks` → `201`, `{id}`; nowe zadanie: `interval_days = 0`, `due_date = today()`.
    - `PUT /api/tasks/{id}` → `{id}`; testy zastąpione w całości, `interval_days` i `due_date` bez zmian.
    - `DELETE /api/tasks/{id}` → `204`.
    - `GET /api/review/due?language=` → `[id, ...]` z `due_date <= today()`, `ORDER BY due_date, id`.
    - `GET /api/summary` → `{"python": {"due": n, "total": n}, "csharp": {"due": n, "total": n}}`.
    - `POST /api/run` → `{"results": [...]}` (format z Task 3); `RuntimeMissing` → `400 {"detail": komunikat}`.
    - `POST /api/tasks/{id}/review` → zapis w `reviews` + aktualizacja `tasks`; odpowiedź `{interval_days, due_date}`.
  - Nieistniejące id → `404 {"detail": "Nie ma takiego zadania"}`.
  - Po trasach API: `app.mount("/", StaticFiles(directory=<katalog main.py>/static, html=True))`.

- [ ] **Step 1: Testy** w `tests/test_api.py`; fixture `client` = `TestClient(create_app(str(tmp_path / "t.db")))`; fixture `task_body` = poprawne zadanie Python `function` z jednym testem. Testy:
  - `test_create_and_get` — POST 201, GET zawiera `tests`, `preview == {"again":1,"partial":1,"good":3}`, `last_reviewed_at is None`.
  - `test_create_validation` — brak `title` → 422; `tests: []` → 422; `language: "java"` → 422.
  - `test_list_filter_language` — zadanie Python + C#, `?language=csharp` zwraca jedno.
  - `test_update_replaces_tests_keeps_schedule` — po review `good`, PUT z dwoma testami; GET ma 2 testy i ten sam `due_date`.
  - `test_delete_and_404` — DELETE 204, GET 404, DELETE ponownie 404.
  - `test_review_updates_due` — `monkeypatch.setattr(main, "today", lambda: date(2026, 11, 8))`; review `good` na nowym → `due_date == "2026-11-11"`; `last_reviewed_at` nie jest `None`; w `reviews` jeden wiersz z `tests_passed`/`tests_total`.
  - `test_due_and_summary_use_local_today` — `today` podmienione na `2026-11-08`; zadanie utworzone tego dnia jest w `/api/review/due` i w `summary["python"] == {"due": 1, "total": 1}`; po review `again` → już nie ma go w `due`, `total` nadal 1.
  - `test_run_endpoint` — POST `/api/run` z kodem Pythona → `results[0]["status"] == "pass"`.
  - `test_run_missing_runtime` — `monkeypatch.setattr(main, "run_tests", <funkcja rzucająca RuntimeMissing("brak")>)` → 400, `detail == "brak"`.
- [ ] **Step 2:** `pytest tests/test_api.py -v` → FAIL.
- [ ] **Step 3:** Zaimplementować `main.py` (utworzyć pusty `static/` z `index.html` zawierającym `LeetRepeat`, żeby mount działał; Task 7 go zastąpi).
- [ ] **Step 4:** `pytest -v` (całość) → PASS.
- [ ] **Step 5:** Commit `feat: API`.

---

### Task 6: Frontend — zasoby wspólne (vendor, style, motyw)

**Files:**
- Create: `static/vendor/monaco/vs/**`, `static/vendor/marked.umd.js`, `static/style.css`, `static/theme.js`, `tests/test_static.py`

**Interfaces:**
- Produces (używane przez Task 7–9):
  - `style.css`: zmienne motywu w `html.lr-dark` / `html.lr-light` o nazwach i wartościach z makiet (`--bg`, `--header`, `--surface`, `--code-bg`, `--raised`, `--border`, `--text`, `--muted`, `--subtle`, `--accent`, `--on-accent`, `--blue-text`, `--purple`, `--py-chip`, `--cs-chip`, `--green*`, `--red*`, `--orange*`, `--hint-*` …); klasy wspólne: `.lr-header`, `.lr-logo`, `.lr-nav a` (+ `.active`), `.btn`, `.btn-primary`, `.btn-run`, `.chip-python`, `.chip-csharp`, `.chip-kind`, `.card`, `.seg` (przełącznik segmentowy, `.seg button.on`), `.result-pass`, `.result-fail`, `.result-error`, `.result-timeout`, `.rate-again`, `.rate-partial`, `.rate-good`. Czcionki: Inter i JetBrains Mono przez stos `Inter, system-ui, sans-serif` / `"JetBrains Mono", ui-monospace, monospace` (bez pobierania z internetu).
  - `theme.js` (ładowany w `<head>` przed `style.css`, bez `defer`): ustawia klasę na `document.documentElement` wg `localStorage['leetrepeat-theme']` → `prefers-color-scheme` → ciemny; po `DOMContentLoaded` podpina kliknięcie przycisku `#theme-toggle` (zapis do `localStorage`, podmiana klasy, ikona słońce/księżyc jak na makietach) i wysyła `window.dispatchEvent(new CustomEvent("themechange", {detail: "ciemny"|"jasny"}))`. Globalnie: `window.lrIsDark() -> boolean`.

- [ ] **Step 1:** Pobrać zależności: w katalogu tymczasowym `npm pack monaco-editor@0.52.2 marked@15`, rozpakować; skopiować `package/min/vs` → `static/vendor/monaco/vs`, `package/lib/marked.umd.js` → `static/vendor/marked.umd.js`. Dołączyć pliki licencji (`LICENSE`) obok.
- [ ] **Step 2: Test** `tests/test_static.py::test_vendor_and_shared_files_served` — `TestClient` na `create_app(tmp db)`; `GET /vendor/monaco/vs/loader.js`, `/vendor/marked.umd.js`, `/style.css`, `/theme.js` → 200; `style.css` zawiera `.lr-light` i `--accent`.
- [ ] **Step 3:** `pytest tests/test_static.py -v` → FAIL.
- [ ] **Step 4:** Napisać `style.css` (wartości kolorów 1:1 z makiet, oba motywy) i `theme.js`.
- [ ] **Step 5:** `pytest tests/test_static.py -v` → PASS.
- [ ] **Step 6:** Commit `feat: wspólne style, motyw jasny/ciemny, Monaco i marked lokalnie`.

---

### Task 7: Ekrany Start i Lista

**Files:**
- Create/replace: `static/index.html`, `static/list.html`
- Modify: `tests/test_static.py`

**Interfaces:**
- Consumes: `GET /api/summary`, `GET /api/tasks?language=`, `DELETE /api/tasks/{id}`; `style.css`, `theme.js`.
- Produces: linki używane przez inne ekrany — `task.html?session=python|csharp|all`, `task.html?id=<id>`, `form.html`, `form.html?id=<id>`.

Każdy ekran ma ten sam nagłówek (logo `</>` + „LeetRepeat”, `#theme-toggle`, nawigacja Start / Wszystkie zadania / + Dodaj zadanie) wpisany wprost w HTML. JS w `<script>` na dole strony, jeden blok, bez modułów.
- **Start:** data po polsku (`toLocaleDateString("pl-PL", {weekday, day, month})`), nagłówek „Do powtórki dziś: N zadań” (odmiana: 1 zadanie, 2–4 zadania, 5+ zadań), dwie karty języków (`due`, „X zadań łącznie”, przycisk „Powtórz Python” → `?session=python`), główny przycisk „Zacznij powtórkę — wszystkie języki (N)” → `?session=all`. Gdy `N == 0`: zamiast przycisków napis „Koniec na dziś 🎉” i link do listy.
- **Lista:** licznik „N zadań · posortowane wg następnej powtórki”, przełącznik Wszystkie / Python / C# (`.seg`), tabela: Tytuł, Język (chip), Typ, Następna powtórka („dziś” wyróżnione kolorem `--orange` dla `due_date <= dziś`, „jutro”, „za N dni”), akcje Otwórz / Edytuj / Usuń. Usuń: `confirm("Usunąć zadanie „<tytuł>”? Testy i historia ocen też zostaną usunięte.")` → DELETE → odświeżenie listy. Pusta lista: „Brak zadań — dodaj pierwsze” z linkiem do formularza.

- [ ] **Step 1: Test** `test_pages_served` — `GET /` zawiera `Do powtórki dziś` i `theme-toggle`; `GET /list.html` zawiera `Wszystkie zadania`.
- [ ] **Step 2:** `pytest tests/test_static.py -v` → FAIL.
- [ ] **Step 3:** Napisać oba pliki wg makiet.
- [ ] **Step 4:** `pytest -v` → PASS. Ręcznie: `python main.py`, dodać zadanie przez `curl -X POST localhost:8000/api/tasks -H 'Content-Type: application/json' -d @przyklad.json`, sprawdzić liczniki na Start, filtr i usuwanie na Liście, przełącznik motywu (zostaje po odświeżeniu).
- [ ] **Step 5:** Commit `feat: ekrany Start i Lista`.

---

### Task 8: Formularz zadania

**Files:**
- Create: `static/form.html`
- Modify: `tests/test_static.py`

**Interfaces:**
- Consumes: `GET/POST/PUT /api/tasks[/{id}]`, `POST /api/run`; Monaco (`require.config({paths: {vs: "/vendor/monaco/vs"}})`), zdarzenie `themechange`.

Zachowanie (makieta 4):
- Pola: Tytuł, Język (`.seg` Python / C#), Typ (`.seg` „function — wywołanie funkcji” / „program — wejście / wyjście”), Treść (textarea, Markdown), Kod startowy (Monaco), Podpowiedź (textarea), Rozwiązanie wzorcowe (Monaco), Testy (wiersze `input` + `expected` + usuń, „+ dodaj test”; na start jeden pusty wiersz).
- Zmiana języka przełącza język obu edytorów (`python` / `csharp`). Zmiana typu zmienia nagłówki kolumn i opis: `function` → „Wywołanie funkcji” / „Oczekiwany wynik (JSON)” / „Wynik porównywany jako JSON — [3, 2, 1] = [3,2,1]”; `program` → „Wejście (stdin)” / „Oczekiwane wyjście (stdout)” / „Porównanie tekstu, bez spacji i pustych linii na końcu”. Kolumna `input` dla `program` to textarea (wejście wieloliniowe), dla `function` zwykłe pole.
- „Sprawdź rozwiązanie na testach” → `POST /api/run` z rozwiązaniem wzorcowym; wynik: zielony pasek „Rozwiązanie wzorcowe przechodzi N / N testy — można zapisywać.” albo lista nieudanych testów (jak na ekranie Zadania); błąd 400 → czerwony komunikat z `detail`.
- „Zapisz zadanie” → POST (nowe) lub PUT (`?id=`) → przejście do `list.html`. Błąd 422 → komunikat przy polu z `detail[].loc` (np. „To pole jest wymagane”), formularz nie znika. Puste wiersze testów (oba pola puste) są pomijane przy zapisie.
- `?id=` → nagłówek „Edytuj zadanie”, pola wypełnione z `GET /api/tasks/{id}`.

- [ ] **Step 1: Test** `test_form_served` — `GET /form.html` zawiera `Nowe zadanie` i `Sprawdź rozwiązanie na testach`.
- [ ] **Step 2:** `pytest tests/test_static.py -v` → FAIL.
- [ ] **Step 3:** Napisać `form.html`.
- [ ] **Step 4:** `pytest -v` → PASS. Ręcznie: utworzyć cztery zadania (Python/C# × function/program) z makiety, „Sprawdź” daje N / N, zapis, edycja zachowuje dane, zapis bez tytułu pokazuje błąd przy polu.
- [ ] **Step 5:** Commit `feat: formularz zadania`.

---

### Task 9: Ekran zadania i sesja powtórki

**Files:**
- Create: `static/task.html`
- Modify: `tests/test_static.py`

**Interfaces:**
- Consumes: `GET /api/review/due?language=`, `GET /api/tasks/{id}`, `POST /api/run`, `POST /api/tasks/{id}/review`; Monaco, marked, `themechange`.

Zachowanie (makieta 2):
- `?session=python|csharp|all` → raz pobiera listę id (`all` = bez parametru `language`), trzyma ją w zmiennej JS; pasek: „Sesja: Python | C# | wszystkie języki”, `n / m` z paskiem postępu, „Zakończ sesję” → `/`. Pusta lista → „Koniec na dziś 🎉” + link na Start.
- `?id=<id>` → jedno zadanie, bez paska sesji; po ocenie przycisk „Wróć do listy”.
- Lewa kolumna: chipy języka i typu, „ostatnio: X dni temu” (z `last_reviewed_at`; „dziś” dla 0; ukryte gdy `null`), tytuł, treść przez `marked.parse`, rozwijane „Podpowiedź” i „Pełne rozwiązanie” (pokaż/ukryj; pierwsze otwarcie ustawia `hint_used` / `solution_used = true`; rozwiązanie w bloku `pre` z czcionką mono).
- Prawa kolumna: Monaco z `starter_code`, nagłówek pliku `rozwiazanie.py` / `Rozwiazanie.cs`, „Uruchom testy” (w trakcie: przycisk wyłączony, tekst „Uruchamiam…”; dla C# dopisek „pierwsze uruchomienie C# trwa kilka sekund”), „Przywróć kod startowy” (ustawia `starter_code` w edytorze), czas wykonania obok („Python · 0,4 s”, mierzony w JS). Wyniki: licznik „k / n zaliczone” i wiersze ✓ OK / ✗ BŁĄD (oczekiwano / otrzymano) / 💥 wyjątek (`message` w `pre`) / ⏱️ przekroczony czas. Błąd 400 → czerwony komunikat z `detail`.
- Oceny: trzy przyciski „Nie pamiętam” / „Częściowo” / „Dobrze pamiętam” z `preview` pod spodem („jutro”, „za N dni”). Klik → `POST /review` z `tests_passed` / `tests_total` z ostatniego uruchomienia (albo `null`) i flagami podglądu → pasek „Zapisano: <ocena> · następna powtórka <kiedy>” + „Następne zadanie →” (w sesji) .
- Następne zadanie: `GET /api/tasks/{id}`; **404 → pominąć i wziąć kolejne** (Review Focus 5).

- [ ] **Step 1: Test** `test_task_page_served` — `GET /task.html` zawiera `Uruchom testy`, `Nie pamiętam`, `Przywróć kod startowy`.
- [ ] **Step 2:** `pytest tests/test_static.py -v` → FAIL.
- [ ] **Step 3:** Napisać `task.html`.
- [ ] **Step 4:** `pytest -v` → PASS. Ręcznie: sesja „wszystkie” z zadaniami z Task 8 — błędne rozwiązanie pokazuje ✗ z oczekiwano/otrzymano, poprawne ✓, ocena przesuwa datę na Liście; w trakcie sesji usunąć kolejne zadanie w drugiej karcie → sesja je pomija; motyw przełącza także Monaco.
- [ ] **Step 5:** Commit `feat: ekran zadania i sesja powtórki`.

---

### Task 10: README i weryfikacja końcowa

**Files:**
- Create: `README.md`

Zawartość (po polsku): czym jest LeetRepeat (2 zdania); wymagania (Python 3.11+, .NET 10 SDK); instalacja i uruchomienie osobno dla **Parrot OS** (`python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`, instalacja .NET 10 przez `dotnet-install.sh --channel 10.0` + dopisanie do `PATH`) i **Windows / PowerShell** (`py -m venv .venv`, `.venv\Scripts\Activate.ps1`, `winget install Microsoft.DotNet.SDK.10`); start `python main.py` → `http://127.0.0.1:8000`; kopia zapasowa = skopiowanie `leetrepeat.db`; przykład zadania `function` i `program` w obu językach (jak w formularzu); `pytest` do testów.

- [ ] **Step 1:** Napisać `README.md`.
- [ ] **Step 2:** `pytest -v` → wszystkie PASS (C# PASS lub SKIP z adnotacją w raporcie).
- [ ] **Step 3:** Scenariusz ręczny ze spec §8 od zera na świeżej bazie (`LEETREPEAT_DB=/tmp/czysta.db python main.py`).
- [ ] **Step 4:** Commit `docs: README` i push na `origin main`.
