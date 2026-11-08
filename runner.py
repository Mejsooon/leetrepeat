"""Uruchamianie kodu użytkownika i porównanie z testami (spec §4)."""
import json
import os
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
    else:
        raise ValueError(f"Nieznany język: {language}")

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    results = []

    # Normalizacja tekstu wyjścia: \r\n -> \n, bez spacji na końcach linii i pustych linii na końcu
    def normalize(text):
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, file_name)

        if kind == "function":
            # --- 2a. Harness: kod użytkownika + wywołanie każdego testu z prefiksem @@numer ---
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
            crash_message = "\n".join(proc.stderr.strip().splitlines()[-5:]) or "Program zakończył się błędem"

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
                result["message"] = "\n".join(proc.stderr.strip().splitlines()[-5:]) or "Program zakończył się błędem"
            elif result["actual"] == normalize(test["expected"]):
                result["status"] = "pass"
            else:
                result["status"] = "fail"
            results.append(result)
        return results
