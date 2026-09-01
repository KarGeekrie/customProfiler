# Changelog

## 1.0.0

First stable release. Every 0.3 name still works; the misspelled ones now raise
`DeprecationWarning` and are scheduled for removal in 2.0.

### Fixed

* **macOS was broken twice over.** `resource` was only imported on Linux, so
  `get_global_info()` raised `NameError` on Darwin; and `ru_maxrss` is in bytes
  there, not kibibytes, so the ×1024 made every macOS figure 1024 times too big.
* **Threads were reported as a call tree that never existed.** Nesting depth was
  one process-wide counter, so four threads each calling one profiled function
  were recorded at depths 3, 2, 1 and 0. Depth and re-entrancy are now per
  thread, and the collector is guarded by a lock.
* **Recursion counted the same seconds several times.** `fib(4)` summed the
  duration of all nine frames. A recursive call is now timed by its outermost
  frame only; `nb_call` still counts every entry.
* **A raising call was lost**, left the depth counter one level too deep for the
  rest of the run, and leaked its watcher thread.
* **Line-by-line labels drifted**: they came from the next trace event minus one,
  so a comment inside the body shifted every following number.
* **A parenthesised multi-line statement swallowed the rest of the function**,
  because bracket counting relied on trace events CPython does not emit
  consistently. Continuation lines are now read from the source.
* **`human_time_duration()` broke the column alignment past one hour**, rendering
  a float as `2.0h2.0min5.399999999999636s`.
* **Per-line `save()` unbalanced the depth counter**, leaving it at `-4` after a
  three-line function and mis-indenting everything profiled afterwards.
* The summary now comes from `atexit` in every case, never `__del__`.
* **Printing no longer raises on a console that cannot represent ⚡** (cp1252,
  the Windows default): the character degrades to a replacement, one per
  character, so the columns stay aligned.
* Nested Python calls are no longer traced in line mode, and `exception` events
  no longer close a statement (a `try`/`except` in the body double-counted).
* **A recursive or nested `@profiler_lbl` used to kill line tracing for the whole
  process**: the inner frame switched the tracer off under its caller, leaving the
  state stuck so every later call reported no lines at all. Only the frame that
  installed the tracer removes it now.
* **Two threads running `@profiler_lbl` at once lost one of them.** `sys.settrace`
  is per thread, so the tracer state is too.
* A failure while starting the watcher thread no longer leaves the function marked
  as running, which would have made every later call look re-entrant and go
  untimed.

### Added

* `__all__`, `__version__`, and `functools.partial` no longer leaks into the
  package namespace.
* The collector is a mapping: `len()`, iteration, `in`, `keys()`, `items()`,
  `values()`, plus `to_dict()` and `reset()`.
* `@profiler(name="my label")` and `@profiler_lbl(name=...)`, alongside the bare
  form.
* `Interactivity.OFF` and the `CUSTOM_PROFILER=0` environment variable: a true
  no-op, so profiled code costs nothing in production.
* `py.typed` and type hints on the public API.
* `per_call_memory_b`, the per-call memory list.
* A test suite (`pytest`), and CI on Linux, macOS and Windows.

### Changed

* `options()` only changes what you pass it. It used to reset every option you
  omitted, because each keyword had a concrete default.
* Configuring the logger twice no longer raises `AttributeError`.
* `Interactivity` is a `str` `Enum`, so `== "ENABLE"` still holds.
* `max_memory_b` is now the maximum, in bytes, like every other `_b` key. The
  per-call list moved to `per_call_memory_b`. **This is the one change that can
  break code silently-ish** — `max(data["max_memory_b"])` now raises `TypeError`.
* The printed banner says `memory peak`.
* The logger examples pass `encoding="utf-8"` to `logging.basicConfig`: with the
  platform default on Windows the ⚡ comes out as `\u26a1`, and a hand-built
  `FileHandler` drops those records outright.
* The line-by-line summary shows `+---` depth markers where it used to show
  `----`, now that the counter stays balanced.
* Minimum Python is 3.9 (0.3 claimed 3.6, which was never tested).
* The version is derived from the git tag by setuptools-scm (`dynamic = ["version"]`),
  so there is no number to bump in a file. `utils/up_version.sh` takes it as an
  argument now.

### Deprecated

Still working, warns, removed in 2.0:

| 0.3 | 1.0 |
|---|---|
| `options(interractivity=…)` | `options(interactivity=…)` |
| `options(useLogger=…)` | `options(use_logger=…)` |
| `options(loggername=…)` | `options(logger_name=…)` |
| `options(addCustumLvl=…)` | `options(add_custom_level=…)` |
| `options(profilerlvl=…)` | `options(profiler_level=…)` |
| `options(forcePrintInCsl=…)` | `options(force_print_in_console=…)` |
| `options(noSummaryInLog=…)` | `options(no_summary_in_log=…)` |
| `data["peack_memory"]`, `data["peack_memory_b"]` | `data["peak_memory"]`, `data["peak_memory_b"]` |
| `info["memory_peack"]`, `info["memory_peack_b"]` | `info["memory_peak"]`, `info["memory_peak_b"]` |
| `custom_profiler.custum_profiler` | `custom_profiler._profiler` |
| `custom_profiler.custum_logger` | `custom_profiler._logging` |
| `thread_mananger` | `_ThreadManager` |
| `INTERACTIVITY_OPT_ENUM` | `Interactivity` |

`profiler`, `profiler_lbl`, `magic_profiler` and `profiler_collecteur` are
unchanged: they are the names in every example, and they are spelled correctly —
`collecteur` is French, not a typo.

## 0.3.0 and earlier

See the git history.
