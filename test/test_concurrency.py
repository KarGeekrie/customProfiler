"""Threads and recursion: two shapes of call that a single global depth counter
used to describe as a call tree that never existed.
"""

import threading
import time

import pytest

from custom_profiler import magic_profiler, profiler
from custom_profiler.collecteur import Interactivity


@pytest.fixture(autouse=True)
def quiet(pc, capsys):
    pc.interractivity = Interactivity.DISABLE
    yield
    capsys.readouterr()


# --- threads -----------------------------------------------------------------

def test_concurrent_calls_are_not_nested(pc):
    """Four threads calling the same function are four top-level calls."""
    @profiler
    def work():
        time.sleep(0.05)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert pc["work"]["nb_call"] == 4
    assert pc.profData["work"]["deep"] == [0, 0, 0, 0]


def test_each_thread_keeps_its_own_depth(pc):
    seen = {}

    @profiler
    def outer(tag):
        with magic_profiler("inner_" + tag):
            time.sleep(0.02)
        seen[tag] = pc.deep[0]

    threads = [threading.Thread(target=outer, args=(t,)) for t in "ab"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert seen == {"a": 0, "b": 0}
    assert pc.profData["inner_a"]["deep"] == [1]
    assert pc.profData["inner_b"]["deep"] == [1]


def test_the_main_thread_depth_is_untouched_by_workers(pc):
    @profiler
    def work():
        time.sleep(0.01)

    before = list(pc.deep)
    t = threading.Thread(target=work)
    t.start()
    t.join()
    assert pc.deep == before


def test_concurrent_calls_are_all_recorded(pc):
    """The collector is mutated from several threads at once."""
    @profiler
    def work():
        time.sleep(0.005)

    threads = [threading.Thread(target=work) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert pc["work"]["nb_call"] == 16
    assert len(pc.profData["work"]["dm_list"]) == 16


# --- recursion ---------------------------------------------------------------

def test_recursion_counts_every_call(pc):
    @profiler
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    fib(4)
    assert pc["fib"]["nb_call"] == 9


def test_recursion_times_only_the_outermost_frame(pc):
    @profiler
    def countdown(n):
        time.sleep(0.02)
        if n:
            countdown(n - 1)

    start = time.perf_counter()
    countdown(3)
    wall = time.perf_counter() - start

    data = pc["countdown"]
    assert data["nb_call"] == 4
    # 4 frames x 20ms of sleep, but only one span of wall clock
    assert data["global_time_s"] == pytest.approx(wall, abs=0.05)
    assert data["global_time_s"] < 2 * wall


def test_recursion_reports_one_line_per_outermost_call(pc, capsys):
    @profiler
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    capsys.readouterr()
    fib(4)
    printed = [l for l in capsys.readouterr().out.splitlines() if "takes :" in l]
    assert len(printed) == 1


def test_recursion_leaves_the_depth_counter_balanced(pc):
    @profiler
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    fib(4)
    assert pc.deep[0] == -1
    assert pc.profData["fib"]["deep"] == [0]


def test_a_second_top_level_call_is_still_timed(pc):
    """Re-entrancy is per running frame, not a one-shot latch."""
    @profiler
    def once():
        time.sleep(0.02)

    start = time.perf_counter()
    once()
    once()
    wall = time.perf_counter() - start

    data = pc["once"]
    assert data["nb_call"] == 2
    # both calls are timed, so the total tracks the wall clock of the pair --
    # never the nominal sleep, which a loaded runner overshoots by 5x
    assert data["global_time_s"] == pytest.approx(wall, abs=0.05)
    assert len(data["per_call_memory_b"]) == 2


def test_mutual_recursion_is_timed_per_name(pc):
    @profiler
    def ping(n):
        if n:
            pong(n - 1)

    @profiler
    def pong(n):
        if n:
            ping(n - 1)

    ping(4)
    assert pc["ping"]["nb_call"] == 3
    assert pc["pong"]["nb_call"] == 2
    assert pc.profData["ping"]["deep"] == [0]


def test_recursive_context_manager(pc):
    def walk(n):
        with magic_profiler("walk"):
            if n:
                walk(n - 1)

    walk(3)
    assert pc["walk"]["nb_call"] == 4
    assert pc.profData["walk"]["deep"] == [0]
