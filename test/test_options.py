"""`options()` and the INTERACTIVITY_OPT_ENUM branches."""

import pytest

from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM

from conftest import requires_pty

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("value", ["ENABLE", "MF_NO_INTERAC", "DISABLE"])
def test_explicit_values_are_kept(pc, value):
    pc.options(interractivity=value)
    assert pc.interractivity == value


def test_invalid_value_is_rejected(pc):
    with pytest.raises(AssertionError, match="INTERACTIVITY_OPT_ENUM"):
        pc.options(interractivity="LOUD")


def test_options_resets_what_you_do_not_pass(pc):
    """Documented gotcha: every keyword has a default, so a partial call resets."""
    pc.options(interractivity=INTERACTIVITY_OPT_ENUM.DISABLE, forcePrintInCsl=True)
    assert pc.forcePrintInCsl is True

    pc.options(interractivity=INTERACTIVITY_OPT_ENUM.DISABLE)
    assert pc.forcePrintInCsl is False


def test_useLogger_false_clears_the_logger(pc):
    pc.logger = print
    pc.options(interractivity=INTERACTIVITY_OPT_ENUM.DISABLE, useLogger=False)
    assert pc.logger is None


def test_auto_without_a_tty_disables_interactive_printing(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM
        pc.options(interractivity=INTERACTIVITY_OPT_ENUM.AUTO)
        print("MODE", pc.interractivity)
        """
    )
    assert "MODE MF_NO_INTERAC" in out


@requires_pty
def test_auto_on_a_tty_enables_interactive_printing(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM
        pc.options(interractivity=INTERACTIVITY_OPT_ENUM.AUTO)
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
        from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM

        pc.options(interractivity=INTERACTIVITY_OPT_ENUM.ENABLE)

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


def test_useLogger_downgrades_enable_to_mf_no_interac(run_py):
    out = run_py(
        """
        import logging
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM

        logging.basicConfig(filename="out.log", filemode="w")
        pc.options(interractivity=INTERACTIVITY_OPT_ENUM.ENABLE, useLogger=True)
        print("MODE", pc.interractivity)
        """
    )
    assert "MODE MF_NO_INTERAC" in out


def test_custom_level_can_only_be_added_once(run_py):
    """add_logging_level() clobber-guards itself; a second call raises."""
    out = run_py(
        """
        import logging
        from custom_profiler import profiler_collecteur as pc
        from custom_profiler.collecteur import INTERACTIVITY_OPT_ENUM

        logging.basicConfig(filename="out.log", filemode="w")
        opts = dict(interractivity=INTERACTIVITY_OPT_ENUM.DISABLE,
                    useLogger=True, addCustumLvl=True)
        pc.options(**opts)
        try:
            pc.options(**opts)
            print("SECOND ok")
        except AttributeError as err:
            print("SECOND AttributeError", err)
        """
    )
    assert "SECOND AttributeError" in out
    assert "PROFILER already defined" in out
