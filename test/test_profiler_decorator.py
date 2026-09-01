"""`@profiler` and `magic_profiler`: the two entry points users actually call."""

import threading
import time

import pytest

from custom_profiler import magic_profiler, profiler
from custom_profiler.collecteur import Interactivity

SLEEP = 0.02


def test_decorator_keeps_the_function_identity(pc):
    @profiler
    def my_func(a, b=0):
        """the docstring"""
        return a + b

    assert my_func.__name__ == "my_func"
    assert my_func.__doc__ == "the docstring"


def test_decorator_is_transparent(pc):
    @profiler
    def my_func(a, *args, **kwargs):
        return a, args, kwargs

    assert my_func(1, 2, k=3) == (1, (2,), {"k": 3})


def test_call_count_and_times(pc, capsys):
    @profiler
    def my_func():
        time.sleep(SLEEP)

    start = time.perf_counter()
    for _ in range(3):
        my_func()
    wall = time.perf_counter() - start
    capsys.readouterr()

    data = pc["my_func"]
    assert data["nb_call"] == 3
    # against the measured wall clock, never the nominal sleep: a loaded CI
    # runner turns sleep(0.02) into 0.07
    assert data["global_time_s"] == pytest.approx(wall, abs=0.05)
    assert data["mean_time_s"] == pytest.approx(data["global_time_s"] / 3)


def test_memory_delta_is_recorded_per_call(pc, capsys):
    @profiler
    def eat():
        big = [0] * (10 ** 6)
        return len(big)

    eat()
    capsys.readouterr()
    assert len(pc["eat"]["per_call_memory_b"]) == 1


def test_context_manager_records_under_its_label(pc, capsys):
    start = time.perf_counter()
    with magic_profiler("my_block"):
        time.sleep(SLEEP)
    wall = time.perf_counter() - start
    capsys.readouterr()

    assert pc["my_block"]["nb_call"] == 1
    assert pc["my_block"]["global_time_s"] == pytest.approx(wall, abs=0.05)


def test_nesting_is_recorded_as_depth(pc, capsys):
    @profiler
    def outer():
        with magic_profiler("inner"):
            time.sleep(0.01)

    outer()
    capsys.readouterr()

    assert pc.profData["outer"]["deep"] == [0]
    assert pc.profData["inner"]["deep"] == [1]


def test_depth_returns_to_the_baseline(pc, capsys):
    @profiler
    def outer():
        with magic_profiler("inner"):
            pass

    outer()
    capsys.readouterr()
    assert pc.deep[0] == -1


def test_nested_functions_are_recorded_separately(pc, capsys):
    @profiler
    def inner():
        time.sleep(0.01)

    @profiler
    def outer():
        inner()

    outer()
    capsys.readouterr()

    assert pc["outer"]["nb_call"] == 1
    assert pc["inner"]["nb_call"] == 1
    assert pc["outer"]["global_time_s"] >= pc["inner"]["global_time_s"]


def test_watcher_thread_is_started_and_joined(pc, capsys):
    before = threading.active_count()
    seen = {}

    @profiler
    def my_func():
        seen["during"] = threading.active_count()
        time.sleep(0.05)

    my_func()
    capsys.readouterr()

    assert seen["during"] == before + 1
    assert threading.active_count() == before


def test_disable_starts_no_thread(pc, capsys):
    pc.interractivity = Interactivity.DISABLE
    before = threading.active_count()
    seen = {}

    @profiler
    def my_func():
        seen["during"] = threading.active_count()

    my_func()
    capsys.readouterr()

    assert seen["during"] == before
    assert pc["my_func"]["nb_call"] == 1     # still profiled, just not watched


# --- behaviour when the profiled callable raises -----------------------------
# Run with DISABLE so no watcher thread can leak into the rest of the session.

def test_exception_propagates(pc, capsys):
    pc.interractivity = Interactivity.DISABLE

    @profiler
    def boom():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        boom()
    capsys.readouterr()


def test_raising_call_is_still_recorded(pc, capsys):
    pc.interractivity = Interactivity.DISABLE

    @profiler
    def boom():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        boom()
    capsys.readouterr()
    assert pc["boom"]["nb_call"] == 1


def test_depth_is_restored_when_the_call_raises(pc, capsys):
    pc.interractivity = Interactivity.DISABLE

    @profiler
    def boom():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        boom()
    capsys.readouterr()
    assert pc.deep[0] == -1


@pytest.mark.slow
def test_watcher_thread_is_not_leaked_when_the_call_raises(run_py):
    """Run out-of-process: a leaked watcher would pollute every later test."""
    out = run_py(
        """
        import threading
        from custom_profiler import profiler
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity

        pc.options(interractivity=Interactivity.MF_NO_INTERAC)
        before = threading.active_count()

        @profiler
        def boom():
            raise ValueError("boom")

        try:
            boom()
        except ValueError:
            pass
        print("LEAKED", threading.active_count() - before)
        """
    )
    leaked = int(next(l for l in out.splitlines() if l.startswith("LEAKED")).split()[1])
    assert leaked == 0
