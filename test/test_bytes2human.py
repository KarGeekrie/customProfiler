"""The collecteur wraps psutil's `bytes2human` to render *negative* deltas."""

import psutil
import pytest

from custom_profiler.collecteur import bytes2human, get_ENUM_list, INTERACTIVITY_OPT_ENUM


@pytest.mark.parametrize("value, expected", [
    (0, "0.0B"),
    (0.0, "0.0B"),
    (10, "10.0B"),
    (1024, "1.0K"),
])
def test_positive_matches_psutil(value, expected):
    assert bytes2human(value) == expected
    assert bytes2human(value) == psutil._common.bytes2human(value)


@pytest.mark.parametrize("value, expected", [
    (-10, "-10.0B"),
    (-1024, "-1.0K"),
    (-1048576, "-1.0M"),
])
def test_negative_gets_a_minus_sign(value, expected):
    """`del b` produces a negative delta; psutil's own helper cannot render it."""
    assert bytes2human(value) == expected


def test_zero_is_not_signed():
    assert not bytes2human(0).startswith("-")


def test_enum_list_exposes_only_the_options():
    assert sorted(get_ENUM_list(INTERACTIVITY_OPT_ENUM)) == [
        "AUTO", "DISABLE", "ENABLE", "MF_NO_INTERAC",
    ]
