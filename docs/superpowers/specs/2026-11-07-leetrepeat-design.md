# LeetRepeat — specyfikacja projektu

Data: 2026-11-07
Status: zatwierdzony projekt, czeka na przegląd specyfikacji

## 1. Cel

Lokalna aplikacja webowa do ćwiczenia programowania metodą powtórek rozłożonych w czasie
(jak Anki/RemNote), połączona z rozwiązywaniem zadań z automatycznymi testami (jak LeetCode).

- Użytkownik (jedna osoba) sam tworzy zadania w języku **Python** lub **C#**.
- Rozwiązuje je w edytorze kodu, może uruchomić testy, podejrzeć podpowiedź lub pełne rozwiązanie.
- Po zadaniu ocenia się: **Nie pamiętam / Częściowo pamiętam / Dobrze pamiętam**,
  a aplikacja wyznacza datę następnej powtórki.

### Kryteria sukcesu

1. Można dodać zadanie (oba języki, oba typy) przez formularz i sprawdzić rozwiązanie wzorcowe na testach przed zapisem.
2. Ekran startowy pokazuje, ile zadań jest dziś do powtórki (wg języka) i pozwala rozpocząć sesję.
3. Testy uruchamiają się poprawnie dla Pythona i C#, dla typów `function` i `program`.
4. Ocena zmienia `due_date` zgodnie z tabelą harmonogramu (sekcja 5).
5. Aplikacja działa na Parrot OS i Windows, offline, uruchamiana jedną komendą.

### Decyzje użytkownika (z rozmowy)

| Temat | Decyzja |
|---|---|
| Kto buduje | Claude buduje narzędzie; użytkownik z niego korzysta |
| Przechowywanie | baza danych (nie pliki zadań) |
| Sprawdzanie kodu | automatyczne testy |
| Języki w v1 | Python i C# |
| Typy zadań | oba: `function` i `program`, wybierane przy tworzeniu |
| Gdzie działa | tylko lokalnie, 0 zł |
| Dodawanie zadań | formularz w aplikacji |
| Wpływ testów/podglądu na ocenę | brak — użytkownik zawsze sam wybiera ocenę |
| Stos technologiczny | FastAPI + SQLite + czysty HTML/CSS/JS |

## 2. Architektura

```
Przeglądarka (HTML/CSS/JS, Monaco, marked)
        │ HTTP, 127.0.0.1
FastAPI (main.py)
  ├─ db.py        — SQLite przez sqlite3 (bez ORM)
  ├─ runner.py    — uruchamianie kodu przez subprocess: python / dotnet
  └─ scheduler.py — obliczanie następnej powtórki
        │
  leetrepeat.db (plik SQLite)
```

- Serwer nasłuchuje wyłącznie na `127.0.0.1` (port domyślny 8000).
- Frontend to pliki statyczne serwowane przez FastAPI; brak frameworka i kroku budowania.
- Monaco Editor i marked są zapisane w `static/vendor/` — aplikacja działa offline.
- Styl kodu: prosty, liniowy, bez rozbijania logiki na wiele małych funkcji pomocniczych.

### Struktura projektu

```
leetrepeat/
├── main.py
├── db.py
├── runner.py
├── scheduler.py
├── static/
│   ├── index.html, task.html, list.html, form.html
│   ├── style.css, *.js
│   └── vendor/        (monaco, marked)
├── tests/
├── requirements.txt
└── README.md          (instalacja: Python, zależności, .NET 10 SDK — Parrot i Windows)
```

Plik bazy `leetrepeat.db` tworzy się automatycznie przy pierwszym starcie i jest w `.gitignore`.

## 3. Model danych

### `tasks`

| Kolumna | Typ | Opis |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| language | TEXT NOT NULL | `'python'` lub `'csharp'` |
| kind | TEXT NOT NULL | `'function'` lub `'program'` |
| description | TEXT NOT NULL | treść w Markdown |
| starter_code | TEXT NOT NULL DEFAULT '' | kod wstawiany do edytora na start |
| hint | TEXT NOT NULL DEFAULT '' | |
| solution | TEXT NOT NULL | pełne rozwiązanie |
| created_at | TEXT NOT NULL | ISO datetime |
| interval_days | REAL NOT NULL DEFAULT 0 | 0 = zadanie nigdy nieocenione |
| due_date | TEXT NOT NULL | ISO date; dla nowego zadania = dzień utworzenia |

### `tests`

| Kolumna | Typ | Opis |
|---|---|---|
| id | INTEGER PK | |
| task_id | INTEGER FK → tasks ON DELETE CASCADE | |
| position | INTEGER NOT NULL | kolejność wyświetlania |
| input | TEXT NOT NULL | `function`: wyrażenie wywołania; `program`: tekst na stdin |
| expected | TEXT NOT NULL | `function`: JSON; `program`: oczekiwany stdout |

Przykłady:

