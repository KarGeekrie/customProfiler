# dolist

Tracked work for `custom_profiler`, ordered by priority.
Status: `[ ]` todo · `[~]` in progress · `[x]` done

---

## P0 — Correctness

These produce **wrong numbers without any warning**, which is the worst failure
mode for an instrumentation tool: the value looks plausible and gets trusted.

### [ ] 1. `async def` and generator functions are not measured

`_profiler._wrap` is a synchronous wrapper. Calling `func(*args, **kwargs)` on a
coroutine function returns the coroutine object immediately, so the `finally`
block runs before the body has executed. Same for any function containing
`yield`: the generator object comes back untouched.

Measured on 1.0.0:

```
⚡ slow_async   | takes : 1.91µs     ← body is `await asyncio.sleep(2)`
⚡ gen          | takes : 1.88µs     ← generator that sleeps 1.5s in total
```

The decorated function still behaves correctly; only the measurement is wrong.

**Where:** `custom_profiler/_profiler.py` → `_wrap()`, `magic_profiler`

**Plan:** branch in `_wrap` on `inspect.iscoroutinefunction` /
`inspect.isasyncgenfunction` / `inspect.isgeneratorfunction` and return the
matching wrapper flavour. Add `__aenter__` / `__aexit__` to `magic_profiler`.

Design points to settle first:
- Wall time across an `await` includes time yielded to the event loop. That is
  the right default for "how long did this step take", but it must be stated in
  the docs, because two concurrent coroutines will each report the full
  wall-clock span and the totals will exceed the run time.
- Nesting depth (`profC.deep`) is `threading.local`. Under asyncio, many tasks
  share one thread, so the tree indentation will interleave. `contextvars`
  instead of `threading.local` fixes this; scope it with the async work.
- For a generator, decide what one "call" means: the whole consumption
  (`__enter__` at first `next()`, `__exit__` at `StopIteration`) is the useful
  answer, not the time of each `next()`.

**Fallback if the above is too large for 1.1:** detect the callable type at
decoration time and raise `TypeError` with a clear message. A loud refusal beats
a silent 1.91µs.

**Acceptance:** a test that decorates a coroutine sleeping 0.2s and asserts
`global_time_s > 0.15`; same for a generator; same for an async generator.

---

### [ ] 2. Name collisions: `__name__` instead of `__qualname__`

`profiler()` builds the key as `name or fct.__name__`. Two methods called `run()`
in two different classes merge into a single collector entry.

Measured on 1.0.0:

```
⚡ run | nb_call=2 | 1.00s     ← A.run() (0.3s) + B.run() (0.7s), silently merged
```

**Where:** `custom_profiler/_profiler.py` → `profiler()`, the `decorate` closure

**Plan:** default to `fct.__qualname__` (`A.run`, `B.run`). Keep `name=` as the
override for a shorter label. Column width is 40 chars in `__str__` and 45 in
`print_line`, so long qualnames will truncate — check the truncation reads
sensibly, or truncate from the left so the method name survives.

**Note:** this changes the keys in `profiler_collecteur[...]`, so it is a
breaking change for anyone reading data programmatically. Either ship it in 2.0,
or ship it in 1.1 behind a `qualname=True` option defaulting to `False` and flip
the default in 2.0.

**Acceptance:** two same-named methods in different classes produce two entries.

---

## P1 — Data model and workflow

### [ ] 3. Keep per-call times, not just the total

`save()` accumulates `dt` as a scalar but keeps `dm_list` as a list. The
asymmetry means memory has per-call detail and time does not, so the summary can
only offer a mean. Over a few thousand calls the mean hides exactly the tail you
are looking for.

**Where:** `custom_profiler/collecteur.py` → `save()`, `__getitem__()`, `__str__()`

**Plan:** add `dt_list` alongside `dm_list`. Expose `per_call_time_s`,
`max_time` / `max_time_s`, `median_time_s`, `p95_time_s` in `__getitem__`.
Keep `dt` as the running sum so `global_time` stays O(1).

**Memory cost:** one float per call. A function called 10M times in a long batch
would hold ~80MB. Add a cap (`max_samples`, default e.g. 100k, keep a reservoir
sample or just the running max beyond it) so a profiler cannot become the memory
problem it is meant to diagnose. This applies to `dm_list` too, which has the
same unbounded growth today.

**Acceptance:** `max_time_s` on a function called with 0.1s / 0.5s / 0.1s
returns ~0.5.

---

### [ ] 4. Log threshold

Today the only volume control is all-or-nothing (`CUSTOM_PROFILER=0`,
`Interactivity.OFF`). To leave decorators on in production you want the three
slow calls, not ten thousand lines.

**Plan:** `@profiler(min_time=0.5)` and/or a global
`pc.options(min_time=..., min_memory=...)`. The call is still recorded in the
collector and still appears in the end-of-run summary; only the per-call line is
suppressed. That distinction matters — dropping the record entirely would make
`nb_call` and the totals wrong.

**Where:** `collecteur.save()`, around the `self.print_line(...)` call

**Acceptance:** a 0.01s call with `min_time=0.5` prints nothing but still shows
up in the summary with the right `nb_call`.

---

### [ ] 5. Baseline comparison

`to_dict()` already produces the whole payload, so this is a small addition on
top of an API that exists. It is also the one thing here that `cProfile`,
`py-spy` and Scalene do not do: they answer "where is the time going right now",
not "has this batch got slower since last month".

**Plan:**
- `pc.dump(path)` — `json.dump(self.to_dict(), ...)` plus a schema version field
  and a timestamp.
