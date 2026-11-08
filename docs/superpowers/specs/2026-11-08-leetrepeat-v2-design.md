# LeetRepeat v2 — nowy frontend i nowe funkcje

Data: 2026-11-08
Status: do akceptacji
Bazuje na: `2026-11-07-leetrepeat-design.md` (v1) — wszystko, czego ten dokument nie zmienia, zostaje jak w v1.
Wygląd: artefakt Design „LeetRepeat — makiety v2” (ekrany Dziś, Sesja, Biblioteka, Nowe zadanie) — przenieść 1:1.

## 1. Cel

Frontend gotowy do codziennego używania (styl z makiet v2) oraz 7 funkcji pokazanych na makietach:

| # | Funkcja | Gdzie |
|---|---|---|
| F1 | Skróty: `Ctrl/⌘ + Enter` uruchamia testy, `1` `2` `3` wybierają ocenę | Sesja |
| F2 | „Cofnij ocenę” po zapisaniu | Sesja |
| F3 | Wykres: ile zadań wraca w najbliższych 14 dniach | Dziś |
| F4 | Pasek utrwalenia (5 stopni) | Biblioteka |
| F5 | Wyszukiwarka po tytule | Biblioteka |
| F6 | Podgląd Markdown („Pisz / Podgląd”) | Nowe zadanie |
| F7 | „Ostatnia sesja była …, powtórzyłeś N zadań” | Dziś |

Plus elementy makiet wymagające danych: talia kart z kolejką na dziś (Dziś), pasek sesji kolorowany ocenami i „Ostatnio X dni temu, ocena: …” (Sesja).

## 2. Zmiany w bazie

`reviews` dostaje dwie kolumny — stan zadania **sprzed** oceny, potrzebny do cofnięcia (F2):

| Kolumna | Typ | Opis |
|---|---|---|
| prev_interval_days | REAL NULL | `interval_days` zadania przed tą oceną |
| prev_due_date | TEXT NULL | `due_date` zadania przed tą oceną |

Migracja w `core/database.py`: przy połączeniu, jeśli kolumny nie istnieją (`PRAGMA table_info(reviews)`), wykonać `ALTER TABLE reviews ADD COLUMN …`. Istniejące bazy użytkownika działają bez ręcznych kroków; stare oceny mają NULL i nie da się ich cofnąć.

## 3. Zmiany w API

| Metoda | Ścieżka | Zmiana |
|---|---|---|
| GET | `/api/tasks?language=` | każdy element dostaje `interval_days` (do paska utrwalenia F4) |
| GET | `/api/tasks/{id}` | dochodzi `last_rating` (`'again'│'partial'│'good'│null`) z najnowszej oceny |
| GET | `/api/review/queue?language=` | **nowy**: zadania do powtórki dziś, w kolejności jak `/review/due`: `[{id, title, language, kind, description, last_reviewed_at, last_rating}]` (talia na ekranie Dziś) |
| GET | `/api/forecast?language=` | **nowy** (F3): 14 elementów `[{date, count}]` od dziś do dziś+13; zaległe zadania (`due_date < dziś`) liczą się do dziś |
| GET | `/api/summary` | dochodzi `last_session: {date, count} │ null` — ostatni dzień z ocenami i liczba **różnych zadań** ocenionych tego dnia (F7) |
| POST | `/api/tasks/{id}/review` | zapisuje też `prev_interval_days`, `prev_due_date` |
| POST | `/api/tasks/{id}/review/undo` | **nowy** (F2): usuwa najnowszą ocenę zadania i przywraca `interval_days`/`due_date` z jej `prev_*`; odpowiedź `{interval_days, due_date}`. 404 gdy brak zadania, 409 `"Tej oceny nie da się cofnąć"` gdy brak ocen albo najnowsza ma `prev_*` = NULL |

`/api/review/due` zostaje (używa go sesja).

## 4. Frontend

- Pliki zostają: `index.html` (Dziś), `task.html` (Sesja / pojedyncze zadanie), `list.html` (Biblioteka), `form.html` (Nowe / Edytuj zadanie); nowy `style.css` z tokenami z makiet v2; `theme.js` bez zmian w działaniu (domyślnie motyw systemowy).
- Czcionki: interfejs — systemowa (`-apple-system, "Segoe UI Variable", "Segoe UI", system-ui`); kod — IBM Plex Mono zapisana lokalnie w `static/vendor/fonts/` (działa offline).
- Przezroczyste paski: nagłówek (wszystkie ekrany), pasek ocen (Sesja), pasek zapisu (Nowe zadanie); przy `prefers-reduced-transparency` pełne tło, przy `prefers-reduced-motion` bez animacji.

### Zachowanie funkcji

- **F1:** `Ctrl+Enter` (na Macu też `⌘+Enter`) działa także z kursorem w edytorze Monaco (`editor.addCommand`). `1/2/3` działają tylko, gdy pasek ocen jest widoczny i fokus **nie** jest w polu tekstowym ani w edytorze.
- **F2:** przycisk „Cofnij ocenę” widoczny po zapisaniu oceny, do przejścia do następnego zadania. Cofnięcie przywraca pasek ocen i szary segment w pasku sesji.
- **F3:** 14 słupków, dzisiejszy w kolorze akcentu; podpisy dni po polsku (`nd 8`, `pn 9`, …), dziś jako „dziś”. Respektuje filtr języka na ekranie Dziś.
- **F4:** stopień z `interval_days`: 0 → Nowe (0/5), <3 → Słabo (1), <7 → Uczysz się (2), <15 → Nieźle (3), <30 → Dobrze (4), ≥30 → Utrwalone (5).
- **F5:** filtrowanie w przeglądarce po fragmencie tytułu (bez wielkości liter), razem z filtrem języka; pusty wynik pokazuje komunikat i przycisk „Nowe zadanie”.
- **F6:** „Podgląd” renderuje treść tym samym `marked`, co ekran sesji.
- **F7:** „Ostatnia sesja była dziś / wczoraj / N dni temu, powtórzyłeś wtedy N zadań.”; gdy `last_session` = null: „To będzie Twoja pierwsza sesja.”
- **Talia (Dziś):** pierwsze 3 zadania z `/api/review/queue`; pod talią „Za nimi jeszcze N w kolejce”. Zero zadań → zamiast talii karta „Na dziś wszystko powtórzone” z datą najbliższej powtórki (z F3).
- **Pasek sesji:** jeden segment na zadanie w sesji; oceniony = kolor oceny, bieżący = obramowanie akcentu, pozostałe szare.

## 5. Testy

pytest dla wszystkich zmian w API i migracji: istniejąca baza v1 (bez kolumn `prev_*`) po połączeniu ma nowe kolumny; undo przywraca dokładnie poprzedni stan; undo bez ocen → 409; forecast liczy zaległe do dziś i ma 14 dni; `last_session` liczy różne zadania; `queue` zwraca `last_rating`. Frontend: test serwowania stron + scenariusz w przeglądarce (headless Chrome) dla F1–F7 w obu motywach.

## 6. Poza zakresem

Konta, wersja online, statystyki poza wykresem 14 dni, cofanie starszych ocen niż najnowsza.