| Język / typ | input | expected |
|---|---|---|
| python / function | `odwroc([1,2,3])` | `[3,2,1]` |
| csharp / function | `Odwroc(new[]{1,2,3})` | `[3,2,1]` |
| dowolny / program | `4` | `8` |

### `reviews` (historia)

| Kolumna | Typ | Opis |
|---|---|---|
| id | INTEGER PK | |
| task_id | INTEGER FK → tasks ON DELETE CASCADE | |
| rating | TEXT NOT NULL | `'again'`, `'partial'`, `'good'` |
| reviewed_at | TEXT NOT NULL | ISO datetime |
| tests_passed | INTEGER NULL | liczba zaliczonych testów w ostatnim uruchomieniu; NULL gdy nie uruchomiono |
| tests_total | INTEGER NULL | liczba testów w ostatnim uruchomieniu; NULL gdy nie uruchomiono |
| hint_used | INTEGER NOT NULL | 0/1 |
| solution_used | INTEGER NOT NULL | 0/1 |

Historia nie wpływa na harmonogram w v1; służy przyszłym statystykom.
Zadanie musi mieć co najmniej jeden test.

## 4. Uruchamianie kodu (`runner.py`)

Wejście: `language`, `kind`, `code`, lista testów `{input, expected}`.
Wyjście: lista wyników, po jednym na test: `status` (`pass` | `fail` | `error` | `timeout`),
`expected`, `actual`, `message`.

### Przebieg

1. Utwórz katalog tymczasowy (`tempfile.TemporaryDirectory`), usuwany po zakończeniu.
2. Zbuduj plik do uruchomienia (harness) wg tabeli poniżej.
3. Uruchom przez `subprocess.run` z limitem czasu; przechwyć stdout i stderr.
4. Porównaj wyniki i zwróć listę.

### Harness

| | `function` | `program` |
|---|---|---|
| Python (`main.py`) | kod użytkownika, a pod nim dla każdego testu `i`: wywołanie w `try`, wypisanie linii `@@i OK <json>` albo `@@i ERR <komunikat>`; serializacja `json.dumps(wynik, separators=(",", ":"))` | kod użytkownika bez zmian; jeden proces na test, `input` na stdin |
| C# (`main.cs`, `dotnet run main.cs`) | na górze `using System.Text.Json;`, potem instrukcje najwyższego poziomu: dla każdego testu `try { Console.WriteLine("@@i OK " + JsonSerializer.Serialize(<input>)); } catch (Exception e) { Console.WriteLine("@@i ERR " + e.Message); }`, pod nimi kod użytkownika (metody `static` jako funkcje lokalne lub klasy) | kod użytkownika bez zmian; `dotnet run main.cs` raz na test z `input` na stdin — pierwsze uruchomienie kompiluje, kolejne korzystają z pamięci podręcznej kompilacji .NET |

Dla `function` wszystkie testy idą w jednym procesie. Linie stdout bez prefiksu `@@` są ignorowane
przy porównaniu (użytkownik może debugować przez `print`).

### Porównanie

- `function`: `expected` i otrzymany tekst parsowane przez `json.loads` i porównywane jako obiekty
  Pythona. Jeśli `expected` nie jest poprawnym JSON-em → status `error` z komunikatem o złym teście.
- `program`: oba teksty normalizowane: `\r\n` → `\n`, usunięcie spacji na końcu każdej linii
  i pustych linii na końcu; porównanie dokładne.

### Statusy

| Status | Kiedy | Co pokazuje UI |
|---|---|---|
| `pass` | wynik zgodny | ✅ |
| `fail` | wynik niezgodny | ❌ oczekiwano / otrzymano |
| `error` | wyjątek, błąd składni/kompilacji, niezerowy kod wyjścia, brak linii `@@i` | 💥 komunikat (stderr / komunikat wyjątku) |
| `timeout` | przekroczony limit | ⏱️ |

Błąd kompilacji C# lub błąd składni Pythona oznacza status `error` dla wszystkich testów z tym samym komunikatem.

### Limity czasu

- Python: 5 s na proces.
- C#: 20 s na każde `dotnet run` (obejmuje ewentualną kompilację).
- Po przekroczeniu proces jest zabijany.

### Brak środowiska

Jeśli `python` (użyty zostanie `sys.executable`) lub `dotnet` nie jest dostępny (`shutil.which`),
endpoint `/api/run` zwraca HTTP 400 z komunikatem, np.
„Nie znaleziono dotnet — zainstaluj .NET 10 SDK (instrukcja w README)”.

### Bezpieczeństwo

Brak sandboxa (kod użytkownika na jego komputerze). Ochrona: nasłuch tylko na `127.0.0.1`,
limit czasu, katalog tymczasowy.

## 5. Harmonogram (`scheduler.py`)

Wejście: `interval_days`, `rating`, dzisiejsza data. Wyjście: nowe `interval_days`, nowa `due_date`.

