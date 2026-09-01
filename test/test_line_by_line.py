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


def test_every_reported_line_carries_a_memory_delta(run_py):
    """Not whether the delta is negative: whether `del` hands pages back to the
    OS is the allocator's business, and on macOS it does not. The sign rendering
    is covered by test_bytes2human."""
    out = run_py(SIMPLE)
    del_line = next(l for l in out.splitlines() if "del b" in l)
    assert "consumes :  Δ" in del_line
    assert "takes :" in del_line


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


def test_line_mode_leaves_the_depth_counter_alone(run_py):
    """A traced line is not a nesting level: it must not move the depth counter."""
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


def test_a_recursive_call_does_not_kill_later_traces(run_py):
    """The inner frame used to switch tracing off under its caller, leaving the
    tracer state stuck and every later @profiler_lbl silently empty."""
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def rec(n):
            a = 1
            if n:
                rec(n - 1)
            return a

        rec(2)

        @profiler_lbl
        def later():
            b = 2
            return b

        later()
        print("KEYS", "|".join(k for k in pc.keys() if " l " in k))
        """
    )
    keys = _keys(out)
    assert "rec l 6" in keys and "rec l 7" in keys
    assert "later l 15" in keys and "later l 16" in keys


def test_a_nested_line_profiled_call_does_not_cut_its_caller(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def inner():
            y = 2
            return y

        @profiler_lbl
        def outer():
            x = 1
            inner()
            return x

        outer()
        print("KEYS", "|".join(k for k in pc.keys() if " l " in k))
        """
    )
    keys = _keys(out)
    # the caller keeps every one of its lines ...
    assert keys == ["outer l 11", "outer l 12", "outer l 13"]
    # ... and the callee is not traced, as documented
    assert not any(k.startswith("inner l") for k in keys)


def test_two_threads_do_not_lose_each_other(run_py):
    """sys.settrace is per thread, so the tracer state is too."""
    out = run_py(
        """
        import threading
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl
        def work_a():
            x = 1
            return x

        @profiler_lbl
        def work_b():
            y = 2
            return y

        ts = [threading.Thread(target=work_a), threading.Thread(target=work_b)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        print("KEYS", "|".join(sorted(k for k in pc.keys() if " l " in k)))
        """
    )
    assert _keys(out) == ["work_a l 7", "work_a l 8",
                          "work_b l 12", "work_b l 13"]
