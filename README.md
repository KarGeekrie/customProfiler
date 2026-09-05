# ⚡ custom_profiler ⚡

[![PyPI](https://img.shields.io/pypi/v/custom-profiler)](https://pypi.org/project/custom-profiler/)
[![Python](https://img.shields.io/pypi/pyversions/custom-profiler)](https://pypi.org/project/custom-profiler/)
[![tests](https://github.com/KarGeekrie/customProfiler/actions/workflows/tests.yml/badge.svg)](https://github.com/KarGeekrie/customProfiler/actions/workflows/tests.yml)
[![License](https://img.shields.io/pypi/l/custom-profiler)](https://github.com/KarGeekrie/customProfiler/blob/main/LICENSE)

**custom_profiler** is a simple, interactive and lightweight (the only dependency is psutil) way of profiling the memory and execution time of your python code.

<p align="center"><img src="https://raw.githubusercontent.com/KarGeekrie/customProfiler/main/gif/demoProf.gif"/></p>

## When to use this

This is **durable instrumentation**: you decorate the handful of functions you care
about, leave the decorators in the code, and read the numbers in your logs, run after
run, in production. It answers *is this still taking as long as it used to*.

It is **not** a diagnostic profiler. To find out which function is slow in the first
place, reach for the right tool and come back:

| You want to | Use |
|---|---|
| find the hotspot in a run | `cProfile` + [snakeviz](https://jiffyclub.github.io/snakeviz/), or [py-spy](https://github.com/benfred/py-spy) on a live process |
| know what actually allocates | [`tracemalloc`](https://docs.python.org/3/library/tracemalloc.html) or [memray](https://github.com/bloomberg/memray) — this package reports process RSS, not allocations |
| time a small expression | `timeit` |
| **keep watching a known hotspot, in your own logs** | **this** |

One dependency (`psutil`), ships type hints (`py.typed`), Python 3.9+.

## Installation

For users:
```bash
pip install custom-profiler 
# it's also ok: pip install custom_profiler
```

For developers:
```bash
git clone https://github.com/KarGeekrie/customProfiler.git
pip install -e "customProfiler[test]"
```

The installed version is available as `custom_profiler.__version__`.

Run the test suite (the demo scripts of this README live in `test/demo/`):
```bash
cd customProfiler && pytest
```

## Upgrading from 0.3

Every 0.3 name still works and raises a `DeprecationWarning`. They go away in 2.0.

| 0.3 | 1.0 |
|---|---|
| `options(interractivity=…)` | `options(interactivity=…)` |
| `options(useLogger=…)` | `options(use_logger=…)` |
| `options(loggername=…)` | `options(logger_name=…)` |
| `options(addCustumLvl=…)` | `options(add_custom_level=…)` |
| `options(profilerlvl=…)` | `options(profiler_level=…)` |
| `options(forcePrintInCsl=…)` | `options(force_print_in_console=…)` |
| `options(noSummaryInLog=…)` | `options(no_summary_in_log=…)` |
| `data["peack_memory"]` | `data["peak_memory"]` |
| `info["memory_peack"]` | `info["memory_peak"]` |
| `INTERACTIVITY_OPT_ENUM` | `Interactivity` |
| `custom_profiler.custum_profiler` | `custom_profiler._profiler` |

Two changes are **not** covered by an alias:

* `max_memory_b` is now the maximum, in bytes, like every other `_b` key. The
  per-call list moved to `per_call_memory_b`, so `max(data["max_memory_b"])` raises
  `TypeError` instead of returning the wrong thing quietly.
* `options()` no longer resets the options you leave out. It used to, because every
  keyword had a concrete default.

The full list is in [CHANGELOG.md](CHANGELOG.md).

## Profile a function

To profile a python function, just add *@profiler*:
```python
import time
from custom_profiler import profiler

@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()
b = my_func()
c = my_func()
```

Give an entry a name of your own with `name=`, on either decorator — useful when the
function name is not what you want to read in the log, or when the same function is
profiled from two places:

```python
@profiler(name="load the config")
def _load():
    ...
```

Your log:
```bash
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    7.8M / peak  160.2M
 ⚡ my_func                                       | takes :        4.15s  | consumes :  Δ    7.6M / peak  160.2M
 ⚡ my_func                                       | takes :        4.16s  | consumes :  Δ    7.6M / peak  160.2M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer       12.49s  / memory peak   190.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---                 my_func                  |    3    |        4.16s  /       12.44s  |    7.8M  /  160.2M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Reading the output

Two things get printed: one line per call as it finishes, and one summary table at
the end of the run.

**The line**, printed when a call returns:

```bash
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    7.8M / peak  160.2M
```

* the **name** — the function's, or the label given to `magic_profiler` / `name=`.
  Truncated at 45 characters; widen it with `options(name_width=70)`, or pass
  `None` to never truncate:

  ```
  name_width = 45     ⚡ services.billing.invoice.recompute_monthly_to | takes : …
  name_width = None   ⚡ services.billing.invoice.recompute_monthly_totals_for_account | takes : …
  ```
* **takes** — wall time of that call
* **Δ** — process RSS when the call returned, minus RSS when it started. Exact, but
  it is the whole process, not your function: see [Limitations](#limitations)
* **peak** — the highest `Δ` the watcher thread saw *during* the call. Only shown
  when a watcher ran, and sampled once a second by default — see
  `refresh_interval` and [Limitations](#limitations). Absent in line-by-line mode

Nested calls are indented two spaces per level, `┌─` opening a group and `├─`
marking a sibling at the same level:

```bash
 ⚡ my_code_to_prof                               | takes :        3.13s  | consumes :  Δ    7.9M / peak  160.2M
 ⚡   ┌─big list                                  | takes :       65.92ms | consumes :  Δ  160.1M / peak  160.1M
```

**The summary table**, printed once at exit:

```bash
 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        7.31s  / memory peak   182.6M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---             my_code_to_prof              |    1    |        3.13s  /        3.13s  |    7.9M  /  160.2M
 ⚡ -+--                 big list                 |    1    |       65.92ms /       65.92ms |  160.1M  /  160.1M
```

* **`+---`**, before the name, is the **depth marker**. Four slots, one per nesting
  level 0 to 3, `+` where this entry was seen at that depth. `+---` ran at top
  level, `-+--` always one level deep, `++--` both — a function called directly
  *and* from inside another profiled one. Deeper than 3 is not shown
* **Nb call** — how many times it ran. For a recursive function this counts every
  entry, while the time counts only the outermost (see [Limitations](#limitations))
* **time : max / global** — the slowest single call, then the total. The mean is
  deliberately not shown: it is `global / Nb call`, both of which are on the line,
  while the worst call is not reconstructible from anything else — and it is the
  number a mean hides. Pick another with
  `options(summary_time=…)`: `"mean"`, `"max"`, `"median"`, `"p95"`, or a tuple of
  them such as `("mean", "max")`, which widens the column
* **mem. max : Δ** — the largest `Δ` across calls
* **/ Th** — the largest value seen including the watcher **Th**read's samples: the
  same as `Δ` when no peak was caught, higher when one was

The header line carries the run totals: wall time since `import custom_profiler`,
and the process memory high-water mark.

## Profile raw code (with context managers)

Profile raw code with minimal impact:

```python
import time
from custom_profiler import profiler, magic_profiler

with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    del e

@profiler
def my_func():
    with magic_profiler("big list") :
        a = [1] * (10 ** 6)
        b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()
```

Your log:
```bash
 ⚡ my_code_to_prof                               | takes :        3.13s  | consumes :  Δ    7.9M / peak  160.2M
 ⚡   ┌─big list                                  | takes :       65.92ms | consumes :  Δ  160.1M / peak  160.1M
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    7.7M / peak  160.1M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        7.31s  / memory peak   182.6M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---             my_code_to_prof              |    1    |        3.13s  /        3.13s  |    7.9M  /  160.2M
 ⚡ -+--                 big list                 |    1    |       65.92ms /       65.92ms |  160.1M  /  160.1M
 ⚡ +---                 my_func                  |    1    |        4.14s  /        4.14s  |    7.7M  /  160.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Access to profiler data

You can access profiler data by requesting it from `profiler_collecteur["my_function_name"]`. For a function (or a part of code profiled with context managers), available data are:
* *nb_call*: number of times the function is called
* *global_time* / *global_time_s*: total time spent in the function (as a string or in seconds)
* *mean_time* / *mean_time_s*: mean time spent in the function (= global_time / nb_call)
* *max_time* / *max_time_s*: the slowest single call
* *median_time_s* / *p95_time_s*: the typical call, and the tail. Beyond
  *max_samples* calls these come from the first samples kept; the mean, total and
  maximum stay exact
* *per_call_time_s*: the duration of each individual call, in seconds
* *max_memory* / *max_memory_b*: maximum memory used by the function (as a string or in bytes)
* *per_call_memory_b*: the memory consumed by each individual call, in bytes
* *peak_memory* / *peak_memory_b*: similar to max_memory, but provides access to thread data. Threads can detect memory peaks during the function execution. *max_memory* only computes the delta memory between the start and end of the function.

`profiler_collecteur` is a mapping, so you do not need to know the names in advance:

```python
from custom_profiler import profiler_collecteur as pc

len(pc)                       # how many things were profiled
"my_func" in pc               # was this one ever called
for name in pc:               # every name, in the order first seen
    print(name, pc[name]["global_time"])

pc.keys(), pc.items(), pc.values()

pc.to_dict()                  # everything at once, as plain dicts:
                              # {"global_info": {...}, "profiled": {name: {...}}}
pc.reset()                    # drop the measurements and start a new phase.
                              # The global timer keeps running.
```

`to_dict()` is the export path — it is JSON-serialisable, so writing a run to a file
is one line. `reset()` is how you profile a long process in phases rather than as one
average.

Global data is also available with `profiler_collecteur.get_global_info()`:
* *global_run_time* / *global_run_time_s*: global time since `import custom_profiler` (as a string or in seconds)
* *memory_peak* / *memory_peak_b*: global memory peak since `import custom_profiler` (as a string or in bytes)

```python
import time
import pprint

from custom_profiler import magic_profiler
from custom_profiler import profiler_collecteur as pc

with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    del e

pprint.pprint(pc["my_code_to_prof"])
pprint.pprint(pc.get_global_info())
```

Your log:
```bash
[...]
>>> pprint.pprint(pc["my_code_to_prof"])
    {'global_time': '       3.43s ',
    'global_time_s': 3.430555187000209,
    'max_memory': '7.9M',
    'max_memory_b': 8265728,
    'mean_time': '       3.43s ',
    'mean_time_s': 3.430555187000209,
    'nb_call': 1,
    'peak_memory': '160.5M',
    'peak_memory_b': 168267776,
    'per_call_memory_b': [8265728]}
>>> pprint.pprint(pc.get_global_info())
    {'global_run_time': '       5.43s ',
    'global_run_time_s': 5.433014978999836,
    'memory_peak': '174.5M',
    'memory_peak_b': 182996992.0}
[...]
```

## Profile line by line

To profile a python function line by line, just add *@profiler_lbl* (no memory peak in this mode):
```python
import time
from custom_profiler import profiler_lbl

@profiler_lbl
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(1)
    del b
    time.sleep(5)
    return a

a = my_func()
```

Your log:
```bash
 ⚡ ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : my_func from [...]/customProfiler/test/demo/prof_lbl.py
 ⚡ l 6       a = [1] * (10 ** 6)                 | takes :        3.41ms | consumes :  Δ    7.9M
 ⚡ l 7       b = [2] * (2 * 10 ** 7)             | takes :       63.09ms | consumes :  Δ  152.7M
 ⚡ l 8       time.sleep(2)                       | takes :        2.00s  | consumes :  Δ    0.0B
 ⚡ l 9       del b                               | takes :       55.80ms | consumes :  Δ -152.5M
 ⚡ l 10      time.sleep(2)                       | takes :        2.00s  | consumes :  Δ    0.0B
 ⚡ l 11      return a                            | takes :      633.85µs | consumes :  Δ    0.0B
 ⚡ ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : end
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    8.1M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        4.15s  / memory peak   175.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---              my_func l 6                 |    1    |       11.14ms /       11.14ms |    7.6M  /    7.6M
 ⚡ +---              my_func l 7                 |    1    |      156.92ms /      156.92ms |  152.6M  /  152.6M
 ⚡ +---              my_func l 8                 |    1    |        2.00s  /        2.00s  |    0.0B  /    0.0B
 ⚡ +---              my_func l 9                 |    1    |       54.68ms /       54.68ms | -152.6M  / -152.6M
 ⚡ +---              my_func l 10                |    1    |        2.00s  /        2.00s  |    0.0B  /    0.0B
 ⚡ +---              my_func l 11                |    1    |      168.90µs /      168.90µs |    0.0B  /    0.0B
 ⚡ +---                 my_func                  |    1    |        4.23s  /        4.23s  |    7.7M  /    7.7M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Options and logger

The profiler uses a thread to monitor memory evolution and offers an interactive report (following time and memory). Thread options are:

```python
class Interactivity(str, Enum) :
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interactive print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interactive print
    AUTO          = "AUTO"          # if the console is redirected (sys.stdout.isatty() == False) AUTO means MF_NO_INTERAC, else ENABLE
    OFF           = "OFF"           # record nothing at all
```

Setting `CUSTOM_PROFILER=0` in the environment switches the package off whole: the
decorators return your function untouched, and nothing is printed at exit. A program
that ships profiled code and runs with the variable set writes nothing at all, so its
own output stays pipeable.

Without it, note that importing `custom_profiler` is enough to get the summary on
stdout when the process ends, even if you never profile anything. Send it to a logger
with `use_logger` if that is in the way.

The other options allow you to activate a logger :
* *use_logger* : put log in a logger, default : *False*
* *logger_name* : name of logger, if use_logger set at True, default : " ⚡"
* *add_custom_level* : add new logging level call *PROFILER* at level *profiler_level*. Log is put in *INFO* if add_custom_level is *False*
* *profiler_level* : logging level, default : *25*
* *force_print_in_console* : if the logger is enabled, force print in the console and in the logger. Default: False
* *no_summary_in_log* : if the logger is enabled, disable the profiler summary in the logger. Default: False
* *refresh_interval* : how often, in seconds, the watcher thread samples memory and
  repaints the interactive line. Default: *1.0*
* *summary_time* : which per-call time statistic the summary shows before the total.
  One of `"mean"`, `"max"`, `"median"`, `"p95"`, or a tuple of them. Default: *("max",)*
* *max_samples* : how many per-call samples to keep per entry, feeding
  `median_time_s` and `p95_time_s`. The call count, total and maximum stay exact
  beyond it. Default: *100000*
* *name_width* : width of the name column, shared by the per-call lines and the
  summary so the two stay aligned. `None` never truncates — the summary then sizes
  itself to its longest name, and short names are still padded so the columns hold.
  Default: *45*

`options()` only changes what you pass it: a partial call leaves every other option
alone.

Pass `encoding="utf-8"` to `logging.basicConfig`. The profiler logs the ⚡ character:
on a platform whose default encoding cannot represent it (cp1252 on Windows) it comes
out escaped as `\u26a1`, and a hand-built `FileHandler` — which defaults to strict
error handling, unlike `basicConfig` — drops those records entirely, without raising.

This example illustrates the loading of options in the profiler:

```python
import time
import logging

from custom_profiler import profiler, Interactivity
from custom_profiler import profiler_collecteur as pc

logging.basicConfig(filename="demologger.txt", filemode='w', encoding="utf-8")

pc.options(interactivity = Interactivity.AUTO # ENABLE / MF_NO_INTERAC / DISABLE / AUTO / OFF
           , use_logger = True
           , logger_name = " ⚡"
           , add_custom_level = True
           , profiler_level = 25
           , force_print_in_console = True
           , no_summary_in_log = False)

#[... run the code you want to profile ...]
@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(1)
    del b
    time.sleep(5)
    return a

a = my_func()
```

Your bash log:
```bash
 ⚡ my_func                                       | takes :        6.13s  | consumes :  Δ    7.9M / peak  160.5M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        6.16s  / memory peak   174.8M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---                 my_func                  |    1    |        6.13s  /        6.13s  |    7.9M  /  160.5M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

Your log in file *demologger.txt*:
```bash
PROFILER: ⚡:   my_func                                       | takes :        6.13s  | consumes :  Δ    7.9M / peak  160.3M
PROFILER: ⚡:
          ⚡:   customProfiler log : global timer        6.13s  / memory peak   175.3M
          ⚡:
          ⚡:                     fct name                    | Nb call |   time : max / global         | mem. max :  Δ / Th
          ⚡:   ============================================================================================================
          ⚡:   +---                 my_func                  |    1    |        6.13s  /        6.13s  |    7.9M  /  160.3M
```

## Limitations

Worth knowing before you trust a number:

* **`async def` and generator functions are not measured.** The decorator times the
  creation of the coroutine or generator object, not its execution, so it reports
  microseconds for work that took seconds — silently, and the number looks
  plausible:

  ```
  async def slow():  await asyncio.sleep(0.3)   # real 0.301s, reported 0.000002s
  ```

  Decorating one raises a `RuntimeWarning` at the decoration site, so you find out
  when you write it rather than when you trust the number. Wrap the `await` in
  `magic_profiler` instead, or profile the synchronous function underneath. Support is not planned for 1.x: the semantics under concurrency need
  deciding first, since wall time across an `await` includes time spent yielded to
  the event loop, so concurrent tasks would each report the full span and the sum
  would exceed the run time.
* **Memory is the process RSS**, not your function's allocations. Anything else
  running in the process — another thread, a garbage collection, an import — lands
  in the delta. Freed memory often stays in the allocator, so a `del` may show no
  drop at all.
* **Profile memory single-threaded.** Time is measured per thread and is
  meaningful under concurrency; memory is process-wide and is not.
* **A recursive function is timed by its outermost call.** `nb_call` counts every
  entry, `global_time` counts the seconds it was on the stack, once.
* **`@profiler_lbl` uses `sys.settrace`**, so it cannot share a process with a
  debugger or with `coverage`. It leaves theirs alone rather than fighting it, which
  means it reports **nothing at all** in that situation rather than breaking them —
  and says so with a `RuntimeWarning`, since a silent empty report is worse than a
  noisy one. Its own timing is still recorded. It also makes the traced
  function much slower, follows only the decorated function and not the functions it
  calls, and reports no memory peak.
* **The memory peak is sampled once per second** by the watcher thread. Below about
  two seconds per call, treat `peak` as indicative and trust only `Δ`: a spike that
  opens and closes inside the call is sampled zero times, and `peak` then just
  repeats `Δ`. Lower `refresh_interval` when you need the real figure —
  a transient 160 MB allocation inside a 450 ms call, measured on Linux:

  ```
  refresh_interval = 1.0    Δ =  20.0K   peak =  20.0K     # never sampled
  refresh_interval = 0.02   Δ =  20.0K   peak = 152.6M     # caught
  ```

  On a platform whose allocator keeps the freed pages, `Δ` would report them too
  and the gap would be smaller — the sampling rate is the part you control.

  The cost is one `memory_info()` read per interval, and a faster repaint of the
  interactive line when it is on.
* The profiler itself costs time. For microbenchmarks, use `timeit`.

## Raw profiler

If you would rather not add a dependency on this package, copy the following instead.
It still needs `psutil` — that is where the memory readings come from — but it is
self-contained and has no other moving parts.

```python
import functools
import time
import sys
import psutil

if sys.platform != 'win32':
    import resource

process = psutil.Process()

_UNITS = ('B', 'K', 'M', 'G', 'T', 'P')

def bytes2human(nbytes):
    for i in range(len(_UNITS) - 1, 0, -1):
        step = 1 << (i * 10)
        if abs(nbytes) >= step:
            return f"{nbytes / step:.1f}{_UNITS[i]}"
    return f"{nbytes:.1f}B"

dicoPerf = {}

class global_info():
    def __init__(self):
        self.start_time = time.perf_counter()
    def info(self):
        run_time_s = time.perf_counter() - self.start_time
        if sys.platform == 'win32':
            mem_peak_b = process.memory_info().peak_wset
        else :
            # ru_maxrss is in kibibytes on Linux and in bytes on macOS/BSD
            unit = 1 if sys.platform == 'darwin' else 1024
            mem_peak_b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
        mem_peak = bytes2human(mem_peak_b)
        return {"global_run_time_s": run_time_s, 
                "memory_peak": mem_peak,
                "memory_peak_b": mem_peak_b}
    def __str__(self):
        info = self.info()
        return f" ⚡⚡⚡ global_run_time_s {info['global_run_time_s']:7.2f}s - global_memory_peak {info['memory_peak']}"
gi = global_info()

class magic_profiler():
    def __init__(self, func_name, dicoPerf):
        self.name = func_name
        self.dicoPerf = dicoPerf
    def __enter__(self):
        self.start_mem = process.memory_info().rss
        self.start_time = time.perf_counter()
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_mem = process.memory_info().rss
        nplog = (end_time - self.start_time, end_mem - self.start_mem)
        if self.name in self.dicoPerf.keys():
            self.dicoPerf[self.name] += [nplog]
        else:
            self.dicoPerf[self.name] = [nplog]
        print(f" ⚡ {self.name:20} - time {end_time - self.start_time:7.2f}s - mem {bytes2human(end_mem - self.start_mem):7}")

def magic_decorator(dicoPerf):
    def decorator(func):
        name = func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_mem = process.memory_info().rss
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            end_mem = process.memory_info().rss
            
            nplog = (end_time - start_time, end_mem - start_mem)
            if name in dicoPerf.keys():
                dicoPerf[name] += [nplog]
            else:
                dicoPerf[name] = [nplog]
            print(f" ⚡ {name:20} - time {end_time - start_time:7.2f}s - mem {bytes2human(end_mem - start_mem):7}")
            return result
        return wrapper
    return decorator

def postProLogPerf(dicoPerf):
    dicoLog = {}
    print(" ⚡ Log perf:")
    for key, value in dicoPerf.items():
        time_tot = sum([arr[0] for arr in value])
        time_mean = time_tot / len(value)
        time_max = max([arr[0] for arr in value])

        mem_max = max([arr[1] for arr in value])
        dicoLog[key] = {"key": key, "time_tot": time_tot, "time_mean": time_mean, "time_max":time_max, "mem_max": mem_max}
        print(f" ⚡    * {key:20} - time_tot {time_tot:7.2f}s - time_mean {time_mean:7.2f}s - time_max {time_max:7.2f}s - mem_max {bytes2human(mem_max):7} - nb call {len(value):4}")
    return dicoLog

#############
#Use example:

with magic_profiler("time.sleep", dicoPerf):
    time.sleep(2)

@magic_decorator(dicoPerf)
def dodo():
    time.sleep(2)

dodo()
dodo()

postProLogPerf(dicoPerf)
print(gi)
```

## License

MIT — see [LICENSE](LICENSE).
