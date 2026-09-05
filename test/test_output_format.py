"""The printed layout is reproduced verbatim in README.md: treat it as a contract.

If one of these fails on purpose, regenerate the README blocks in the same commit.
"""

import time

import pytest

from custom_profiler import magic_profiler, profiler


def test_line_layout(pc, capsys):
    pc.print_line("my_func", "       1.00s ", "1.0K")
    line = capsys.readouterr().out.rstrip("\n")

    assert line.startswith(" ⚡")
    assert "| takes :        1.00s  |" in line
    assert "consumes :  Δ    1.0K" in line


def test_function_name_column_is_45_chars(pc, capsys):
    pc.print_line("f", "  t", "m")
    line = capsys.readouterr().out
    name_field = line.split(" |")[0][len(" ⚡ "):]
    assert len(name_field) == 45


def test_long_names_are_truncated_not_wrapped(pc, capsys):
    pc.print_line("n" * 80, "  t", "m")
    line = capsys.readouterr().out
    assert "n" * 45 in line
    assert "n" * 46 not in line


def test_peak_column_appears_only_once_a_thread_reported(pc, capsys):
    pc.print_line("f", "  t", "1.0K")
    assert "peak" not in capsys.readouterr().out

    pc.thread_view("f", 4096)
    pc.print_line("f", "  t", "1.0K")
    assert "peak    4.0K" in capsys.readouterr().out


def test_nested_entries_get_a_tree_glyph(pc, capsys):
    pc.deep = [1, 0]
    pc.print_line("inner", "  t", "m")
    assert "┌─inner" in capsys.readouterr().out

    pc.deep = [1, 1]
    pc.print_line("sibling", "  t", "m")
    assert "├─sibling" in capsys.readouterr().out


def test_top_level_entries_have_no_glyph(pc, capsys):
    pc.deep = [0, -1]
    pc.print_line("outer", "  t", "m")
    out = capsys.readouterr().out
    assert "┌─" not in out and "├─" not in out


def test_summary_depth_markers(pc, capsys):
    @profiler
    def outer():
        with magic_profiler("inner"):
            time.sleep(0.01)

    outer()
    capsys.readouterr()

    summary = str(pc)
    outer_row = next(l for l in summary.splitlines() if "outer" in l)
    inner_row = next(l for l in summary.splitlines() if "inner" in l)
    assert outer_row.split()[1] == "+---"   # only seen at depth 0
    assert inner_row.split()[1] == "-+--"   # only seen at depth 1


def test_summary_header_columns(pc):
    pc.incr()
    pc.save("f", 1.0, 0)
    header = next(l for l in str(pc).splitlines() if "fct name" in l)
    assert "Nb call" in header
    assert "time : max / global" in header      # max by default, not mean
    assert "mem. max :  Δ / Th" in header


def test_print_goes_to_stdout_when_no_logger(pc, capsys):
    pc._print("hello")
    assert capsys.readouterr().out == " ⚡hello\n"


def test_logger_replaces_stdout(pc, capsys):
    seen = []
    pc.logger = seen.append
    pc._print("hello")

    assert seen == ["  hello"]
    assert capsys.readouterr().out == ""


def test_force_print_in_csl_writes_to_both(pc, capsys):
    seen = []
    pc.logger = seen.append
    pc.forcePrintInCsl = True
    pc._print("hello")

    assert seen == ["  hello"]
    assert capsys.readouterr().out == " ⚡hello\n"


@pytest.mark.slow
def test_output_survives_a_console_that_cannot_print_the_bolt(run_py):
    """A cp1252 console (Windows) used to raise UnicodeEncodeError out of the
    atexit summary. Degrade to a replacement char instead, one per character so
    the columns stay put."""
    out = run_py(
        """
        from custom_profiler import profiler
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity

        pc.options(interactivity=Interactivity.DISABLE)

        @profiler
        def my_func():
            return 1

        my_func()
        """,
        env={"PYTHONIOENCODING": "cp1252"},
    )
    assert "customProfiler log" in out       # the summary is still printed
    assert "my_func" in out
    assert "?" in out                        # with the bolt replaced
    assert "Traceback" not in out


# --- the time column ---------------------------------------------------------

def _summary_row(pc, name):
    return next(l for l in str(pc).splitlines() if name in l and "+" in l)


def test_the_summary_shows_the_worst_call_not_the_mean(pc):
    """208 calls at 12ms and 8 at 740ms: the mean says 40ms and hides the tail."""
    for _ in range(200):
        pc.incr()
        pc.save("f", 0.012, 0)
    for _ in range(8):
        pc.incr()
        pc.save("f", 0.740, 0)

    time_field = _summary_row(pc, "f").split("|")[2]
    shown, total = [c.strip() for c in time_field.split("/")]
    assert shown == "740.00ms"          # the worst call
    assert total == "8.32s"             # not the mean, which is 40.00ms

    pc.options(summary_time="mean")
    time_field = _summary_row(pc, "f").split("|")[2]
    assert time_field.split("/")[0].strip() == "40.00ms"


