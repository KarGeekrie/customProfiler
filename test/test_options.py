"""`options()`, the Interactivity branches, and the legacy keyword aliases."""

import pytest

from custom_profiler.collecteur import Interactivity

from conftest import requires_pty

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("value", ["ENABLE", "MF_NO_INTERAC", "DISABLE"])
def test_explicit_values_are_kept(pc, value):
    pc.options(interactivity=value)
    assert pc.interractivity == value


def test_invalid_value_is_rejected(pc):
    with pytest.raises(AssertionError, match="Interactivity"):
        pc.options(interactivity="LOUD")


def test_unknown_keyword_is_rejected(pc):
    with pytest.raises(TypeError, match="nonsense"):
        pc.options(nonsense=True)


def test_options_keeps_what_you_do_not_pass(pc):
    """A partial call means "change only this", not "reset the rest"."""
    pc.options(interactivity=Interactivity.DISABLE, force_print_in_console=True)
    assert pc.forcePrintInCsl is True

    pc.options(no_summary_in_log=True)
    assert pc.forcePrintInCsl is True
    assert pc.interractivity == Interactivity.DISABLE


def test_the_interactivity_attribute_has_a_correct_alias(pc):
    pc.options(interactivity=Interactivity.DISABLE)
    assert pc.interactivity == Interactivity.DISABLE
    pc.interactivity = Interactivity.MF_NO_INTERAC
    assert pc.interractivity == Interactivity.MF_NO_INTERAC


@pytest.mark.parametrize("old, new, value", [
    ("interractivity", "interactivity", "DISABLE"),
    ("forcePrintInCsl", "force_print_in_console", True),
    ("noSummaryInLog", "no_summary_in_log", True),
    ("loggername", "logger_name", "x"),
])
def test_legacy_keywords_still_work_and_warn(pc, old, new, value):
    with pytest.warns(DeprecationWarning, match=old):
        pc.options(**{old: value})

    attr = {"interactivity": "interractivity",
            "force_print_in_console": "forcePrintInCsl",
            "no_summary_in_log": "noSummaryInLog",
            "logger_name": "loggername"}[new]
    assert getattr(pc, attr) == value


def test_use_logger_false_clears_the_logger(pc):
    pc.logger = print
    pc.options(use_logger=False)
    assert pc.logger is None


def test_auto_without_a_tty_disables_interactive_printing(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity
        pc.options(interactivity=Interactivity.AUTO)
        print("MODE", pc.interractivity)
        """
    )
    assert "MODE MF_NO_INTERAC" in out


@requires_pty
def test_auto_on_a_tty_enables_interactive_printing(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity
        pc.options(interactivity=Interactivity.AUTO)
        print("MODE", pc.interractivity)
        """,
        tty=True,
    )
    assert "MODE ENABLE" in out


def test_import_resolves_auto_on_its_own(run_py):
    """`import custom_profiler` already calls options(AUTO): that is by design."""
    out = run_py(
        """
        from custom_profiler import profiler_collecteur as pc
        print("MODE", pc.interractivity)
        print("TIMER", pc.get_global_info()["global_run_time_s"] > 0)
        """
    )
    assert "MODE MF_NO_INTERAC" in out
    assert "TIMER True" in out


@requires_pty
def test_interactive_mode_refreshes_in_place(run_py):
    """ENABLE repaints the current line with \\r and a yellow escape code."""
    out = run_py(
        """
        import time
        from custom_profiler import profiler
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity

        pc.options(interactivity=Interactivity.ENABLE)

        @profiler
        def my_func():
            time.sleep(1.2)

        my_func()
        """,
        tty=True,
    )
    assert "\\033[93m" in out.replace("\x1b", "\\033")
    assert "\r" in out
    assert "my_func" in out


def test_use_logger_downgrades_enable_to_mf_no_interac(run_py):
    out = run_py(
        """
        import logging
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity

        logging.basicConfig(filename="out.log", filemode="w", encoding="utf-8")
        pc.options(interactivity=Interactivity.ENABLE, use_logger=True)
        print("MODE", pc.interractivity)
        """
    )
    assert "MODE MF_NO_INTERAC" in out


def test_configuring_the_logger_twice_is_idempotent(run_py):
    """add_logging_level() raises if called twice; options() must not let it."""
    out = run_py(
        """
        import logging
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import Interactivity

        logging.basicConfig(filename="out.log", filemode="w", encoding="utf-8")
        opts = dict(interactivity=Interactivity.DISABLE,
                    use_logger=True, add_custom_level=True)
        pc.options(**opts)
        try:
            pc.options(**opts)
            print("SECOND ok")
        except AttributeError as err:
            print("SECOND AttributeError", err)
        """
    )
    assert "SECOND ok" in out
