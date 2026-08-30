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
    assert entry["deep"] == [0, 0, 0]


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
        "max_memory", "max_memory_b",
        "peack_memory", "peack_memory_b",
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
    assert data["max_memory_b"] == [1024, 2048]      # the whole list, not the max
    assert data["max_memory"] == "2.0K"              # ... but the string is the max
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
    assert pc["f"]["peack_memory_b"] == 4096
    assert pc["f"]["peack_memory"] == "4.0K"


def test_peak_memory_falls_back_to_the_delta(pc):
    pc.incr()
    pc.save("f", 1.0, 4096)
    pc.thread_view("f", 1024)
    assert pc["f"]["peack_memory_b"] == 4096


def test_get_global_info_keys_and_types(pc):
    info = pc.get_global_info()
    assert set(info) == {
        "global_run_time", "global_run_time_s", "memory_peack", "memory_peack_b",
    }
    assert info["global_run_time_s"] > 0
    assert info["memory_peack_b"] > 0
    assert isinstance(info["memory_peack"], str)


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
