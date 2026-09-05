"""The data-access API documented in the README is a public contract."""

import time

import pytest


def test_fresh_collecteur_is_empty(pc):
    assert list(pc.profData.keys()) == []
    assert pc.deep == [-1, -1]


def test_unknown_key_lists_the_available_ones(pc):
    pc.incr()
    pc.save("known", 1.0, 10)
    with pytest.raises(KeyError) as err:
        pc["nope"]
    assert "known" in str(err.value)


def test_save_aggregates_repeated_calls(pc):
    for _ in range(3):
        pc.incr()
        pc.save("f", 0.5, 100)

    entry = pc.profData["f"]
    assert entry["nbCall"] == 3
    assert entry["dt"] == pytest.approx(1.5)
    assert entry["dm_list"] == [100, 100, 100]
    assert entry["dt_list"] == [0.5, 0.5, 0.5]
    assert entry["dt_max"] == pytest.approx(0.5)
    assert entry["deep"] == {0}          # the set of depths, not one per call


def test_save_restores_the_depth_counter(pc):
    pc.incr()
    pc.save("f", 0.1, 0)
    assert pc.deep[0] == -1


def test_getitem_exposes_exactly_the_documented_keys(pc):
    pc.incr()
    pc.save("f", 2.0, 1024)
    assert set(pc["f"]) == {
        "nb_call",
        "global_time", "global_time_s",
        "mean_time", "mean_time_s",
        "max_time", "max_time_s",
        "median_time_s", "p95_time_s", "per_call_time_s",
        "max_memory", "max_memory_b", "per_call_memory_b",
        "peak_memory", "peak_memory_b",
    }


def test_getitem_values(pc):
    pc.incr()
    pc.save("f", 2.0, 1024)
    pc.incr()
    pc.save("f", 4.0, 2048)

    data = pc["f"]
    assert data["nb_call"] == 2
    assert data["global_time_s"] == pytest.approx(6.0)
    assert data["mean_time_s"] == pytest.approx(3.0)
    assert data["max_memory_b"] == 2048              # the max, like max_memory
    assert data["per_call_memory_b"] == [1024, 2048]  # one entry per call
    assert data["max_memory"] == "2.0K"
    assert data["global_time"].strip() == "6.00s"
    assert data["mean_time"].strip() == "3.00s"


def test_thread_view_keeps_the_maximum(pc):
    pc.thread_view("f", 10)
    pc.thread_view("f", 50)
    pc.thread_view("f", 20)
    assert pc.profThread["f"] == 50


def test_peak_memory_combines_deltas_and_thread_samples(pc):
    pc.incr()
    pc.save("f", 1.0, 1024)
    pc.thread_view("f", 4096)
    assert pc["f"]["peak_memory_b"] == 4096
    assert pc["f"]["peak_memory"] == "4.0K"


def test_peak_memory_falls_back_to_the_delta(pc):
    pc.incr()
    pc.save("f", 1.0, 4096)
    pc.thread_view("f", 1024)
    assert pc["f"]["peak_memory_b"] == 4096


def test_get_global_info_keys_and_types(pc):
    info = pc.get_global_info()
    assert set(info) == {
        "global_run_time", "global_run_time_s", "memory_peak", "memory_peak_b",
    }
    assert info["global_run_time_s"] > 0
    assert info["memory_peak_b"] > 0
    assert isinstance(info["memory_peak"], str)


def test_global_run_time_increases(pc):
    first = pc.get_global_info()["global_run_time_s"]
    time.sleep(0.01)
    assert pc.get_global_info()["global_run_time_s"] > first


def test_str_without_data_is_the_short_form(pc):
    out = str(pc)
    assert "global timer" in out
    assert "max memory use" in out
    assert "fct name" not in out


def test_str_with_data_is_the_summary_table(pc):
    pc.incr()
    pc.save("my_func", 1.0, 1024)
    out = str(pc)
    assert "customProfiler log" in out
    assert "fct name" in out and "Nb call" in out
    assert "=" * 108 in out
    assert "my_func" in out


def test_vendored_bytes2human_matches_psutil():
    """The formatting is vendored to avoid psutil's private API: keep it identical."""
    import psutil
    from custom_profiler.collecteur import _bytes2human
    for value in [0, 1, 10, 1023, 1024, 1025, 10 ** 6, 10 ** 9, 2 ** 40, 3 * 2 ** 50]:
        assert _bytes2human(value) == psutil._common.bytes2human(value), value