| Ocena | Nowe zadanie (`interval_days == 0`) | Pozostałe |
|---|---|---|
| `again` (Nie pamiętam) | 1 | 1 |
| `partial` (Częściowo) | 1 | `max(interval × 1.2, interval + 1)` |
| `good` (Dobrze) | 3 | `interval × 2.5` |

`due_date = dziś + round(nowy interval)` dni. `interval_days` przechowywany bez zaokrąglenia.
Ocena zawsze aktualizuje harmonogram, także gdy zadanie otwarto przed terminem.
UI pokazuje pod każdym przyciskiem przewidywany odstęp — `GET /api/tasks/{id}` zwraca go jako pole
`preview: {again, partial, good}` (dni), liczone tą samą funkcją co przy zapisie oceny.

## 6. API

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/api/tasks?language=` | lista zadań (bez testów), sortowana po `due_date` |
| GET | `/api/tasks/{id}` | zadanie z testami i `preview` odstępów dla trzech ocen |
| POST | `/api/tasks` | utworzenie zadania z testami |
| PUT | `/api/tasks/{id}` | edycja zadania; testy zastępowane w całości; harmonogram bez zmian |
| DELETE | `/api/tasks/{id}` | usunięcie (kaskadowo testy i historia) |
| GET | `/api/review/due?language=` | id zadań z `due_date <= dziś`, najstarsze pierwsze |
| GET | `/api/summary` | `{python: n, csharp: n}` — liczba zadań do powtórki dziś |
| POST | `/api/run` | `{language, kind, code, tests}` → lista wyników |
| POST | `/api/tasks/{id}/review` | `{rating, tests_passed, tests_total, hint_used, solution_used}` → `{interval_days, due_date}` |

Walidacja przez modele Pydantic; błędy → HTTP 422 z nazwą pola. Nieistniejące id → 404.

## 7. Ekrany

1. **Start (`/`)** — liczba zadań do powtórki dziś wg języka; przycisk „Zacznij powtórkę”
   (wszystkie lub wybrany język); linki „Dodaj zadanie” i „Wszystkie zadania”.
2. **Zadanie (`/task.html?id=…` lub sesja `?session=python|csharp|all`)** — po lewej treść
   (Markdown), przyciski „Podpowiedź” i „Rozwiązanie” (rozwijane); po prawej edytor Monaco
   z kodem startowym, „Uruchom testy”, lista wyników; na dole trzy przyciski oceny z przewidywanym
   odstępem. W sesji po ocenie przejście do kolejnego zadania; na końcu „Koniec na dziś”.
   Pasek u góry: tytuł, język, typ, licznik `n / m` w sesji.
3. **Lista (`/list.html`)** — tabela: tytuł, język, typ, następna powtórka; filtr języka;
   „Otwórz”, „Edytuj”, „Usuń” (z potwierdzeniem).
4. **Formularz (`/form.html`, `?id=` dla edycji)** — tytuł, język, typ, treść, kod startowy (Monaco),
   podpowiedź, rozwiązanie (Monaco), lista testów (dodaj/usuń), „Sprawdź rozwiązanie na testach”
   (uruchamia rozwiązanie wzorcowe przez `/api/run`), „Zapisz”. Zapis możliwy także przy
   niezaliczonych testach (użytkownik decyduje), ale wyniki są widoczne.

Interfejs w języku polskim.

**Tryb jasny i ciemny:** przycisk ze słońcem/księżycem w nagłówku każdego ekranu przełącza motyw.
Kolory zdefiniowane jako zmienne CSS w dwóch zestawach (`.lr-dark`, `.lr-light`) na elemencie głównym.
Wybór zapisywany w `localStorage` przeglądarki (klucz `leetrepeat-theme`); domyślnie motyw systemowy
(`prefers-color-scheme`), a gdy niedostępny — ciemny. Edytor Monaco przełącza się odpowiednio
między motywami `vs-dark` i `vs`.

Makiety ekranów: artefakt Design „LeetRepeat — makiety ekranów”.

## 8. Testy

pytest + `fastapi.testclient`:

- `scheduler`: każdy wiersz tabeli z sekcji 5, w tym przypadek `partial` przy małym odstępie.
- `runner`: Python i C#, `function` i `program`; przypadki pass, fail, error (wyjątek, błąd składni/
  kompilacji), timeout; normalizacja białych znaków; JSON z różnymi odstępami. Testy C# oznaczone
  `skipif(shutil.which("dotnet") is None)`.
- API: CRUD zadań, `/review/due`, `/summary`, zapis oceny zmieniający `due_date`, 404/422;
  każdy test na tymczasowym pliku bazy.

Frontend: weryfikacja ręczna (scenariusz: dodaj zadanie Python i C#, rozwiąż, oceń, sprawdź datę).

## 9. Poza zakresem v1

Konta użytkowników, wersja online, import/eksport z pliku, ekran statystyk, języki inne niż Python
i C#, sandbox wykonania kodu, wpływ testów/podglądu na ocenę.
