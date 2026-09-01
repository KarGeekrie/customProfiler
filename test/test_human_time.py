"""`human_time_duration` produces the fixed-width strings the log columns rely on."""

import pytest

from custom_profiler.human_readable_time import human_time_duration as htd


@pytest.mark.parametrize("seconds, unit", [
    (1, "s "),
    (60, "s "),          # 60 still belongs to the "small" branch
    (0.5, "ms"),
    (1e-3, "ms"),
    (1e-6, "us"),
    (1e-9, "ns"),
])
def test_unit_selection(seconds, unit):
    got = htd(seconds)
    expected = unit if unit != "us" else "µs"
    assert got.endswith(expected), got


@pytest.mark.parametrize("seconds", [1, 60, 0.5, 1e-3, 1e-6, 1e-9, 1e-12])
def test_short_durations_are_13_chars_wide(seconds):
    """The summary columns are aligned by this width; do not change it lightly."""
    assert len(htd(seconds)) == 13


@pytest.mark.parametrize("seconds, expected", [
    (1, "       1.00s "),
    (0.5, "     500.00ms"),
    (1e-3, "       1.00ms"),
])
def test_exact_rendering(seconds, expected):
    assert htd(seconds) == expected


def test_below_nanosecond_falls_back_to_scientific():
    assert htd(1e-12) == "   1.00E-12s "


def test_zero_returns_the_int_zero():
    """Documented quirk: the only non-str return value."""
    assert htd(0) == 0
    assert isinstance(htd(0), int)


@pytest.mark.parametrize("seconds, expected", [
    (61, "     1min 1s"),
    (90, "     1min30s"),
    (3599, "    59min59s"),
])
def test_minutes_branch(seconds, expected):
    assert htd(seconds) == expected


def test_hours_branch_with_int_input():
    assert htd(3600) == "  1h 0min 0s"
    assert htd(3661) == "  1h 1min 1s"


def test_hours_branch_with_float_input():
    """A real perf_counter() delta is a float: it must stay 12 chars wide."""
    assert htd(7325.4) == "  2h 2min 5s"
    assert len(htd(3600.0)) == 12


@pytest.mark.parametrize("bad", ["1", None, [1], True])
def test_rejects_non_numeric(bad):
    with pytest.raises(AssertionError):
        htd(bad)
