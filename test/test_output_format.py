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
    assert "time : mean / global" in header
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
