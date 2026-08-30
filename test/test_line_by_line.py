"""`@profiler_lbl` drives `sys.settrace`, so every case needs a fresh interpreter."""

import pytest

pytestmark = pytest.mark.slow

SIMPLE = """
    import time
    from custom_profiler import profiler_lbl
    from custom_profiler import profiler_collecteur as pc

    @profiler_lbl
    def my_func():
        a = [1] * (10 ** 5)
        b = [2] * (10 ** 6)
        time.sleep(0.01)
        del b
        return a

    my_func()
    print("KEYS", "|".join(pc.profData.keys()))
"""


def _keys(out):
    line = next(l for l in out.splitlines() if l.startswith("KEYS"))
    return [k.strip() for k in line[len("KEYS "):].split("|")]


def test_every_line_is_reported(run_py):
    out = run_py(SIMPLE)
    assert "line per line : my_func from" in out
    assert "line per line : end" in out
    for src in ["a = [1] * (10 ** 5)", "b = [2] * (10 ** 6)",
                "time.sleep(0.01)", "del b", "return a"]:
        assert src in out, src


def test_lines_are_registered_under_their_source_number(run_py):
    out = run_py(SIMPLE)
    # the function body starts at line 7 of the generated snippet
    assert _keys(out) == [
        "my_func l 7", "my_func l 8", "my_func l 9",
        "my_func l 10", "my_func l 11", "my_func",
    ]


def test_the_function_itself_is_still_profiled(run_py):
    out = run_py(SIMPLE)
    assert _keys(out)[-1] == "my_func"


def test_no_peak_column_in_line_mode(run_py):
    """`profiler_lbl` starts no watcher thread, so the peak column must stay off."""
    out = run_py(SIMPLE)
    reported = [l for l in out.splitlines() if "| takes :" in l]
    assert reported
    assert all("consumes :  Δ" in l for l in reported)
    assert not any("peak" in l for l in reported)


def test_freed_memory_is_shown_as_a_negative_delta(run_py):
    out = run_py(SIMPLE)
    del_line = next(l for l in out.splitlines() if "del b" in l)
    assert "Δ   -" in del_line or "Δ  -" in del_line


def test_return_value_is_preserved(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl

        @profiler_lbl
        def my_func(x):
            y = x + 1
            return y * 2

        print("RESULT", my_func(20))
        """
    )
    assert "RESULT 42" in out


@pytest.mark.xfail(strict=True, reason=(
    "known bug: line labels are taken from the *next* trace event minus one, so "
    "a comment or blank line inside the body shifts every following number"
))
def test_line_numbers_survive_a_comment_in_the_body(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = 1
            # a comment
            b = 2
            return a + b

        my_func()
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    assert _keys(out) == ["my_func l 6", "my_func l 8", "my_func l 9", "my_func"]


@pytest.mark.xfail(strict=True, reason=(
    "known bug: CPython >=3.10 emits a single line event for a parenthesised "
    "multi-line statement, so __paren_count never returns to 0 and every "
    "remaining line of the function is swallowed"
))
def test_multiline_statement_does_not_swallow_the_rest(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = 1
            b = (2 +
                 3 +
                 4)
            c = 5
            return a + b + c

        my_func()
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    keys = _keys(out)
    assert "my_func l 10" in keys      # c = 5
    assert "my_func l 11" in keys      # return