- `pc.compare(path)` — load a previous dump, print the summary with a delta
  column, flag entries above a tolerance.
- New / disappeared functions must be handled explicitly rather than skipped:
  a function that vanished from the run is often the interesting signal.

```
⚡ +--- load_data | 3 | 4.15s / 12.44s | +18.2% vs baseline ⚠
⚡ +--- transform | 1 | 0.31s /  0.31s |  -2.1% vs baseline
⚡ +--- new_step  | 1 | 1.02s /  1.02s |  (not in baseline)
```

- `compare()` should return a non-zero-ish result object (or offer
  `fail_over=0.2`) so CI can gate on it. That is the use case that makes the
  feature worth having.

**Acceptance:** dump, re-run with an artificially slowed function, compare
reports a positive delta on that function only.

---

## P2 — Smaller items

### [ ] 6. Tag the PID under `multiprocessing`

Each worker gets its own singleton and its own `atexit` summary, so pooled runs
interleave several unrelated tables on stdout with nothing to tell them apart.
Minimum: put the PID in the summary header. Better: an opt-in merge helper for
the parent process.

### [ ] 7. Make the sampling interval configurable

`REFRESH_S = 1.` is hard-coded in `_profiler.py`. The README already documents
that a spike inside a fast function can be missed; letting the user pass
`pc.options(refresh_s=0.05)` turns a documented limitation into a trade-off they
control. Note the cost in the docstring: more samples means more `memory_info()`
syscalls.

### [ ] 8. `reset()` only clears the calling thread's state

`reset()` empties `profData` / `profThread` under the lock, but resets
`self._local.deep` and `self._local.active` for the calling thread only. Other
live threads keep their depth counters, so indentation after a reset can be
wrong. Either document it as "call from a quiescent state" or version the
thread-local block so stale state is discarded on next access.

### [ ] 9. `__new__(self)` sets class attributes

`profiler_collecteur.__new__` takes the class as `self` and assigns `profData`,
`_local`, `_lock` and the rest onto it, so the state lives on the class rather
than the instance. Harmless while the singleton holds, but any subclass would
share the parent's data. Rename the parameter to `cls` and move the
initialisation to `__init__` guarded by an `_initialised` flag, or keep the
current behaviour and write a comment saying it is deliberate.

---

## Documentation

### [ ] 10. Fix the inverted sentence in "Access to profiler data"

> You **cannot** access profiler data by requesting it from
> `profiler_collecteur["my_function_name"]`.

Should be **can**. The paragraph then lists the available fields, so the section
currently contradicts itself in its first line.

### [ ] 11. Document the public API that exists but is not in the README

None of these appear anywhere in the README today:

- `@profiler(name="...")` and `@profiler_lbl(name="...")` — the label override
- `pc.to_dict()` — the export path, and the basis of item 5
- `pc.reset()` — profiling a run in phases
- The mapping interface: `keys()`, `items()`, `values()`, `len(pc)`, `in`,
  iteration. Worth a three-line example; right now a reader assumes
  `pc["name"]` is the only way in.
- `custom_profiler.__version__`
- `py.typed` — the package ships type hints and is classified `Typing :: Typed`
  on PyPI; say so, it is a real selling point for the target audience.
- `requires-python = ">=3.9"`

### [ ] 12. Language pass on the README

- `## Profil function` → `## Profile a function`; same for the other headings
- `## Profil row code` → `## Profile raw code` (three occurrences of "row" for
  "raw", including the `## Row profiler:` heading at the bottom)
- `For devellopeur` → `For developers`
- `offert` → `offers`, in the Options section

### [ ] 13. Add a "when to use this" section near the top

The README explains *how* to use the tool but never *why this one*. The honest
positioning is the strongest pitch and takes a short paragraph: this is durable
instrumentation you leave in the code and read in your logs, not a diagnostic
profiler you run in a session. Use `cProfile` + snakeviz or `py-spy` to find a
hotspot; use this to keep watching it. `tracemalloc` or `memray` when you need
real allocation data rather than RSS; `timeit` for microbenchmarks.

Naming the alternatives builds more trust than avoiding them, and it stops
people arriving with the wrong expectation and leaving disappointed.

### [ ] 14. Migration note for 0.3 → 1.0

The CHANGELOG covers the renames well, but someone upgrading reads the README
first. A short table would do: `peack_memory` → `peak_memory`, `memory_peack` →
`memory_peak`, `interractivity` → `interactivity`, `useLogger` → `use_logger`,
`INTERACTIVITY_OPT_ENUM` → `Interactivity`, `thread_mananger` → `_ThreadManager`,
all still working with a `DeprecationWarning` and scheduled for removal in 2.0.

### [ ] 15. Add badges

PyPI version, supported Python versions, CI status (`.github/workflows/tests.yml`
exists and is not surfaced), licence. Cheap, and they answer "is this alive"
before anyone reads a line.

### [ ] 16. Limitations section: add the async caveat

Until item 1 lands, the Limitations section must say that `async def` and
generator functions are not measured correctly. It is currently the only
documented-nowhere failure, and that section is otherwise the most trustworthy
part of the README — it is worth keeping it complete.

Once item 1 lands, replace it with the concurrency note: under asyncio, wall
time across an `await` includes time spent yielded to the loop, so concurrent
tasks each report the full span and the sum will exceed the run time.

### [ ] 17. Document the sampling interval where it bites

The Limitations section says the peak is sampled once per second. Worth adding
the practical consequence: for anything under ~2s, treat the `peak` column as
indicative and trust only `Δ`.