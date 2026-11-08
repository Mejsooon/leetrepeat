from runner import run_tests

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
