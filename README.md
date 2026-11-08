# LeetRepeat

Twoje własne „LeetCode + Anki”: tworzysz zadania programistyczne w **Pythonie** i **C#**, rozwiązujesz je
w edytorze z automatycznymi testami, a po każdym zadaniu oceniasz, jak dobrze pamiętałeś — aplikacja
sama ustala, kiedy wrócić do zadania.

Działa lokalnie na Twoim komputerze (`http://127.0.0.1:8000`), bez internetu i bez kont.

## Wymagania

| Co | Po co |
|---|---|
| Python 3.11+ | serwer aplikacji i uruchamianie zadań w Pythonie |
| .NET 10 SDK | uruchamianie zadań w C# (bez niego działa tylko Python) |

## Instalacja — Parrot OS / Linux

```bash
git clone https://github.com/Mejsooon/leetrepeat
cd leetrepeat
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

.NET 10 SDK — oficjalnym skryptem instalacyjnym Microsoftu:

```bash
wget https://dot.net/v1/dotnet-install.sh
bash dotnet-install.sh --channel 10.0
echo 'export DOTNET_ROOT=$HOME/.dotnet' >> ~/.bashrc
echo 'export PATH=$PATH:$HOME/.dotnet' >> ~/.bashrc
source ~/.bashrc
dotnet --version        # powinno pokazać 10.x
```

## Instalacja — Windows (PowerShell)

```powershell
git clone https://github.com/Mejsooon/leetrepeat
cd leetrepeat
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
winget install Microsoft.DotNet.SDK.10
dotnet --version        # w NOWYM oknie PowerShell; powinno pokazać 10.x
```

> Jeśli PowerShell blokuje `Activate.ps1`, uruchom raz:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Uruchomienie

```bash
python main.py
```

Otwórz w przeglądarce **http://127.0.0.1:8000**. Serwer zatrzymujesz przez `Ctrl+C`.

Serwer nasłuchuje tylko na `127.0.0.1` i przyjmuje wyłącznie adresy `127.0.0.1` / `localhost` — ani nikt z sieci
lokalnej, ani obca strona internetowa nie może wysłać Ci kodu do wykonania. Otwieraj aplikację pod jednym z tych
dwóch adresów.

## Dane i kopia zapasowa

Wszystkie zadania, testy i historia ocen są w jednym pliku **`leetrepeat.db`** obok `main.py`.
Kopia zapasowa = skopiuj ten plik. Po aktualizacji aplikacji baza sama dostaje nowe kolumny przy pierwszym
uruchomieniu — nic nie trzeba robić ręcznie (ocen sprzed aktualizacji nie da się cofnąć). Inna lokalizacja bazy: zmienna `LEETREPEAT_DB`, np.
`LEETREPEAT_DB=~/zadania.db python main.py`.

## Jak pisać zadania

Typ zadania wybierasz w formularzu:

**function** — testy wywołują Twoją funkcję, a wynik porównywany jest jako JSON (`[3, 2, 1]` = `[3,2,1]`).

| Język | Rozwiązanie | Test: wywołanie | Test: oczekiwany wynik |
|---|---|---|---|
| Python | `def odwroc(lista):`<br>`    return lista[::-1]` | `odwroc([1, 2, 3])` | `[3,2,1]` |
| C# | `static int[] Odwroc(int[] a)`<br>`{ Array.Reverse(a); return a; }` | `Odwroc(new[]{1,2,3})` | `[3,2,1]` |

W C# możesz też napisać klasę: `static class S { public static int Suma(int[] a) => a.Sum(); }`
i w teście wywołać `S.Suma(new[]{1,2,3})`. Linie `using ...;` możesz pisać na górze kodu jak zwykle.

**program** — test podaje tekst na wejście (`input()` / `Console.ReadLine()`) i porównuje to, co
program wypisze (bez spacji i pustych linii na końcu).

| Język | Rozwiązanie | Test: wejście | Test: wyjście |
|---|---|---|---|
| Python | `x = int(input())`<br>`print(x * 2)` | `4` | `8` |
| C# | `int x = int.Parse(Console.ReadLine());`<br>`Console.WriteLine(x * 2);` | `4` | `8` |

Przed zapisem kliknij **„Sprawdź rozwiązanie na testach”** — wyłapiesz literówki w testach.

`print()` do debugowania w zadaniach typu function nie psuje testów — liczy się tylko zwrócony wynik.

## Gotowe zestawy zadań

W folderze `seeds/` są gotowe zadania w plikach JSON. Import do Twojej bazy (serwer może być wyłączony):

```bash
python seeds/import_tasks.py seeds/python_variables.json
```

| Plik | Zawartość |
|---|---|
| `python_variables.json` | 10 zadań z notatki PYTHON — VARIABLES: typy, `isinstance`, konwersje, swap, mutowalność, kopie, `is` vs `==`, nazwy zmiennych |

Zadania, które już są w bazie (ten sam tytuł i język), są pomijane — import można powtarzać.

## Skróty klawiszowe (sesja powtórki)

| Skrót | Działanie |
|---|---|
| `Ctrl + Enter` (Mac: `⌘ + Enter`) | uruchom testy — działa też z kursorem w edytorze |
| `1` / `2` / `3` | ocena: Nie pamiętam / Częściowo / Dobrze pamiętam (gdy nie piszesz w edytorze ani w polu tekstowym) |

Po ocenie możesz kliknąć **Cofnij ocenę** — zadanie wraca do stanu sprzed oceny (działa dla najnowszej oceny zadania).

## Ekrany

- **Dziś** — ile zadań czeka, kolejka (pierwsze 3 zadania), wykres powtórek na 14 dni, informacja o ostatniej sesji.
- **Sesja** — pasek u góry ma po jednym segmencie na zadanie, w kolorze Twojej oceny.
- **Biblioteka** — zadania pogrupowane według terminu, wyszukiwarka, pasek utrwalenia:

| Odstęp powtórek | Utrwalenie |
|---|---|
| nowe zadanie | Nowe |
| < 3 dni | Słabo |
| < 7 dni | Uczysz się |
| < 15 dni | Nieźle |
| < 30 dni | Dobrze |
| 30+ dni | Utrwalone |

- **Nowe zadanie** — przełącznik „Pisz / Podgląd” pokazuje treść tak, jak zobaczysz ją w sesji.

## Powtórki

| Ocena | Nowe zadanie | Kolejne powtórki |
|---|---|---|
| Nie pamiętam | jutro | jutro |
| Częściowo | jutro | odstęp × 1,2 (co najmniej +1 dzień) |
| Dobrze pamiętam | za 3 dni | odstęp × 2,5 |

## Limity

- Python: 5 s na uruchomienie, C#: 20 s (pierwsza kompilacja C# trwa kilka sekund).
- Zadania C# nie mogą używać zewnętrznych paczek NuGet (kompilacja działa offline).

## Struktura projektu

```
leetrepeat/
├── main.py               # start aplikacji: tworzy FastAPI, podpina API i frontend
├── api/
│   ├── routes.py         # endpointy HTTP: przyjmują dane, wołają serwis, zwracają odpowiedź
│   └── schemas.py        # jak wyglądają dane z frontendu (walidacja Pydantic)
├── services/
│   ├── tasks.py          # logika zadań: "dziś", nowy termin po ocenie, podsumowanie
│   ├── scheduler.py      # wzory powtórek (Nie pamiętam / Częściowo / Dobrze)
│   └── runner.py         # uruchamianie kodu Python/C# i porównanie z testami
├── repository/
│   └── tasks.py          # cały SQL: odczyt i zapis zadań, testów, ocen
├── core/
│   └── database.py       # połączenie z SQLite i tworzenie tabel
├── static/               # frontend: HTML, CSS, JS (+ Monaco w vendor/)
├── seeds/                # gotowe zestawy zadań + skrypt importu
└── tests/                # testy pytest
```

Przepływ jednego żądania, np. ocena zadania:

```
przeglądarka → api/routes.py → services/tasks.py → repository/tasks.py → core/database.py → leetrepeat.db
                 (HTTP, 404)     (nowy termin)       (UPDATE + INSERT)    (połączenie)
```

Gdy dodajesz nową funkcję: SQL do `repository/`, obliczenia i decyzje do `services/`, nowy adres URL do `api/routes.py`.

## Testy aplikacji

```bash
pytest
```

Testy C# są pomijane, jeśli `dotnet` nie jest zainstalowany.