def test_the_time_column_is_selectable(pc):
    for _ in range(10):
        pc.incr()
        pc.save("f", 0.1, 0)
    pc.incr()
    pc.save("f", 0.5, 0)

    pc.options(summary_time="mean")
    assert "time : mean / global" in str(pc)

    pc.options(summary_time=("median", "p95"))
    header = next(l for l in str(pc).splitlines() if "fct name" in l)
    assert "time : median / p95 / global" in header


def test_extra_columns_widen_the_rule_to_match(pc):
    pc.incr()
    pc.save("f", 0.1, 0)

    def widths():
        lines = str(pc).splitlines()
        header = next(l for l in lines if "fct name" in l)
        rule = next(l for l in lines if "===" in l)
        row = _summary_row(pc, "f")
        return len(header), len(rule), len(row)

    pc.options(summary_time=("max",))
    one = widths()
    assert one[0] == one[2]                      # header and row line up

    pc.options(summary_time=("mean", "max"))
    two = widths()
    assert two[2] == one[2] + 16                 # one more 13-char field plus " / "
    assert two[1] == one[1] + 16                 # and the rule follows
    assert two[0] == two[2]


def test_the_default_stays_a_108_character_rule(pc):
    pc.incr()
    pc.save("f", 0.1, 0)
    rule = next(l for l in str(pc).splitlines() if "===" in l)
    assert rule.count("=") == 108


@pytest.mark.parametrize("bad", [(), "p50", ("max", "p50"), 42])
def test_summary_time_rejects_unknown_statistics(pc, bad):
    with pytest.raises((AssertionError, TypeError), match="summary_time|iterable|argument"):
        pc.options(summary_time=bad)


# --- long names --------------------------------------------------------------

LONG_NAME = "services.billing.invoice.recompute_monthly_totals_for_account"


def test_the_default_still_truncates_at_45(pc, capsys):
    pc.print_line(LONG_NAME, "  t", "m")
    line = capsys.readouterr().out
    assert LONG_NAME[:45] in line
    assert LONG_NAME[:46] not in line


def test_a_wider_column_shows_more_of_the_name(pc, capsys):
    pc.options(name_width=70)
    pc.print_line(LONG_NAME, "  t", "m")
    line = capsys.readouterr().out

    assert LONG_NAME in line                       # 61 chars, fits in 70
    name_field = line.split(" |")[0][len(" ⚡ "):]
    assert len(name_field) == 70


def test_no_limit_never_truncates(pc, capsys):
    pc.options(name_width=None)
    pc.print_line(LONG_NAME, "  t", "m")
    assert LONG_NAME in capsys.readouterr().out


def test_no_limit_pads_short_names_to_the_default(pc, capsys):
    pc.options(name_width=None)
    pc.print_line("f", "  t", "m")
    name_field = capsys.readouterr().out.split(" |")[0][len(" ⚡ "):]
    assert len(name_field) == 45


def test_the_summary_sizes_itself_to_the_longest_name(pc):
    pc.incr()
    pc.save(LONG_NAME, 1.0, 0)
    pc.incr()
    pc.save("f", 1.0, 0)
    pc.options(name_width=None)

    lines = [l for l in str(pc).splitlines() if "fct name" in l or "+---" in l or "===" in l]
    assert LONG_NAME in "\n".join(lines)
    assert len(set(len(l) for l in lines)) == 1        # header, rule and rows line up


def test_a_wider_column_widens_the_rule_by_the_same_amount(pc):
    pc.incr()
    pc.save("f", 1.0, 0)

    def rule():
        return next(l for l in str(pc).splitlines() if "===" in l).count("=")

    default = rule()
    pc.options(name_width=60)
    assert rule() == default + 15


def test_the_live_line_and_the_summary_share_the_width(pc, capsys):
    pc.options(name_width=60)
    pc.incr()
    pc.save("f", 1.0, 0)
    live = capsys.readouterr().out.splitlines()[0]
    header = next(l for l in str(pc).splitlines() if "fct name" in l)

    assert live.index(" | takes") == header.index(" | Nb call")


@pytest.mark.parametrize("bad", [0, 5, -10, 12.5, "wide", True])
def test_name_width_rejects_unusable_values(pc, bad):
    with pytest.raises(AssertionError, match="name_width"):
        pc.options(name_width=bad)
