"""The surface `custom_profiler` promises for 1.0: exports, mapping interface,
named decorators, the kill switch, and the deprecated spellings it keeps alive.
"""

import time

import pytest

import custom_profiler
from custom_profiler import magic_profiler, profiler, profiler_lbl
from custom_profiler.collecteur import Interactivity


@pytest.fixture(autouse=True)
def quiet(pc, capsys):
    pc.interractivity = Interactivity.DISABLE
    yield
    capsys.readouterr()


# --- exports -----------------------------------------------------------------

def test_all_lists_the_public_names():
    assert set(custom_profiler.__all__) == {
        "profiler", "profiler_lbl", "magic_profiler", "profiler_collecteur",
        "Interactivity", "INTERACTIVITY_OPT_ENUM", "__version__",
    }


def test_functools_partial_no_longer_leaks():
    assert not hasattr(custom_profiler, "partial")


def test_version_is_exposed():
    assert isinstance(custom_profiler.__version__, str)
    assert custom_profiler.__version__.split(".")[0].isdigit()


# --- named decorators --------------------------------------------------------

def test_decorator_accepts_a_custom_name(pc):
    @profiler(name="my label")
    def whatever():
        return 1

    assert whatever() == 1
    assert "my label" in pc
    assert "whatever" not in pc


def test_bare_decorator_still_works(pc):
    @profiler
    def whatever():
        return 1

    whatever()
    assert "whatever" in pc


def test_named_decorator_keeps_the_function_identity(pc):
    @profiler(name="label")
    def whatever(a, b=1):
        """doc"""
        return a + b

    assert whatever.__name__ == "whatever"
    assert whatever.__doc__ == "doc"
    assert whatever(1, b=2) == 3


def test_line_decorator_accepts_a_name(run_py):
    out = run_py(
        """
        from custom_profiler import profiler_lbl
        from custom_profiler import profiler_collecteur as pc

        @profiler_lbl(name="traced")
        def whatever():
            a = 1
            return a

        whatever()
        print("KEYS", "|".join(pc.keys()))
        """
    )
    assert "traced" in out
    assert "whatever l" not in out


# --- mapping interface -------------------------------------------------------

def test_len_iter_and_contains(pc):
    for name in ("a", "b"):
        pc.incr()
        pc.save(name, 1.0, 0)

    assert len(pc) == 2
    assert list(pc) == ["a", "b"]
    assert "a" in pc and "zzz" not in pc
    assert pc.keys() == ["a", "b"]


def test_items_and_values(pc):
    pc.incr()
    pc.save("a", 2.0, 8)

    (key, data), = pc.items()
    assert key == "a"
    assert data["global_time_s"] == pytest.approx(2.0)
    assert pc.values()[0] == data


def test_to_dict_is_plain_data(pc):
    pc.incr()
    pc.save("a", 1.0, 16)

    dumped = pc.to_dict()
    assert set(dumped) == {"global_info", "profiled"}
    assert type(dumped["profiled"]["a"]) is dict
    assert dumped["profiled"]["a"]["nb_call"] == 1
    assert dumped["global_info"]["global_run_time_s"] > 0


def test_to_dict_is_json_serialisable(pc):
    import json
    pc.incr()
    pc.save("a", 1.0, 16)
    assert json.loads(json.dumps(pc.to_dict()))["profiled"]["a"]["nb_call"] == 1


def test_reset_clears_measurements(pc):
    pc.incr()
    pc.save("a", 1.0, 16)
    pc.thread_view("a", 32)
    elapsed = pc.get_global_info()["global_run_time_s"]

    pc.reset()

    assert len(pc) == 0
    assert pc.profThread == {}
    assert pc.deep == [-1, -1]
    # the global timer is not a measurement: it keeps running
    assert pc.get_global_info()["global_run_time_s"] >= elapsed


def test_profiling_works_again_after_reset(pc):
    @profiler
    def work():
        return 1

    work()
    pc.reset()
    work()
    assert pc["work"]["nb_call"] == 1


# --- kill switch -------------------------------------------------------------

def test_env_var_strips_the_decorator(run_py):
    out = run_py(
        """
        from custom_profiler import profiler, magic_profiler
        from custom_profiler import profiler_collecteur as pc

        def raw():
            return 1

        decorated = profiler(raw)
        print("SAME", decorated is raw)

        with magic_profiler("block"):
            pass

        decorated()
        print("COLLECTED", len(pc))
        """,
        env={"CUSTOM_PROFILER": "0"},
    )
    assert "SAME True" in out
    assert "COLLECTED 0" in out


def test_the_env_var_also_silences_the_exit_summary(run_py):
    """"costs nothing in production" has to mean nothing on stdout either: the
    summary used to print anyway, corrupting the output of any program that
    merely imports the package."""
    out = run_py(
        """
        import custom_profiler
        print("--- end of program ---")
        """,
        env={"CUSTOM_PROFILER": "0"},
    )
    assert out.strip() == "--- end of program ---"


