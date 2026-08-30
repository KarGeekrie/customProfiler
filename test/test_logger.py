"""Logger wiring and the end-of-run summary.

`add_logging_level` can only run once per interpreter and the summary is emitted
from `atexit`/`__del__`, so every case here gets its own process.
"""

import pytest

pytestmark = pytest.mark.slow

PROFILED = """
    import logging
    from custom_profiler import profiler
    from custom_profiler import profiler_collecteur as pc
    from custom_profiler.collecteur import Interactivity

    logging.basicConfig(filename="out.log", filemode="w")
    pc.options(interactivity=Interactivity.MF_NO_INTERAC,
               use_logger=True,
               logger_name=" ⚡",
               add_custom_level={add_custom_level},
               profiler_level=25,
               force_print_in_console={force_print_in_console},
               no_summary_in_log={no_summary_in_log})

    @profiler
    def my_func():
        a = [1] * (10 ** 5)
        return a

    my_func()
"""


@pytest.fixture
def run_logged(run_py, tmp_path):
    def _run(add_custom_level=True, force_print_in_console=False, no_summary_in_log=False):
        stdout = run_py(PROFILED.format(
            add_custom_level=add_custom_level,
            force_print_in_console=force_print_in_console,
            no_summary_in_log=no_summary_in_log,
        ))
        return stdout, (tmp_path / "out.log").read_text(encoding="utf-8")

    return _run


def test_custom_level_is_used(run_logged):
    _, log = run_logged(add_custom_level=True)
    assert "PROFILER" in log
    assert "my_func" in log


def test_without_custom_level_it_falls_back_to_info(run_logged):
    _, log = run_logged(add_custom_level=False)
    assert "INFO" in log
    assert "PROFILER" not in log
    assert "my_func" in log


def test_logger_name_prefixes_every_record(run_logged):
    _, log = run_logged()
    assert "⚡" in log


def test_summary_is_appended_at_exit(run_logged):
    _, log = run_logged(no_summary_in_log=False)
    assert "customProfiler log" in log
    assert "fct name" in log
    assert "=" * 108 in log


def test_no_summary_in_log_suppresses_it(run_logged):
    _, log = run_logged(no_summary_in_log=True)
    assert "my_func" in log
    assert "fct name" not in log


def test_logger_silences_the_console(run_logged):
    stdout, log = run_logged(force_print_in_console=False)
    assert "my_func" in log
    assert "my_func" not in stdout


def test_force_print_in_csl_keeps_both(run_logged):
    stdout, log = run_logged(force_print_in_console=True)
    assert "my_func" in log
    assert "my_func" in stdout


def test_summary_is_printed_at_exit_without_a_logger(run_py):
    """Without a logger the summary comes from `__del__` at interpreter shutdown."""
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
        print("END OF USER CODE")
        """
    )
    body, _, summary = out.partition("END OF USER CODE")
    assert "customProfiler log" in summary
    assert "my_func" in summary


def test_bare_import_still_reports_the_global_timer(run_py):
    out = run_py("import custom_profiler\n")
    assert "customProfiler log" in out
    assert "global timer" in out
    assert "fct name" not in out
