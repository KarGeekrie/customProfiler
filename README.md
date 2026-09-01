# ⚡ custom_profiler ⚡

**custom_profiler** is a simple, interactive and lightweight (the only dependency is psutil) way of profiling the memory and execution time of your python code.

<p align="center"><img src="https://raw.githubusercontent.com/KarGeekrie/customProfiler/main/gif/demoProf.gif"/></p>

## Installation :

For user :
```bash
pip install custom-profiler 
# it's also ok : pip install custom_profiler
```

For devellopeur :
```bash
git clone https://github.com/KarGeekrie/customProfiler.git
pip install -e "customProfiler[test]"
```

Run the test suite (the demo scripts of this README live in `test/demo/`) :
```bash
cd customProfiler && pytest
```

## Profil function :

For profil python function, just add *@profiler* :
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

Your log :
```bash
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    7.8M / peak  160.2M
 ⚡ my_func                                       | takes :        4.15s  | consumes :  Δ    7.6M / peak  160.2M
 ⚡ my_func                                       | takes :        4.16s  | consumes :  Δ    7.6M / peak  160.2M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer       12.49s  / memory peak   190.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---                 my_func                  |    3    |        4.15s  /       12.44s  |    7.8M  /  160.2M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Profil row code (with context managers) :

Profil row code with minimal impact :

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

Your log :
```bash
 ⚡ my_code_to_prof                               | takes :        3.13s  | consumes :  Δ    7.9M / peak  160.2M
 ⚡   ┌─big list                                  | takes :       65.92ms | consumes :  Δ  160.1M / peak  160.1M
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    7.7M / peak  160.1M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        7.31s  / memory peak   182.6M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---             my_code_to_prof              |    1    |        3.13s  /        3.13s  |    7.9M  /  160.2M
 ⚡ -+--                 big list                 |    1    |       65.92ms /       65.92ms |  160.1M  /  160.1M
 ⚡ +---                 my_func                  |    1    |        4.14s  /        4.14s  |    7.7M  /  160.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Access to profiler data :

You cannot access profiler data by requesting it from `profiler_collecteur["my_function_name"]`. For a function (or a part of code profiled with context managers), available data are:
* *nb_call*: number of times the function is called
* *global_time* / *global_time_s*: total time spent in the function (as a string or in seconds)
* *mean_time* / *mean_time_s*: mean time spent in the function (= global_time / nb_call)
* *max_memory* / *max_memory_b*: maximum memory used by the function (as a string or in bytes)
* *per_call_memory_b*: the memory consumed by each individual call, in bytes
* *peak_memory* / *peak_memory_b*: similar to max_memory, but provides access to thread data. Threads can detect memory peaks during the function execution. *max_memory* only computes the delta memory between the start and end of the function.

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

Your log :
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

## Profil line by line :

For profil python function line by line, just add *@profiler_lbl* (follow memory peak is Not Avail in this case) :
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

Your log :
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
 ⚡                   fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
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

## Options and logger :

The profiler uses thread to monitor memory evolution and offert interactive report (follow time and memory). Thread options are :

```python
class Interactivity(str, Enum) :
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interactive print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interactive print
    AUTO          = "AUTO"          # if the console is redirected (sys.stdout.isatty() == False) AUTO means MF_NO_INTERAC, else ENABLE
    OFF           = "OFF"           # record nothing at all
```

Setting `CUSTOM_PROFILER=0` in the environment removes the decorators entirely, so
profiled code costs nothing in production.

The other options allow you to activate a logger :
* *use_logger* : put log in a logger, default : *False*
* *logger_name* : name of logger, if use_logger set at True, default : " ⚡"
* *add_custom_level* : add new logging level call *PROFILER* at level *profiler_level*. Log is put in *INFO* if add_custom_level is *False*
* *profiler_level* : logging level, default : *25*
* *force_print_in_console* : if the logger is enabled, force print in the console and in the logger. Default: False
* *no_summary_in_log* : if the logger is enabled, disable the profiler summary in the logger. Default: False

`options()` only changes what you pass it: a partial call leaves every other option
alone.

Pass `encoding="utf-8"` to `logging.basicConfig`. The profiler logs the ⚡ character:
on a platform whose default encoding cannot represent it (cp1252 on Windows) it comes
out escaped as `\u26a1`, and a hand-built `FileHandler` — which defaults to strict
error handling, unlike `basicConfig` — drops those records entirely, without raising.

This example illustrates the loading of options in the profiler :

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

#[... run your code to profil...]
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

Your bash log :
```bash
 ⚡ my_func                                       | takes :        6.13s  | consumes :  Δ    7.9M / peak  160.5M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        6.16s  / memory peak   174.8M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---                 my_func                  |    1    |        6.13s  /        6.13s  |    7.9M  /  160.5M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

Your log in file *demologger.txt* :
```bash
PROFILER: ⚡:   my_func                                       | takes :        6.13s  | consumes :  Δ    7.9M / peak  160.3M
PROFILER: ⚡:
          ⚡:   customProfiler log : global timer        6.13s  / memory peak   175.3M
          ⚡:
          ⚡:                     fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
          ⚡:   ============================================================================================================
          ⚡:   +---                 my_func                  |    1    |        6.13s  /        6.13s  |    7.9M  /  160.3M
```

## Limitations :

Worth knowing before you trust a number :

* **Memory is the process RSS**, not your function's allocations. Anything else
  running in the process — another thread, a garbage collection, an import — lands
  in the delta. Freed memory often stays in the allocator, so a `del` may show no
  drop at all.
* **Profile memory single-threaded.** Time is measured per thread and is
  meaningful under concurrency; memory is process-wide and is not.
* **A recursive function is timed by its outermost call.** `nb_call` counts every
  entry, `global_time` counts the seconds it was on the stack, once.
* **`@profiler_lbl` uses `sys.settrace`**, so it cannot share a process with a
  debugger or with `coverage`, and it makes the traced function much slower. It
  follows only the decorated function, not the functions it calls, and reports no
  memory peak.
* **The memory peak is sampled once per second** by the watcher thread, so a
  spike inside a fast function can be missed. The `Δ` column is exact; the `peak`
  column is a best effort.
* The profiler itself costs time. For microbenchmarks, use `timeit`.

## Row profiler:

If you don't want any dependencies, simply copy the following code:

```python
import functools
import time
import sys
import psutil
from psutil._common import bytes2human

if sys.platform != 'win32':
    import resource

process = psutil.Process()

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
        if self.name in dicoPerf.keys():
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
#Use exemple:

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
