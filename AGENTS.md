# AGENTS.md — instructions for coding agents

Project: **custom_profiler** — a small, dependency-light (only `psutil`) time & memory
profiler for Python, published on PyPI as `custom-profiler` (author: Karim Ammar,
repo: https://github.com/KarGeekrie/customProfiler).

Read this file before touching code. It records what is *not* obvious from reading
the sources.

---

## 1. Map of the code

| File | Role |
|---|---|
| `custom_profiler/__init__.py` | Public API + **side effects at import** (see §3). |
| `custom_profiler/collecteur.py` | Singleton `profiler_collecteur`: data store, all printing/formatting, the end-of-run summary, `options()` and the logger wiring. **The core of the project.** |
| `custom_profiler/custum_profiler.py` | `profiler` decorator, `magic_profiler` context manager, and the memory-watcher `Thread` (`task` / `thread_mananger`). |
| `custom_profiler/line_by_line.py` | `sys.settrace`-based line-by-line tracer (`trace_calls` / `trace_lines`). |
| `custom_profiler/custum_logger.py` | `add_logging_level()` — adds the custom `PROFILER` level (level 25) to `logging`. |
| `custom_profiler/human_readable_time.py` | `human_time_duration()` (aliased `htd`) — fixed-width time strings. |
| `test/` | Automated `pytest` suite (see §6). |
| `test/demo/` | Runnable snippets backing the README's output blocks — printed, not asserted; excluded from collection. |
| `pytest.ini` | Test config: `testpaths=test`, `test/demo` excluded, `slow` marker. |
| `utils/up_version.sh` | Tag + build + upload to PyPI. **Never run it.** |
| `README.md` | The only user documentation. Must stay in sync with the printed output. |

Public API (everything users are allowed to import):

```python
from custom_profiler import profiler, profiler_lbl, magic_profiler, \
                            profiler_collecteur, INTERACTIVITY_OPT_ENUM
```

* `profiler` / `profiler_lbl` are `functools.partial(custum_profiler.profiler, linePerline=False/True)`.
* `profiler_collecteur` exported from `__init__` is an **instance**, not the class.
* `INTERACTIVITY_OPT_ENUM`: `ENABLE` / `MF_NO_INTERAC` / `DISABLE` / `AUTO`.

---

## 2. Hard rule: do not "fix" the spelling of the public API

The codebase is full of deliberate/legacy misspellings that are **part of the shipped
API** and of the module paths on PyPI. Renaming them is a breaking change for every
user, and is out of scope unless the maintainer explicitly asks for a major version.

Keep as-is, everywhere:

`custum_profiler`, `custum_logger`, `collecteur`, `profiler_collecteur`,
`interractivity`, `INTERACTIVITY_OPT_ENUM`, `MF_NO_INTERAC`, `addCustumLvl`,
`loggername`, `forcePrintInCsl`, `noSummaryInLog`, `peack_memory`, `peack_memory_b`,
`memory_peack`, `memory_peack_b`, `thread_mananger`, `mem_peack_b`, `linePerline`.

The same applies to the returned dict keys of `profiler_collecteur[...]` and of
`get_global_info()` — they are documented in the README and consumed by users.

Do not do repo-wide reformatting, do not add type hints, do not convert
`INTERACTIVITY_OPT_ENUM` to `enum.Enum`, do not restyle comments. Match the
surrounding style: 4 spaces, no docstrings except where they already exist,
leading-comma multi-line argument lists, mixed FR/EN comments.

---

## 3. Behaviours that will bite you

* **Import has side effects.** `__init__.py` instantiates the singleton (which starts
  the global timer) and calls `options(interractivity=AUTO)`. `AUTO` resolves at that
  moment via `sys.stdout.isatty()` → `ENABLE` on a TTY, `MF_NO_INTERAC` when the
  output is redirected.
* **`profiler_collecteur` is a singleton with class-level state.** `__new__` is
  declared `def __new__(self)` — the first parameter is the *class*, so all attributes
  (`profData`, `profThread`, `start_time`, `deep`, …) live on the class. There is one
  shared collector per process, by design.
* **`options()` resets what you don't pass.** Every keyword has a default, so calling
  `options(useLogger=True)` also silently resets `interractivity` to `AUTO`,
  `forcePrintInCsl` to `False`, etc. Callers must pass the whole set (the README
  examples do).
* **`useLogger=True` downgrades `ENABLE` to `MF_NO_INTERAC`** — the interactive
  carriage-return line would corrupt a log file.
* **Two different end-of-run summary paths.** Without a logger, the summary is printed
  from `profiler_collecteur.__del__`. With a logger, it is emitted from an
  `atexit`-registered callback. Interpreter-shutdown ordering makes both fragile:
  if you change the summary, test both paths and both console/file cases.
* **`add_logging_level('PROFILER', 25)` raises `AttributeError` if already defined.**
  Consequence: `options(useLogger=True, addCustumLvl=True)` can only be called once per
  process. This is why `test/demo/demo_logger.py` runs one case per process and why
  `test/test_logger.py` drives each case through `run_py` (§6).
* **The watcher thread** (`task` in `custum_profiler.py`) polls every 10 ms and prints
  only when `i % 100 == True` — i.e. `== 1`, since `True == 1`. That is once per second,
  intentionally rare. Leave it alone unless you are changing the refresh rate on
  purpose; it is not a typo to be "cleaned up".
* **`profiler_lbl` starts no watcher thread**, so line-by-line mode has no memory-peak
  column (`peak`). The README says so; keep it true.
* **The line tracer keeps its state in `line_by_line.state`**, a module-level
  `tracer_state` holding the frame being traced, the pending statement and its
  start/end line. Only the outermost frame is traced: `trace_calls` returns `None`
  for nested calls, so a Python callee does not clobber the trace.
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
* **`bytes2human` is redefined in `collecteur.py`** to handle negative deltas (it wraps
  `psutil._common.bytes2human` and prepends `-`). `custum_profiler.py` imports the
  *psutil* one directly, which cannot render negatives. Use the collector's version
  for anything that can go negative.
* **Platform support.** `import resource` is guarded by `sys.platform == 'linux'`, but
  `get_global_info()` uses it on every non-`win32` platform → `NameError` on macOS.
  Known limitation; only touch it if the task is about platform support.

---

## 4. Output format is a contract

The README shows exact console output. Column widths, the ⚡ prefixes, the
`"="*108` rule, the `{fname: <45.45}` field, the `+---` / `-+--` depth markers built
from `profData[key]["deep"]`, and the nesting glyphs `┌─` / `├─` driven by
`self.deep = [current, previous]` are all reproduced there.

If you change any of that, **regenerate and update the corresponding README blocks in
the same commit.** Depth bookkeeping is split across `incr()` (before the call) and
`save()` (which decrements) — keep them balanced.

Time strings come from `human_time_duration` and are fixed-width (11 chars + unit);
memory strings from `bytes2human`. Do not inline ad-hoc formatting.

---

## 5. Performance

This is a profiler: overhead is the product. The hot paths are
`profiler.wrapper`, `magic_profiler.__enter__/__exit__`, `task`'s loop and
`trace_lines`. Do not add I/O, imports, allocations or string work there. Timing must
stay `time.perf_counter()`; memory must stay `process.memory_info().rss` on the module
level `process = psutil.Process()` object (never re-create it per call).

---

## 6. Running things

The system `python3` has **no `psutil`**. Use a venv:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest                      # ~4 s, 97 passed / 6 xfailed
pytest -m "not slow"        # in-process only, no subprocesses
```

Suite layout (`test/`):

| File | Covers |
|---|---|
| `conftest.py` | `reset_collecteur` (autouse) and `run_py` — see below. |
| `test_human_time.py` | Unit selection, the 13-char fixed width, boundaries, the `0` quirk. |
| `test_bytes2human.py` | Negative deltas, sign-free zero, parity with psutil. |
| `test_collecteur_api.py` | `save`/`__getitem__`/`get_global_info`/`thread_view` — the README's data contract. |
| `test_output_format.py` | Column widths, `peak` column, tree glyphs, depth markers, logger vs stdout routing. |
| `test_profiler_decorator.py` | `@profiler`, `magic_profiler`, nesting, watcher-thread lifecycle, raising calls. |
| `test_options.py` | Enum validation, the reset-on-partial-call gotcha, `AUTO` on and off a tty. |
| `test_line_by_line.py` | `@profiler_lbl` output, source line numbers, no peak column. |
| `test_logger.py` | `PROFILER` vs `INFO`, `atexit` summary, `noSummaryInLog`, `forcePrintInCsl`. |

Two rules the suite is built on — respect them when adding tests:

* **`reset_collecteur` is autouse** and wipes the singleton before *and* after each
  test. Never leave state (or a leaked watcher thread) behind; if a test cannot help
  it, run it out-of-process.
* **`run_py(code, tty=False)`** runs a snippet in a fresh interpreter and returns its
  stdout. Use it for anything that can only happen once per process
  (`add_logging_level`, `sys.settrace`, the `atexit`/`__del__` summary, `AUTO`
  resolved at import) or that needs a real terminal (`tty=True`, via `pty`).
  It dedents *and* left-strips the snippet, so **line N of the literal is line N of
  the script** — the line-by-line tests assert on real source line numbers.
* Keep sleeps at ~0.02 s and assert timings with a generous `pytest.approx(abs=0.15)`.
  Nothing in the suite may depend on wall-clock precision.

**Six tests are `xfail(strict=True)`** — they pin known bugs (see §8). `strict` means
they turn into failures the day someone fixes the bug: that is the signal to delete
the marker, not to delete the test.

The demo scripts are unchanged and still regenerate the README output:

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

## 7. Repo hygiene

* Version lives in **`setup.py` only** (`0.3.0`). Bumping it is what drives
  `utils/up_version.sh` (git tag + PyPI upload). Never tag, publish, or run that script.
* Never commit `custom_profiler/__pycache__/` or the `*.log` / `demologger.txt` files
  the demos produce.
* Imports inside the package are **absolute** (`from custom_profiler.collecteur import …`).
  Keep that style.
* Commit messages in this repo are short and lowercase (`up doc ...`, `fix ... bug`,
  `improvement logger`). Match it. Commit or push only when asked.
* `gif/demoProf.gif` is the README demo; regenerate it only on request.

---

## 8. Bug history pinned by the test suite

Six bugs were fixed on `fix/known-bugs-and-pyproject`; each keeps a regression test.
Do not reintroduce them:

1. **`human_time_duration` >= 1 h with a float** rendered as
   `'2.0h2.0min5.399999999999636s'` (28 chars instead of 12). The branch now formats
   with `{h:3.0f}` — real `perf_counter()` deltas are always floats.
   → `test_human_time.py::test_hours_branch_with_float_input`
2. **A raising call was never recorded** — `profiler.wrapper` now closes over a
   `try/finally`.
   → `test_profiler_decorator.py::test_raising_call_is_still_recorded`
3. **`deep[0]` drifted after an exception**, indenting every later line one level too
   deep, permanently. Same `try/finally`.
   → `test_profiler_decorator.py::test_depth_is_restored_when_the_call_raises`
4. **The watcher thread leaked after an exception** (`tm.end()` was skipped) and kept
   writing into `profThread` for the rest of the process. Same `try/finally`, plus
   `useThread` is now latched at entry instead of re-tested at exit.
   → `test_profiler_decorator.py::test_watcher_thread_is_not_leaked_when_the_call_raises`
5. **Line labels drifted** — they came from the *next* trace event minus one, so a
   comment or blank line shifted every following number. Each statement now carries
   its own `f_lineno`.
   → `test_line_by_line.py::test_line_numbers_survive_a_comment_in_the_body`
6. **A multi-line statement swallowed the rest of the function** — see §3.
   → `test_line_by_line.py::test_multiline_statement_does_not_swallow_the_rest`

**Still open**, deliberately (`xfail(strict=True)`):

* **Line mode leaves `profC.deep` far below its baseline** — every per-line `save()`
  decrements the counter without a matching `incr()`, so `deep[0]` ends at `-4` after
  a 3-line function and anything profiled afterwards is mis-indented. Any fix changes
  the depth markers the README's line-by-line summary shows (`----` would become
  `+---`), so it needs a maintainer decision, not a silent patch.
  → `test_line_by_line.py::test_line_mode_leaves_the_depth_counter_alone`
* **`get_global_info()` raises `NameError` on macOS** — see §3.
