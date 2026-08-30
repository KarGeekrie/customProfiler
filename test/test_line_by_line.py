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


def test_multiline_statement_is_reported_once(run_py):
    """The continuation lines are read from the source, not waited for."""
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
    assert keys == ["my_func l 6", "my_func l 7", "my_func l 10",
                    "my_func l 11", "my_func"]
    assert "b = (2 + 3 + 4)" in out


def test_backslash_continuation_is_marked(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = 1 + \\
                2 + \\
                3
            return a

        my_func()
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    assert "a = 1 + [...]" in out
    assert _keys(out) == ["my_func l 6", "my_func l 9", "my_func"]


def test_brackets_inside_a_string_do_not_extend_the_statement(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = "("          # not a real bracket
            b = 2
            return b

        my_func()
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    assert _keys(out) == ["my_func l 6", "my_func l 7", "my_func l 8", "my_func"]


def test_nested_python_calls_are_not_traced(run_py):
    """Only the decorated function is followed line by line."""
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        def helper():
            x = 1
            return x

        @profiler_lbl
        def my_func():
            a = helper()
            return a

        my_func()
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    assert _keys(out) == ["my_func l 10", "my_func l 11", "my_func"]
    assert "helper l" not in out


def test_a_looping_line_is_counted_once_per_pass(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            total = 0
            for i in range(3):
                total += i
            return total

        my_func()
        print("NBCALL", pc["my_func l 8  "]["nb_call"])
        """
    )
    assert "NBCALL 3" in out


def test_the_last_line_is_saved_when_the_function_raises(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = 1
            raise ValueError("boom")

        try:
            my_func()
        except ValueError:
            pass
        print("KEYS", "|".join(pc.profData.keys()))
        """
    )
    assert "line per line : end" in out
    assert _keys(out) == ["my_func l 6", "my_func l 7", "my_func"]


@pytest.mark.xfail(strict=True, reason=(
    "known bug (not in the fixed batch, fixing it would change the documented "
    "summary markers): every per-line save() decrements profC.deep without a "
    "matching incr(), so deep[0] ends far below its baseline"
))
def test_line_mode_leaves_the_depth_counter_alone(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def my_func():
            a = 1
            b = 2
            return a + b

        my_func()
        print("DEEP", pc.deep[0])
        """
    )
    assert "DEEP -1" in out