def test_global_memory_peak_is_plausible(pc):
    """Guards the ru_maxrss unit: kibibytes on Linux, bytes on macOS."""
    import psutil
    rss = psutil.Process().memory_info().rss
    peak = pc.get_global_info()["memory_peak_b"]
    assert rss * 0.5 < peak < rss * 20


def test_summary_survives_a_call_still_running(pc):
    """An inner recursive frame records nothing until the outer one returns."""
    pc.incr("f")
    pc.incr("f")
    pc.save("f", 1.0, 100, outermost=False)
    assert pc["f"]["nb_call"] == 1
    assert pc["f"]["per_call_memory_b"] == []
    assert "f" in str(pc)


def test_keep_deep_leaves_the_counter_alone(pc):
    pc.incr()
    before = pc.deep[0]
    pc.save("line", 0.1, 0, keep_deep=True)
    assert pc.deep[0] == before
    pc.save("fct", 0.1, 0)
    assert pc.deep[0] == before - 1


# --- per-call times ----------------------------------------------------------

def test_per_call_times_are_kept(pc):
    for dt in (0.1, 0.3, 0.2):
        pc.incr()
        pc.save("f", dt, 0)

    data = pc["f"]
    assert data["per_call_time_s"] == [0.1, 0.3, 0.2]
    assert data["max_time_s"] == pytest.approx(0.3)
    assert data["max_time"].strip() == "300.00ms"
    assert data["global_time_s"] == pytest.approx(0.6)
    assert data["mean_time_s"] == pytest.approx(0.2)


def test_median_and_p95_see_the_tail_the_mean_hides(pc):
    """The point of the whole thing: 99 fast calls and one slow one."""
    for _ in range(99):
        pc.incr()
        pc.save("f", 0.01, 0)
    pc.incr()
    pc.save("f", 5.0, 0)

    data = pc["f"]
    assert data["mean_time_s"] == pytest.approx(0.0599, abs=1e-3)   # says "fast"
    assert data["median_time_s"] == pytest.approx(0.01)             # typical call
    assert data["max_time_s"] == pytest.approx(5.0)                 # the tail
    assert data["p95_time_s"] == pytest.approx(0.01)                # 1 in 100 is not p95


def test_p95_tracks_a_fatter_tail(pc):
    for _ in range(90):
        pc.incr()
        pc.save("f", 0.01, 0)
    for _ in range(10):
        pc.incr()
        pc.save("f", 2.0, 0)

    assert pc["f"]["p95_time_s"] == pytest.approx(2.0)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_statistics_are_defined_for_tiny_samples(pc, n):
    for _ in range(n):
        pc.incr()
        pc.save("f", 0.2, 0)

    data = pc["f"]
    assert data["median_time_s"] == pytest.approx(0.2)
    assert data["p95_time_s"] == pytest.approx(0.2)
    assert data["max_time_s"] == pytest.approx(0.2)


def test_an_unprofiled_entry_has_zeroed_statistics(pc):
    """A recursive inner frame records nothing but the call count."""
    pc.incr("f")
    pc.incr("f")
    pc.save("f", 1.0, 100, outermost=False)

    data = pc["f"]
    assert data["nb_call"] == 1
    assert data["max_time_s"] == 0.
    assert data["median_time_s"] == 0.
    assert data["p95_time_s"] == 0.
    assert data["per_call_time_s"] == []


# --- the sample cap ----------------------------------------------------------

def test_samples_are_capped_but_count_sum_and_max_stay_exact(pc):
    pc.options(max_samples=10)
    for i in range(50):
        pc.incr()
        pc.save("f", 0.01 * (i + 1), i)

    entry = pc.profData["f"]
    assert len(entry["dt_list"]) == 10        # the distribution is sampled ...
    assert len(entry["dm_list"]) == 10
    data = pc["f"]
    assert data["nb_call"] == 50              # ... the rest is not
    assert data["global_time_s"] == pytest.approx(0.01 * sum(range(1, 51)))
    assert data["max_time_s"] == pytest.approx(0.5)     # the 50th call, past the cap
    assert data["max_memory_b"] == 49


def test_max_samples_defaults_to_100k(pc):
    assert pc.max_samples == 100_000


@pytest.mark.parametrize("bad", [0, -1, 1.5, "lots", None, True])
def test_max_samples_must_be_a_positive_int(pc, bad):
    with pytest.raises(AssertionError, match="max_samples"):
        pc.options(max_samples=bad)
