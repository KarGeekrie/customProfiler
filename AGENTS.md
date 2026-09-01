# AGENTS.md — instructions for coding agents

Project: **custom_profiler** — a small, dependency-light (only `psutil`) time & memory
profiler for Python, published on PyPI as `custom-profiler` (author: Karim Ammar,
repo: https://github.com/KarGeekrie/customProfiler). MIT.

Read this file before touching code. It records what is *not* obvious from reading
the sources.

---

## 1. Map of the code

| File | Role |
|---|---|
| `custom_profiler/__init__.py` | Public API (`__all__`, `__version__`) + **side effects at import** (see §3). |
| `custom_profiler/collecteur.py` | Singleton `profiler_collecteur`: data store, all printing/formatting, the end-of-run summary, `options()` and the logger wiring. **The core of the project.** |
| `custom_profiler/_profiler.py` | `profiler` decorator, `magic_profiler` context manager, and the memory-watcher `Thread` (`task` / `_ThreadManager`). |
| `custom_profiler/line_by_line.py` | `sys.settrace`-based line-by-line tracer (`trace_calls` / `trace_lines`). |
| `custom_profiler/_logging.py` | `add_logging_level()` — adds the custom `PROFILER` level (level 25) to `logging`. |
| `custom_profiler/human_readable_time.py` | `human_time_duration()` (aliased `htd`) — fixed-width time strings. |
| `custom_profiler/custum_profiler.py`, `custum_logger.py` | Deprecating shims for the two renamed modules. Nothing new goes in them. |
| `test/` | Automated `pytest` suite (see §6). |
| `test/demo/` | Runnable snippets backing the README's output blocks — printed, not asserted; excluded from collection. |
| `pyproject.toml` | **The** packaging file (PEP 621, setuptools backend) — and the pytest config (`[tool.pytest.ini_options]`). |
| `MANIFEST.in` | Ships the test tree, LICENSE and CHANGELOG in the sdist — and prunes what setuptools-scm's file finder would otherwise add, the 557K demo gif above all. |
| `.github/workflows/tests.yml` | CI: pytest on 3.9→3.13 × Linux/macOS/Windows, plus a build + `twine check` job. |
| `utils/up_version.sh` | Tag + build + upload to PyPI. **Never run it.** |
| `README.md` | The only user documentation. Must stay in sync with the printed output. |
| `CHANGELOG.md` | What changed in 1.0, and the full deprecation table. |

Public API — everything users are allowed to import:

```python
from custom_profiler import (profiler, profiler_lbl, magic_profiler,
                             profiler_collecteur, Interactivity, __version__)
```

* `profiler` / `profiler_lbl` work bare (`@profiler`) or called (`@profiler(name="…")`).
* `profiler_collecteur` exported from `__init__` is an **instance**, not the class.
* `Interactivity` is a `str, Enum`: `ENABLE` / `MF_NO_INTERAC` / `DISABLE` / `AUTO` / `OFF`.
  `INTERACTIVITY_OPT_ENUM` is an alias of it.

---

## 2. The 1.0 deprecation contract

1.0 corrected the misspelled public names and kept **every** old spelling working.
That contract is the thing to protect:

* Old `options()` keywords (`interractivity`, `useLogger`, `loggername`,
  `addCustumLvl`, `profilerlvl`, `forcePrintInCsl`, `noSummaryInLog`) are accepted
  through `**legacy` in `options()` and raise `DeprecationWarning`.
* Old result keys (`peack_memory`, `peack_memory_b`, `memory_peack`,
  `memory_peack_b`) resolve through `_ProfData.__getitem__`, which warns. They are
  **not** stored in the dict, so `keys()` and `to_dict()` stay clean.
* `custom_profiler.custum_profiler` and `custum_logger` are shim modules that warn
  on import and re-export from `_profiler` / `_logging`.
* `INTERACTIVITY_OPT_ENUM`, `thread_mananger` are plain aliases.

None of this may be removed before 2.0. When you add a public name, add it to
`__all__` and to the CHANGELOG's table.

**Still deliberately spelled as they are**: `profiler`, `profiler_lbl`,
`magic_profiler`, `profiler_collecteur`, and the module `collecteur.py`. They are
in every README example, and `collecteur` is French, not a typo. The storage
attribute is still `profC.interractivity`; `interactivity` is a property alias on
top of it (making the misspelled one a property would break `__new__`, which
assigns it on the class).

Match the surrounding style: 4 spaces, no docstrings except where they already
exist, leading-comma multi-line argument lists, mixed FR/EN comments. Do not
reformat wholesale. Type hints go on the public API only — the tracer's hot path
stays as it is.

---

## 3. Behaviours that will bite you

* **Import has side effects.** `__init__.py` instantiates the singleton (which starts
  the global timer) and calls `options(interactivity=AUTO)`. `AUTO` resolves at that
  moment via `sys.stdout.isatty()` → `ENABLE` on a TTY, `MF_NO_INTERAC` when the
  output is redirected.
* **`profiler_collecteur` is a singleton with class-level state.** `__new__` is
  declared `def __new__(self)` — the first parameter is the *class*, so the shared
  attributes (`profData`, `profThread`, `start_time`, …) live on the class. There is
  one collector per process, by design.
* **Depth and re-entrancy are per thread**, held in `_local` (a `threading.local`)
  behind the `deep` and `_active` properties. Two threads calling the same profiled
  function are not nested inside one another. `profData` mutation is guarded by
  `_lock` (an `RLock`, because `save()` calls `print_line()`).
* **A recursive call is timed by its outermost frame only.** `incr(fname)` returns
  `False` for a re-entrant call; `save(..., outermost=False)` then bumps `nbCall`
  and nothing else — no time, no memory, no printed line. Without that, `fib(4)`
  counted the same seconds four times over.
* **`save(keep_deep=True)`** records an entry that is *not* a nesting level. The
  line-by-line tracer uses it: a traced line must not move the counter the
  enclosing function pushed.
* **`options()` only changes what you pass.** Every parameter defaults to `_UNSET`.
  Adding a parameter with a concrete default silently resurrects the old footgun.
* **`useLogger=True` downgrades `ENABLE` to `MF_NO_INTERAC`** — the interactive
  carriage-return line would corrupt a log file.
* **`add_logging_level('PROFILER', 25)` raises if the level already exists**, so
  `_enable_logger` guards with `hasattr(logging, self.lvl)`. Keep that guard:
  without it, calling `options(use_logger=True)` twice raises.
* **The summary comes from `atexit`**, registered once in `__new__`
  (`_report_at_exit`). Never move it back to `__del__`: at interpreter teardown the
  module globals it needs may already be gone.
* **The watcher thread** (`task` in `_profiler.py`) wakes every `POLL_S`, and both
  samples memory and repaints every `REFRESH_S` (one second) — **starting
  immediately**, not one `REFRESH_S` in. Delaying that first sample means a
  sub-second call is never sampled and its `peak` column reads `0.0B`; that was a
  regression, and `test_the_watcher_samples_before_the_first_refresh` pins it.
  The `peak` column is still only a 1 Hz sample after that — the README says so.
  Raising the rate is a real improvement, but it changes reported numbers, so it
  needs a decision first.
* **`profiler_lbl` starts no watcher thread**, so line-by-line mode has no memory-peak
  column (`peak`). The README says so; keep it true.
* **The line tracer keeps its state in `line_by_line.state`**, a `tracer_state`
  that subclasses `threading.local` — `sys.settrace` is installed per thread, so
  the state must be too, or two threads tracing at once lose one of them. Only the
  outermost frame is traced: `trace_calls` returns `None` for nested calls, so a
  Python callee does not clobber the trace.
* **Only the frame that installed the tracer removes it** (`sys.gettrace() is None`
  guards the install). A nested or recursive `@profiler_lbl` calling
  `sys.settrace(None)` under its caller left the state stuck and killed line
  tracing for the rest of the process. It also means `profiler_lbl` no longer
  clobbers a debugger's or coverage's tracer — it just reports nothing.
* **Never derive a statement's extent from the trace events.** CPython emits one
  `line` event per statement for a simple multi-line expression, and several
  out-of-order ones for a complex one — that mismatch is what used to swallow the
  rest of the function. `get_statement()` reads the continuation lines from the
  source instead (bracket counting on literal-stripped text, `\` continuation), and
  `trace_lines` ignores any event landing inside `[state.lineno, state.line_end]`.
  Exercise both with the `my_func2` sample in
  `python custom_profiler/line_by_line.py` (the `__main__` block) after any change.
* **`get_source()` caches `inspect.getsourcelines` per code object.** It used to run
  on every single line event, which dominated the tracer's own cost.
* **`bytes2human` is vendored** in `collecteur.py` (psutil's lives in the private
  `psutil._common`) and wrapped to render negative deltas. Use it — never
  `psutil._common` — for anything that can go negative.
* **Platform memory.** Windows reads `peak_wset`; everything else reads
  `ru_maxrss`, which is **kibibytes on Linux and bytes on macOS** — hence
  `RU_MAXRSS_UNIT`. Both halves were broken before 1.0.
* **`CUSTOM_PROFILER=0`** is read once, at import of `_profiler`, and makes the
  decorators return the function untouched. `Interactivity.OFF` is the runtime
  equivalent, checked at the top of the wrapper.

---

## 4. Output format is a contract

The README shows exact console output. Column widths, the ⚡ prefixes, the
`"="*108` rule, the `{fname: <45.45}` field, the `+---` / `-+--` depth markers built
from `profData[key]["deep"]`, and the nesting glyphs `┌─` / `├─` driven by
`deep = [current, previous]` are all reproduced there.

If you change any of that, **regenerate and update the corresponding README blocks in
the same commit** by running the matching script in `test/demo/`. Depth bookkeeping
is split across `incr()` (before the call) and `save()` (which decrements) — keep
them balanced.

Time strings come from `human_time_duration` and are fixed-width (11 chars + unit);
memory strings from `bytes2human`. Do not inline ad-hoc formatting.

---

## 5. Performance

This is a profiler: overhead is the product. The hot paths are
`_wrap.wrapper`, `magic_profiler.__enter__/__exit__`, `task`'s loop and
`trace_lines`. Do not add I/O, imports, allocations or string work there. Timing must
stay `time.perf_counter()`; memory must stay `process.memory_info().rss` on the module
level `process = psutil.Process()` object (never re-create it per call).

---

## 6. Running things

The system `python3` has **no `psutil`**. Use a venv:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest                      # ~7 s, 153 tests
pytest -m "not slow"        # in-process only, no subprocesses
```

Suite layout (`test/`):

| File | Covers |
|---|---|
| `conftest.py` | `reset_collecteur` (autouse) and `run_py` — see below. |
| `test_human_time.py` | Unit selection, the 13-char fixed width, boundaries, the `0` quirk. |
| `test_bytes2human.py` | Negative deltas, sign-free zero, parity with psutil, the enum. |
| `test_collecteur_api.py` | `save`/`__getitem__`/`get_global_info`/`thread_view` — the README's data contract. |
| `test_output_format.py` | Column widths, `peak` column, tree glyphs, depth markers, logger vs stdout routing. |
| `test_profiler_decorator.py` | `@profiler`, `magic_profiler`, nesting, watcher-thread lifecycle, raising calls. |
| `test_concurrency.py` | Threads and recursion: the two shapes a single global counter got wrong. |
| `test_public_api.py` | `__all__`, mapping interface, `reset`/`to_dict`, named decorators, kill switch, every deprecated spelling. |
| `test_options.py` | Enum validation, partial calls, legacy keywords, `AUTO` on and off a tty. |
| `test_line_by_line.py` | `@profiler_lbl` output, source line numbers, no peak column. |
| `test_logger.py` | `PROFILER` vs `INFO`, `atexit` summary, `no_summary_in_log`, `force_print_in_console`. |

Rules the suite is built on — respect them when adding tests:

* **`reset_collecteur` is autouse** and wipes the singleton before *and* after each
  test. Never leave state (or a leaked watcher thread) behind; if a test cannot help
  it, run it out-of-process.
* **`run_py(code, tty=False, env=None)`** runs a snippet in a fresh interpreter and
  returns its stdout. Use it for anything that can only happen once per process
  (`add_logging_level`, `sys.settrace`, the `atexit` summary, `AUTO` and
  `CUSTOM_PROFILER` resolved at import) or that needs a real terminal (`tty=True`,
  via `pty`). It dedents *and* left-strips the snippet, so **line N of the literal is
  line N of the script** — the line-by-line tests assert on real source line numbers.
* Keep sleeps at ~0.02 s, and **never assert against the nominal sleep, however
  generous the tolerance**: a loaded macOS runner turned `sleep(0.02)` into 0.07.
  Bracket it with the two things that are true on any machine: `recorded <= wall`
  for a wall clock measured around the calls, and `recorded >= n * SLEEP * 0.95`
  because `time.sleep` never returns early. A *fraction* of the window is not a
  valid lower bound either — the profiler's own overhead was 55% of it on one
  macOS runner, and that test went red on main.
* A bug worth fixing later gets an `xfail(strict=True)` test, not a comment. Strict
  means it turns into a failure the day someone fixes it.

The demo scripts regenerate the README output:

```bash
python test/demo/prof_function.py     # @profiler, repeated calls
python test/demo/prof_cm.py           # magic_profiler, nesting
python test/demo/prof_lbl.py          # @profiler_lbl
python test/demo/demo_get.py          # data access API
python test/demo/demo_logger.py       # logger; ONE case per process (see §3)
python custom_profiler/line_by_line.py         # tracer edge cases
python custom_profiler/human_readable_time.py  # formatting table
```

Run them interactively (a TTY) *and* redirected (`> out.txt`) when you touch printing,
interactivity or the summary — `AUTO` takes a different branch in each case.

---

## 7. Repo hygiene

* **The version is the git tag.** `pyproject.toml` declares `dynamic = ["version"]`
  and setuptools-scm derives it, so there is no number to bump in any file — between
  releases you get `0.3.1.dev13+g1782fb9`. `utils/up_version.sh X.Y.Z` creates the
  tag and publishes. Never tag, publish, or run that script.
* Anything that builds the package needs the **tags and full history**: that is why
  CI checks out with `fetch-depth: 0`. A shallow clone silently produces a dev
  version.
* There is **no `setup.py` and no `setup.cfg`** — do not add one back. Build with
  `python -m build`; `pip install -e ".[test]"` is the dev install.
* Every user-visible change needs a `CHANGELOG.md` entry.
* Never commit `custom_profiler/__pycache__/` or the `*.log` / `demologger.txt` files
  the demos produce.
* Imports inside the package are **absolute** (`from custom_profiler.collecteur import …`).
  Keep that style.
* `custum_profiler.py` is the one file in the repo with CRLF line endings. Preserve
  them; normalising rewrites its whole `git blame`.
* Commit messages in this repo are short and lowercase (`up doc ...`, `fix ... bug`).
  Match it. Commit or push only when asked.
* `gif/demoProf.gif` is the README demo; regenerate it only on request.

---

## 8. Known limitations, on purpose

Documented in the README's *Limitations* section, not bugs to fix by surprise:

* Memory is process RSS, so it is only meaningful single-threaded, and a `del` may
  show no drop because the allocator keeps the pages.
* The `peak` column is sampled at 1 Hz (see §3).
* `sys.settrace` means `profiler_lbl` cannot coexist with a debugger or `coverage`,
  and it follows only the decorated function.
* No async and no generator support. Both are real gaps; both need their semantics
  decided before any code.
