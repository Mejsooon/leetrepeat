import shutil

import pytest

import runner
from runner import RuntimeMissing, run_tests

needs_dotnet = pytest.mark.skipif(shutil.which("dotnet") is None, reason="brak dotnet")

REV = "static int[] Odwroc(int[] a) { var r = (int[])a.Clone(); Array.Reverse(r); return r; }"


@needs_dotnet
def test_function_pass():
    r = run_tests("csharp", "function", REV, [{"input": "Odwroc(new[]{1,2,3})", "expected": "[3,2,1]"}])
    assert r[0]["status"] == "pass"


@needs_dotnet
def test_function_fail():
    r = run_tests("csharp", "function", REV, [{"input": "Odwroc(new[]{1,2})", "expected": "[1,2]"}])
    assert r[0]["status"] == "fail" and r[0]["actual"] == "[2,1]"


@needs_dotnet
def test_function_static_class_and_using():
    code = "using System.Linq;\nstatic class S { public static int Suma(int[] a) => a.Sum(); }"
    r = run_tests("csharp", "function", code, [{"input": "S.Suma(new[]{1,2,3})", "expected": "6"}])
    assert r[0]["status"] == "pass"


@needs_dotnet
def test_function_exception():
    code = "static int Dziel(int a, int b) => a / b;"
    r = run_tests("csharp", "function", code, [{"input": "Dziel(1, 0)", "expected": "0"}])
    assert r[0]["status"] == "error" and "DivideByZeroException" in r[0]["message"]


@needs_dotnet
def test_compile_error_all_error():
    r = run_tests("csharp", "function", "static int X( { }", [{"input": "X()", "expected": "1"}] * 2)
    assert [t["status"] for t in r] == ["error", "error"] and "CS" in r[0]["message"]


@needs_dotnet
def test_program_pass_polish():                      # Review Focus 1
    code = "var x = Console.ReadLine();\nConsole.WriteLine(x + \" gęś\");"
    r = run_tests("csharp", "program", code, [{"input": "zażółć", "expected": "zażółć gęś"}])
    assert r[0]["status"] == "pass"


@needs_dotnet
def test_program_two_tests():
    code = "int x = int.Parse(Console.ReadLine());\nConsole.WriteLine(x * 2);"
    r = run_tests("csharp", "program", code, [{"input": "4", "expected": "8"}, {"input": "5", "expected": "11"}])
    assert [t["status"] for t in r] == ["pass", "fail"]


def test_missing_dotnet_raises(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeMissing):
        run_tests("csharp", "program", "", [{"input": "", "expected": ""}])
