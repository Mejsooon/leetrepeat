# LeetRepeat v2 — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Frontend w stylu makiet v2 oraz funkcje F1–F7 ze specyfikacji v2.

**Architecture:** Zmiany backendu idą przez istniejące warstwy (`core/` migracja, `repository/` SQL, `services/` logika, `api/` trasy). Frontend to dalej czysty HTML/CSS/JS w `static/` — cztery pliki przepisane na nowy wygląd, wspólny `style.css` z tokenami z makiet.

**Tech Stack:** jak v1 (FastAPI, SQLite, pytest, Monaco 0.52.2, marked 15) + IBM Plex Mono lokalnie (`@fontsource/ibm-plex-mono`).

**Spec:** `docs/superpowers/specs/2026-11-08-leetrepeat-v2-design.md` (+ v1 dla wszystkiego, czego v2 nie zmienia). Wygląd: artefakt Design „LeetRepeat — makiety v2”.

## Global Constraints

- Kod prosty i liniowy, bez mnożenia funkcji pomocniczych (prośba użytkownika); SQL tylko w `repository/`, decyzje i daty w `services/`, HTTP w `api/routes.py`.
- „Dziś” zawsze z `services.tasks.today()` (lokalna data); testy podmieniają tę funkcję.
- Kolory, promienie, odstępy i teksty 1:1 z makiet v2; interfejs po polsku, zdania (bez WIELKICH LITER w etykietach).
- Czcionka UI: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif`; kod: `"IBM Plex Mono"` z `static/vendor/fonts/`.
- Brak zasobów z internetu w czasie działania.
- `prefers-reduced-motion` → bez animacji; `prefers-reduced-transparency` → paski z pełnym tłem.
- Tytuły i komunikaty wstawiane przez `textContent` (nie `innerHTML`); Markdown tylko przez `marked`.

## Review Focus

1. **Podwójne kliknięcie „Cofnij ocenę”** — drugie wywołanie cofnęłoby starszą ocenę. Oczekiwane: przycisk blokowany od razu po kliknięciu i znika po sukcesie. → Task 8 (sprawdzenie w scenariuszu przeglądarki).
2. **Wciśnięcie `1` w wyszukiwarce, tytule lub edytorze** — nie może zapisać oceny. → Task 8 (scenariusz: wpisanie „1” w edytorze nie zmienia paska ocen).
3. **Migracja na bazie użytkownika z v1 uruchomiona dwa razy** — drugie połączenie nie może rzucić „duplicate column”. → Task 1 test `test_migration_adds_prev_columns_once`.
4. **Zaległe zadania i filtr języka w wykresie** — zadanie z terminem wczoraj liczy się do dziś i tylko w swoim języku. → Task 3 test `test_forecast_counts_overdue_today_and_filters_language`.
5. **Bardzo długi tytuł zadania** — w talii, na liście i w sesji zawija się lub ucina wielokropkiem, nie rozpycha układu. → Task 5–8 (CSS `overflow-wrap: anywhere`; sprawdzenie w scenariuszu z tytułem 120 znaków).

---

### Task 1: Migracja bazy i zapis stanu sprzed oceny

**Files:** Modify `core/database.py`, `repository/tasks.py` (`save_review`), `services/tasks.py` (`review_task`); Test `tests/test_db.py`, `tests/test_api.py`

**Interfaces:**
- Produces: kolumny `reviews.prev_interval_days REAL NULL`, `reviews.prev_due_date TEXT NULL`; `repo.save_review(db_path, task_id, review, interval_days, due_date, reviewed_at, prev_interval_days, prev_due_date)`.

- [ ] **Step 1: Testy**
  - `tests/test_db.py::test_migration_adds_prev_columns_once` — utworzyć plik bazy schematem v1 (ręczny `CREATE TABLE reviews` bez `prev_*` + `tasks`, `tests`), dwa razy `connect(path)`; `PRAGMA table_info(reviews)` zawiera `prev_interval_days` i `prev_due_date`; drugie połączenie bez wyjątku.
  - `tests/test_api.py::test_review_stores_previous_state` — nowe zadanie (`today` = 2026-11-08), review `good`; wiersz `reviews` ma `prev_interval_days == 0` i `prev_due_date == "2026-11-08"`.
- [ ] **Step 2:** `.venv/bin/pytest tests/test_db.py tests/test_api.py -q` → 2 FAIL.
- [ ] **Step 3:** W `connect()` po `executescript(SCHEMA)`: odczyt `PRAGMA table_info(reviews)`, `ALTER TABLE reviews ADD COLUMN …` dla brakujących. Dodać kolumny także do `SCHEMA` (nowe bazy). `review_task` przekazuje `task["interval_days"]`, `task["due_date"]`.
- [ ] **Step 4:** `.venv/bin/pytest -q` → wszystko PASS.
- [ ] **Step 5:** Commit `feat: migracja reviews (prev_*) i zapis stanu sprzed oceny`.

---

### Task 2: Cofnięcie oceny (F2)

**Files:** Modify `repository/tasks.py`, `services/tasks.py`, `api/routes.py`; Test `tests/test_api.py`

**Interfaces:**
- Consumes: kolumny z Task 1.
- Produces: `repo.undo_last_review(db_path, task_id) -> dict | None` — w jednej transakcji usuwa najnowszą ocenę (`ORDER BY reviewed_at DESC, id DESC`) i ustawia `tasks.interval_days/due_date` z jej `prev_*`; zwraca `{interval_days, due_date}`; `None`, gdy brak ocen albo `prev_*` NULL (nic nie zmienia). `service.undo_review(db_path, task_id) -> dict | None | "missing"` — `"missing"` gdy brak zadania. Trasa `POST /api/tasks/{id}/review/undo` → 200 / 404 `"Nie ma takiego zadania"` / 409 `"Tej oceny nie da się cofnąć"`.

- [ ] **Step 1: Testy** w `tests/test_api.py` (z `fixed_today`):
  - `test_undo_restores_previous_state` — review `good` (due 2026-11-11), undo → `{"interval_days": 0, "due_date": "2026-11-08"}`; GET zadania: `due_date == "2026-11-08"`, `last_reviewed_at is None`; tabela `reviews` pusta.
  - `test_undo_only_latest` — review `good`, review `again`, undo → stan po `good` (`due_date == "2026-11-11"`), w `reviews` jeden wiersz.
  - `test_undo_without_reviews_409` — nowe zadanie, undo → 409, `detail == "Tej oceny nie da się cofnąć"`.
  - `test_undo_legacy_review_409` — wstawić ręcznie review z `prev_* = NULL`, undo → 409, wiersz zostaje.
  - `test_undo_missing_task_404`.
- [ ] **Step 2:** pytest → 5 FAIL.
- [ ] **Step 3:** Zaimplementować trzy warstwy.
- [ ] **Step 4:** `.venv/bin/pytest -q` → PASS.
- [ ] **Step 5:** Commit `feat: cofnięcie oceny`.

---

### Task 3: Nowe dane do odczytu (kolejka, prognoza, ostatnia sesja, utrwalenie)

**Files:** Modify `repository/tasks.py`, `services/tasks.py`, `api/routes.py`; Test `tests/test_api.py`

**Interfaces:**
- Produces:
  - `GET /api/tasks` — element ma też `interval_days`.
  - `GET /api/tasks/{id}` — dochodzi `last_rating` (najnowsza ocena lub `null`).
  - `repo.queue(db_path, today, language=None) -> list[dict]` i `GET /api/review/queue?language=` → `[{id, title, language, kind, description, last_reviewed_at, last_rating}]`, kolejność `due_date, id`, tylko `due_date <= today`.
  - `repo.due_counts_between(db_path, start, end, language=None) -> dict[str, int]` (data → liczba, zadania z `due_date <= end`; zaległe przypisane do `start`); `service.forecast(db_path, language=None) -> list[{date, count}]` — 14 dni; `GET /api/forecast?language=`.
  - `repo.last_session(db_path) -> dict | None` — `{date: "YYYY-MM-DD", count}`: najnowsza data `substr(reviewed_at, 1, 10)` i `COUNT(DISTINCT task_id)` tego dnia; `GET /api/summary` dostaje klucz `last_session`.

- [ ] **Step 1: Testy** (`fixed_today` = 2026-11-08):
  - `test_list_includes_interval_days` — po review `good` element listy ma `interval_days == 3`.
  - `test_get_task_last_rating` — `null` przed oceną, `"partial"` po review `partial`.
  - `test_queue_returns_due_with_last_rating` — dwa zadania, jedno ocenione `again` wczoraj (podmienić `today` na 2026-11-07, ocenić, wrócić do 2026-11-08) → kolejka zawiera oba; ocenione ma `last_rating == "again"`; `?language=csharp` → `[]`.
  - `test_forecast_counts_overdue_today_and_filters_language` — zadanie Python z `due_date` ustawionym SQL-em na 2026-11-07, zadanie Python na 2026-11-10, zadanie C# na 2026-11-08, zadanie Python na 2026-11-30 → `/api/forecast` ma 14 elementów, `[0] == {"date": "2026-11-08", "count": 2}`, `[2]["count"] == 1`, `[13]["date"] == "2026-11-21"`, suma = 3; `?language=python` → `[0]["count"] == 1`.
  - `test_summary_last_session` — bez ocen `last_session is None`; po 2 ocenach jednego zadania i 1 drugiego tego samego dnia → `{"date": <data reviewed_at>, "count": 2}`.
- [ ] **Step 2:** pytest → FAIL.
- [ ] **Step 3:** Zaimplementować; `reviewed_at` przy zapisie z `service.now()` (lokalny czas), więc `substr(…,1,10)` to lokalna data.
- [ ] **Step 4:** `.venv/bin/pytest -q` → PASS.
- [ ] **Step 5:** Commit `feat: kolejka, prognoza 14 dni, ostatnia sesja, interval w liście`.

---

### Task 4: Wspólne style v2, czcionka kodu

**Files:** Replace `static/style.css`; Create `static/vendor/fonts/ibm-plex-mono-{400,500}.woff2` + `LICENSE`; Modify `tests/test_static.py`

**Interfaces:**
- Produces (dla Task 5–8): tokeny CSS z makiet v2 na `html.lr-light` / `html.lr-dark` (nazwy jak w makietach: `--bg --surface --sunken --ink --ink-2 --muted --line --line-strong --accent --accent-soft --on-accent --forgot* --partial* --good* --code-bg --glass --shadow --py --py-bg --cs --cs-bg`); klasy: `.bar`, `.btn` (`.primary`, `.quiet`), `.chip` (`.py`, `.cs`), `.seg` (+`button.on`), `.kbd`, `.field`, `.help`, `.input`, `.card`, `.container` (max 1240 px, padding 32 px; na telefonie 16 px), `.sr-only`. `theme.js` bez zmian (klasy `lr-dark`/`lr-light`).

- [ ] **Step 1:** `npm pack @fontsource/ibm-plex-mono` → skopiować `files/ibm-plex-mono-latin-ext-400-normal.woff2` i `…-500-…` (latin-ext obejmuje polskie znaki) oraz `LICENSE`.
- [ ] **Step 2: Test** `test_v2_assets_served` — `/vendor/fonts/ibm-plex-mono-400.woff2` → 200; `style.css` zawiera `--forgot`, `backdrop-filter`, `prefers-reduced-transparency`, `IBM Plex Mono`.
- [ ] **Step 3:** pytest → FAIL. **Step 4:** napisać `style.css` (`@font-face` dla obu wag). **Step 5:** PASS, commit `feat: style v2 i czcionka kodu`.

---

### Task 5: Ekran Dziś (`index.html`) — F3, F7, talia

**Files:** Replace `static/index.html`; Modify `tests/test_static.py`

**Interfaces:** Consumes `GET /api/summary` (`due`, `total`, `last_session`), `/api/review/queue`, `/api/forecast`.

Zachowanie wg spec v2 §4 (F3, F7, talia, pusty stan). Filtr Wszystkie / Python / C# przeładowuje kolejkę i prognozę z `?language=`. Nagłówek: „N zadań czeka na powtórkę” (+ „ w Pythonie” / „ w C#”) z odmianą 1 / 2–4 / 5+. „Zacznij powtórkę” → `task.html?session=<all|python|csharp>`. Długie tytuły: `overflow-wrap: anywhere`.

- [ ] **Step 1: Test** `test_today_page_served` — `/` zawiera `Zacznij powtórkę`, `Najbliższe dwa tygodnie`, `theme-toggle`, `/vendor/fonts` nie jest wymagane w HTML (font ładowany z CSS).
- [ ] **Step 2:** FAIL. **Step 3:** napisać. **Step 4:** `pytest -q` PASS + scenariusz Chrome: baza z zestawem VARIABLES → nagłówek „10 zadań…”, talia pokazuje 3 karty, wykres 14 słupków, filtr C# → pusty stan „Na dziś wszystko powtórzone”, oba motywy.
- [ ] **Step 5:** Commit `feat: ekran Dziś v2`.

---

### Task 6: Biblioteka (`list.html`) — F4, F5

**Files:** Replace `static/list.html`; Modify `tests/test_static.py`

Grupy: „Do powtórki dziś” (`due_date <= dziś`), „W tym tygodniu” (1–7 dni), „Później”; puste grupy ukryte. Pasek utrwalenia wg progów spec v2 F4 (tekst + 5 kresek, `role="img"` z `aria-label`). Wyszukiwarka i filtr języka działają razem, bez zapytań do serwera (jedno `GET /api/tasks` na wejściu i po usunięciu). Usuń: `confirm(...)` jak w v1 → `DELETE` → odświeżenie. Pusta biblioteka: „Nie masz jeszcze zadań” + „Nowe zadanie”; pusty wynik wyszukiwania: komunikat z makiety.

- [ ] **Step 1: Test** `test_library_page_served` — `/list.html` zawiera `Biblioteka`, `Szukaj po tytule`.
- [ ] **Step 2–4:** FAIL → napisać → PASS + scenariusz: wpisanie „lis” zostawia „Odwróć listę”/„Niezależne listy”, filtr C# + fraza bez wyników → komunikat, usuwanie działa.
- [ ] **Step 5:** Commit `feat: Biblioteka v2`.

---

### Task 7: Nowe / edycja zadania (`form.html`) — F6

**Files:** Replace `static/form.html`; Modify `tests/test_static.py`

Zachowanie formularza v1 (walidacja 422 przy polach, pomijanie pustych testów, edycja `?id=`, „Sprawdź rozwiązanie” przez `/api/run`, Monaco w obu polach kodu) w układzie z makiety: sekcje Opis / Kod obok siebie, Testy pod spodem, pasek na dole (status + Anuluj + Sprawdź rozwiązanie + Zapisz zadanie). „Pisz / Podgląd” (F6) — `marked.parse` treści. Po sprawdzeniu: ✓ przy zaliczonych testach, przy niezaliczonych krótki opis (oczekiwano / otrzymano lub komunikat). Nagłówek „Edytuj zadanie” w trybie edycji.

- [ ] **Step 1: Test** `test_editor_page_served` — `/form.html` zawiera `Nowe zadanie`, `Podgląd`, `Sprawdź rozwiązanie`.
- [ ] **Step 2–4:** FAIL → napisać → PASS + scenariusz: puste zapisanie pokazuje błędy pól, podgląd Markdown, utworzenie zadania C# program, edycja wczytuje dane.
- [ ] **Step 5:** Commit `feat: edytor zadania v2`.

---

### Task 8: Sesja (`task.html`) — F1, F2, pasek sesji

**Files:** Replace `static/task.html`; Modify `tests/test_static.py`

**Interfaces:** Consumes `/api/review/due`, `/api/tasks/{id}` (`last_rating`, `last_reviewed_at`, `preview`), `/api/run`, `/api/tasks/{id}/review`, `/api/tasks/{id}/review/undo`.

Zachowanie v1 (kolejka, pomijanie 404, pojedyncze zadanie `?id=`, podpowiedź/rozwiązanie z flagami, reset kodu, wyniki testów) w układzie z makiety + pasek segmentów + „Ostatnio X dni temu, ocena: …” + dolny pasek ocen. F1: `Ctrl/⌘+Enter` przez `editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, …)` i `keydown` na `document`; `1/2/3` tylko gdy pasek ocen widoczny i `document.activeElement` nie jest `input`, `textarea` ani wewnątrz edytora. F2: „Cofnij ocenę” → `POST …/undo`; przycisk `disabled` od kliknięcia do odpowiedzi; sukces → pasek ocen wraca, segment szary, licznik ocenionych −1; 409 → komunikat z `detail`. Koniec sesji: karta „Koniec na dziś” z liczbą ocenionych i podsumowaniem kolorów.

- [ ] **Step 1: Test** `test_session_page_served` — `/task.html` zawiera `Jak dobrze pamiętałeś to zadanie?`, `Cofnij ocenę`, `Uruchom testy`.
- [ ] **Step 2–4:** FAIL → napisać → PASS + scenariusz Chrome: `Ctrl+Enter` w edytorze uruchamia testy; wpisanie „1” w edytorze nie ocenia; `2` poza edytorem ocenia „Częściowo” i barwi segment; „Cofnij ocenę” przywraca termin (sprawdzić przez API) i szary segment; podwójne kliknięcie cofa tylko raz; zadanie usunięte w trakcie sesji pominięte; długi tytuł nie rozpycha układu.
- [ ] **Step 5:** Commit `feat: sesja v2 ze skrótami i cofaniem oceny`.

---

### Task 9: README i weryfikacja końcowa

**Files:** Modify `README.md`

Dopisać: skróty klawiszowe, cofanie oceny, wykres, pasek utrwalenia (progi), informacja o automatycznej migracji bazy.

- [ ] **Step 1:** README. **Step 2:** `.venv/bin/pytest -q` → PASS. **Step 3:** pełny scenariusz na świeżej bazie + na kopii bazy w schemacie v1 (migracja). **Step 4:** Commit `docs: README v2`.
