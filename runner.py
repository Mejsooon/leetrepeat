"""Uruchamianie kodu użytkownika i porównanie z testami (spec §4)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


class RuntimeMissing(Exception):
    """Brak interpretera / SDK na komputerze — komunikat po polsku dla użytkownika."""


def run_tests(language: str, kind: str, code: str, tests: list[dict]) -> list[dict]:
    # --- 1. Jaki program uruchamia kod i z jakim limitem czasu ---
    if language == "python":
        if not sys.executable:
            raise RuntimeMissing("Nie znaleziono Pythona")
        file_name = "main.py"
        command = [sys.executable, file_name]
        time_limit = 5
    elif language == "csharp":
        if shutil.which("dotnet") is None:
            raise RuntimeMissing("Nie znaleziono dotnet — zainstaluj .NET 10 SDK (instrukcja w README)")
        file_name = "main.cs"
        command = ["dotnet", "run", file_name]
        time_limit = 20                             # obejmuje kompilację
    else:
        raise ValueError(f"Nieznany język: {language}")

    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
           "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
    results = []

    # Normalizacja tekstu wyjścia: \r\n -> \n, bez spacji na końcach linii i pustych linii na końcu
    def normalize(text):
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)

    # Treść błędu procesu: dla C# linie "error CS..." (błędy kompilacji), inaczej końcówka stderr
    def error_text(proc):
        output = proc.stdout + "\n" + proc.stderr
        compile_errors = [line.strip() for line in output.splitlines() if "error CS" in line]
        if compile_errors:
            return "\n".join(dict.fromkeys(compile_errors))   # bez powtórzeń
        return "\n".join(proc.stderr.strip().splitlines()[-5:]) or "Program zakończył się błędem"

    # C#: linie "using X;" muszą być na samej górze pliku, więc wyciągamy je z kodu użytkownika
    usings = ""
    if language == "csharp":
        code_lines = code.splitlines()
        usings = "\n".join(line for line in code_lines if re.match(r"^\s*using\s+[\w.]+\s*;", line))
        code = "\n".join(line for line in code_lines if not re.match(r"^\s*using\s+[\w.]+\s*;", line))
        # PublishAot=false: zwykła kompilacja (z AOT nie działa JsonSerializer i potrzebne są paczki NuGet)
        # Nullable=disable + WarningLevel=0: ostrzeżenia kompilatora nie trafiają do wyjścia programu
        csharp_header = ("#:property PublishAot=false\n#:property Nullable=disable\n#:property WarningLevel=0\n"
                         + usings + "\n")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, file_name)
        if language == "csharp":
            # Pusta lista źródeł NuGet: kompilacja działa offline, bez łączenia się z nuget.org
            with open(os.path.join(tmp, "nuget.config"), "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                        "<configuration><packageSources><clear /></packageSources></configuration>\n")

        if kind == "function":
            # --- 2a. Harness: kod użytkownika + wywołanie każdego testu z prefiksem @@numer ---
            if language == "csharp":
                source = (csharp_header + "using System.Text.Json;\n"
                          "Console.OutputEncoding = System.Text.Encoding.UTF8;\n")
                for i, test in enumerate(tests):
                    source += (
                        f'try {{ Console.WriteLine("@@{i} OK " + JsonSerializer.Serialize({test['input']})); }}\n'
                        f'catch (Exception __e) {{ Console.WriteLine("@@{i} ERR " + __e.GetType().Name + ": " + __e.Message); }}\n'
                    )
                source += code + "\n"
            else:
                source = code + "\n\nimport json as __json\n"
                for i, test in enumerate(tests):
                    source += (
                        "try:\n"
                        f"    __r = {test['input']}\n"
                        f"    print('@@{i} OK ' + __json.dumps(__r, separators=(',', ':'), ensure_ascii=False))\n"
                        "except Exception as __e:\n"
                        f"    print('@@{i} ERR ' + type(__e).__name__ + ': ' + str(__e))\n"
                    )
            with open(path, "w", encoding="utf-8") as f:
                f.write(source)

            # --- 3a. Jeden proces na wszystkie testy ---
            try:
                proc = subprocess.run(command, cwd=tmp, input="", capture_output=True,
                                      text=True, encoding="utf-8", timeout=time_limit, env=env)
            except subprocess.TimeoutExpired:
                for test in tests:
                    results.append({"status": "timeout", "input": test["input"], "expected": test["expected"],
                                    "actual": None, "message": f"Przekroczono limit czasu ({time_limit} s)"})
                return results

            # Zbieramy linie "@@i OK <json>" / "@@i ERR <komunikat>"; reszta stdout (debug print) jest ignorowana
            answers = {}
            for line in proc.stdout.splitlines():
                if not line.startswith("@@"):
                    continue
                number, status, rest = (line[2:].split(" ", 2) + ["", ""])[:3]
                answers[number] = (status, rest)
            crash_message = error_text(proc)

            # --- 4a. Porównanie każdego testu ---
            for i, test in enumerate(tests):
                result = {"status": "error", "input": test["input"], "expected": test["expected"],
                          "actual": None, "message": None}
                if str(i) not in answers:
                    result["message"] = crash_message
                else:
                    status, rest = answers[str(i)]
                    if status == "ERR":
                        result["message"] = rest
                    else:
                        result["actual"] = rest
                        try:
                            expected_value = json.loads(test["expected"])
                        except json.JSONDecodeError:
                            result["message"] = "Niepoprawny JSON w polu expected"
                            results.append(result)
                            continue
                        result["status"] = "pass" if json.loads(rest) == expected_value else "fail"
                results.append(result)
            return results

        # --- 2b. Program: kod bez zmian, osobny proces na każdy test, input na stdin ---
        with open(path, "w", encoding="utf-8") as f:
            if language == "csharp":
                f.write(csharp_header + "Console.OutputEncoding = System.Text.Encoding.UTF8;\n"
                        "Console.InputEncoding = System.Text.Encoding.UTF8;\n" + code + "\n")
            else:
                f.write(code)
        for test in tests:
            result = {"status": "error", "input": test["input"], "expected": test["expected"],
                      "actual": None, "message": None}
            try:
                proc = subprocess.run(command, cwd=tmp, input=test["input"], capture_output=True,
                                      text=True, encoding="utf-8", timeout=time_limit, env=env)
            except subprocess.TimeoutExpired:
                result["status"] = "timeout"
                result["message"] = f"Przekroczono limit czasu ({time_limit} s)"
                results.append(result)
                continue
            result["actual"] = normalize(proc.stdout)
            if proc.returncode != 0:
                result["message"] = error_text(proc)
            elif result["actual"] == normalize(test["expected"]):
                result["status"] = "pass"
            else:
                result["status"] = "fail"
            results.append(result)
        return results
