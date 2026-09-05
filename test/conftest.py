"""Shared fixtures.

Two facts drive everything here:

* ``profiler_collecteur`` is a process-wide singleton whose state lives on the
  *class* (``__new__`` is declared ``def __new__(self)``), so a test that does
  not clean up poisons every following test -> ``reset_collecteur`` is autouse.
* a few features can only be exercised once per interpreter (``add_logging_level``
  raises if ``PROFILER`` already exists, ``sys.settrace``, ``atexit`` summaries,
  ``AUTO`` resolved at import time) -> those tests spawn a subprocess through
  the ``run_py`` fixture.
"""

import os
import subprocess
import sys
import textwrap
from collections import OrderedDict
from pathlib import Path

import pytest

from custom_profiler import profiler_collecteur
from custom_profiler.collecteur import (Interactivity, DEFAULT_REFRESH_S,
                                        DEFAULT_MAX_SAMPLES, DEFAULT_SUMMARY_TIME)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def reset_collecteur():
    """Give each test a pristine singleton, before *and* after it runs."""

    def _reset():
        profiler_collecteur.profData = OrderedDict()
        profiler_collecteur.profThread = OrderedDict()
        profiler_collecteur.deep = [-1, -1]
        profiler_collecteur.logger = None
        profiler_collecteur.forcePrintInCsl = False
        profiler_collecteur.noSummaryInLog = False
        profiler_collecteur._local.active = {}
        # options() sets these on the instance, shadowing the class default
        profiler_collecteur.refresh_interval = DEFAULT_REFRESH_S
        profiler_collecteur.max_samples = DEFAULT_MAX_SAMPLES
        profiler_collecteur.summary_time = DEFAULT_SUMMARY_TIME
        # never AUTO: the tests must not depend on pytest's capture mode
        profiler_collecteur.interractivity = Interactivity.MF_NO_INTERAC

    _reset()
    yield profiler_collecteur
    _reset()


@pytest.fixture
def pc(reset_collecteur):
    return reset_collecteur


def _env(extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTHONWARNINGS", None)
    if extra:  # last, so a test can override PYTHONIOENCODING
        env.update(extra)
    return env


@pytest.fixture
def run_py(tmp_path):
    """Run a snippet in a fresh interpreter and return its stdout.

    ``tty=True`` hands the child a pseudo-terminal, which is the only way to
    exercise the ``AUTO`` -> ``ENABLE`` branch of ``options()``.
    """

    counter = {"n": 0}

    def _run(code, tty=False, check=True, timeout=60, env=None):
        counter["n"] += 1
        script = tmp_path / f"snippet_{counter['n']}.py"
        # lstrip so that line N of the literal is line N of the script: the
        # line-by-line tests assert on real source line numbers.
        script.write_text(textwrap.dedent(code).lstrip("\n"), encoding="utf-8")
        cmd = [sys.executable, str(script)]

        if not tty:
            proc = subprocess.run(
                cmd, cwd=tmp_path, env=_env(env), timeout=timeout,
                # errors="replace": a snippet may deliberately run under another
                # console encoding, and cp1252 "µs" is not valid utf-8
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if check:
                assert proc.returncode == 0, proc.stderr
            return proc.stdout

        import pty

        master, slave = pty.openpty()
        proc = subprocess.Popen(
            cmd, cwd=tmp_path, env=_env(env),
            stdout=slave, stderr=subprocess.PIPE, close_fds=True,
        )
        os.close(slave)
        chunks = []
        try:
            while True:
                try:
                    data = os.read(master, 4096)
                except OSError:  # the child closed the pty
                    break
                if not data:
                    break
                chunks.append(data)
        finally:
            os.close(master)
        proc.wait(timeout=timeout)
        if check:
            assert proc.returncode == 0, proc.stderr.read().decode("utf-8", "replace")
        return b"".join(chunks).decode("utf-8", "replace")

    return _run


requires_pty = pytest.mark.skipif(
    sys.platform == "win32", reason="pty is POSIX only"
)
