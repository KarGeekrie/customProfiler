# ⚡ custom_profiler ⚡

**custom_profiler** is a simple, interactive and lightweight (the only dependency is psutil) way of profiling the memory and execution time of your python code.

<p align="center"><img src="/gif/demoProf.gif?raw=true"/></p>

## Installation :

For user :
```bash
pip install custom-profiler 
# it's also ok : pip install custom_profiler
```

For devellopeur :
```bash
git clone https://github.com/KarGeekrie/customProfiler.git
pip install -e customProfiler
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

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer       12.49s  / memory peack   190.1M
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

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        7.31s  / memory peack   182.6M
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
* *max_memory* / *max_memory_b*: maximum memory used by the function (as a string or a list of memory consumed for each call in bytes)
* peak_memory / *peak_memory_b*: similar to max_memory, but provides access to thread data. Threads can detect memory peaks during the function execution. *max_memory* only computes the delta memory between the start and end of the function.

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
    'max_memory_b': [8265728],
    'mean_time': '       3.43s ',
    'mean_time_s': 3.430555187000209,
    'nb_call': 1,
    'peack_memory': '160.5M',
    'peack_memory_b': 168267776}
>>> pprint.pprint(pc.get_global_info())
    {'global_run_time': '       5.43s ',
    'global_run_time_s': 5.433014978999836,
    'memory_peack': '174.5M',
    'memory_peack_b': 182996992.0}
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
 ⚡ ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : my_func from [...]/customProfiler/test/prof_lbl.py
 ⚡ l 6       a = [1] * (10 ** 6)                 | takes :        3.41ms | consumes :  Δ    7.9M
 ⚡ l 7       b = [2] * (2 * 10 ** 7)             | takes :       63.09ms | consumes :  Δ  152.7M
 ⚡ l 8       time.sleep(2)                       | takes :        2.00s  | consumes :  Δ    0.0B
 ⚡ l 9       del b                               | takes :       55.80ms | consumes :  Δ -152.5M
 ⚡ l 10      time.sleep(2)                       | takes :        2.00s  | consumes :  Δ    0.0B
 ⚡ l 11      return a                            | takes :      633.85µs | consumes :  Δ    0.0B
 ⚡ ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : end
 ⚡ my_func                                       | takes :        4.14s  | consumes :  Δ    8.1M

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        4.15s  / memory peack   175.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡                   fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
 ⚡ ============================================================================================================
 ⚡ +---              my_func l 6                 |    1    |        3.41ms /        3.41ms |    7.9M  /    7.9M
 ⚡ ----              my_func l 7                 |    1    |       63.09ms /       63.09ms |  152.7M  /  152.7M
 ⚡ ----              my_func l 8                 |    1    |        2.00s  /        2.00s  |    0.0B  /    0.0B
 ⚡ ----              my_func l 9                 |    1    |       55.80ms /       55.80ms | -152.5M  / -152.5M
 ⚡ ----              my_func l 10                |    1    |        2.00s  /        2.00s  |    0.0B  /    0.0B
 ⚡ ----              my_func l 11                |    1    |      633.85µs /      633.85µs |    0.0B  /    0.0B
 ⚡ ----                 my_func                  |    1    |        4.14s  /        4.14s  |    8.1M  /    8.1M
 ⚡⚡⚡⚡⚡⚡⚡⚡
```

## Options and logger :

The profiler uses thread to monitor memory evolution and offert interactive report (follow time and memory). Thread options are :

```python
class INTERACTIVITY_OPT_ENUM :
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interacrtif print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interacrtif print
    AUTO          = "AUTO"          # if console is redirect in file (sys.stdout.isatty() == false) AUTO is equivalente to MF_NO_INTERAC else is equivalente to ENABLE
```

The other options allow you to activate a logger :
* *useLogger* : put log in a logger, default : *False*
* *loggername* : name of logger, if useLogger set at True, default : " ⚡"
* *addCustumLvl* : add new logging level call *PROFILER* at level *profilerlvl*. Log is put in *INFO" is addCustumLvl is *False*
* *profilerlvl* : logging level, default : *25*
* *forcePrintInCsl* : if the logger is enabled, force print in the console and in the logger. Default: False
* *noSummaryInLog* : if the logger is enabled, disable the profiler summary in the logger. Default: False

This example illustrates the loading of options in the profiler :

```python
import time
import logging

from custom_profiler import profiler, INTERACTIVITY_OPT_ENUM
from custom_profiler import profiler_collecteur as pc

logging.basicConfig(filename="demologger.txt", filemode='w')

pc.options(interractivity = INTERACTIVITY_OPT_ENUM.AUTO # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
           , useLogger = True
           , loggername = " ⚡"
           , addCustumLvl = True
           , profilerlvl = 25
           , forcePrintInCsl = True
           , noSummaryInLog = False)

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

 ⚡⚡⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        6.16s  / memory peack   174.8M
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
          ⚡:   customProfiler log : global timer        6.13s  / memory peack   175.3M
          ⚡:
          ⚡:                     fct name                    | Nb call |   time : mean / global        | mem. max :  Δ / Th
          ⚡:   ============================================================================================================
          ⚡:   +---                 my_func                  |    1    |        6.13s  /        6.13s  |    7.9M  /  160.3M
```