def test_without_the_env_var_the_summary_is_printed(run_py):
    out = run_py(
        """
        import custom_profiler
        print("--- end of program ---")
        """
    )
    assert "customProfiler log" in out.split("--- end of program ---")[1]


def test_env_var_absent_keeps_profiling(run_py):
    out = run_py(
        """
        from custom_profiler import profiler
        from custom_profiler import profiler_collecteur as pc

        @profiler
        def work():
            return 1

        work()
        print("COLLECTED", len(pc))
        """
    )
    assert "COLLECTED 1" in out


def test_off_records_nothing_at_runtime(pc):
    pc.interractivity = Interactivity.OFF

    @profiler
    def work():
        return 42

    with magic_profiler("block"):
        pass

    assert work() == 42
    assert len(pc) == 0


def test_off_can_be_turned_back_on(pc):
    @profiler
    def work():
        return 1

    pc.interractivity = Interactivity.OFF
    work()
    pc.interractivity = Interactivity.DISABLE
    work()
    assert pc["work"]["nb_call"] == 1


# --- deprecated spellings ----------------------------------------------------

def test_deprecated_data_keys_still_resolve(pc):
    pc.incr()
    pc.save("a", 1.0, 4096)

    data = pc["a"]
    with pytest.warns(DeprecationWarning, match="peack_memory"):
        assert data["peack_memory"] == data["peak_memory"]
    with pytest.warns(DeprecationWarning, match="peack_memory_b"):
        assert data["peack_memory_b"] == data["peak_memory_b"]


def test_deprecated_global_keys_still_resolve(pc):
    info = pc.get_global_info()
    with pytest.warns(DeprecationWarning, match="memory_peack"):
        assert info["memory_peack"] == info["memory_peak"]


def test_deprecated_module_paths_still_import(run_py):
    out = run_py(
        """
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from custom_profiler.custum_profiler import profiler, magic_profiler
            from custom_profiler.custum_logger import add_logging_level
        print("WARNED", sum(1 for w in caught
                            if issubclass(w.category, DeprecationWarning)))
        print("USABLE", callable(profiler), callable(add_logging_level))
        """
    )
    assert "WARNED 2" in out
    assert "USABLE True True" in out


def test_deprecated_thread_manager_alias():
    from custom_profiler import _profiler
    assert _profiler.thread_mananger is _profiler._ThreadManager


def test_the_shim_still_takes_the_0_3_positional_call():
    """0.3 spelled it profiler(func, linePerline); keyword-only would break that."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from custom_profiler.custum_profiler import profiler as legacy

    def raw():
        return 1

    assert legacy(raw, False)() == 1
    assert legacy(raw)() == 1


# --- what the profiler cannot measure ----------------------------------------

def test_decorating_a_coroutine_warns(pc):
    with pytest.warns(RuntimeWarning, match="coroutine function"):
        @profiler
        async def slow():
            pass


def test_decorating_a_generator_warns(pc):
    with pytest.warns(RuntimeWarning, match="generator function"):
        @profiler
        def gen():
            yield 1


def test_decorating_an_async_generator_warns(pc):
    with pytest.warns(RuntimeWarning, match="async generator function"):
        @profiler
        async def agen():
            yield 1


def test_the_named_form_warns_too(pc):
    with pytest.warns(RuntimeWarning, match="coroutine function"):
        @profiler(name="label")
        async def slow():
            pass


def test_the_line_decorator_warns_too(pc):
    with pytest.warns(RuntimeWarning, match="coroutine function"):
        @profiler_lbl
        async def slow():
            pass


def test_an_ordinary_function_does_not_warn(pc, recwarn):
    @profiler
    def plain():
        return 1

    plain()
    assert [w for w in recwarn if issubclass(w.category, RuntimeWarning)] == []


def test_the_warning_points_at_the_decoration_site(pc):
    with pytest.warns(RuntimeWarning) as caught:
        @profiler
        async def slow():
            pass

    assert caught[0].filename == __file__      # not inside custom_profiler/


def test_a_foreign_tracer_warns_and_reports_no_lines(pc, capsys):
    """Under coverage or a debugger we leave their tracer alone, so we see
    nothing -- which is worth saying out loud."""
    import sys
    sys.settrace(lambda frame, event, arg: None)
    try:
        @profiler_lbl
        def traced():
            return 1

        with pytest.warns(RuntimeWarning, match="another tracer is installed"):
            assert traced() == 1
    finally:
        sys.settrace(None)
    capsys.readouterr()

    assert "traced" in pc                       # its own timing is still there
    assert not [k for k in pc.keys() if " l " in k]


def test_a_recursive_line_profiled_call_does_not_warn(pc, capsys, recwarn):
    """Our own tracer is not "another tracer": the inner frame must stay quiet."""
    @profiler_lbl
    def rec(n):
        if n:
            rec(n - 1)
        return n

    rec(2)
    capsys.readouterr()
    assert [w for w in recwarn if "another tracer" in str(w.message)] == []
