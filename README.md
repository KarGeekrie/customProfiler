# ⚡ custom_profiler ⚡

**custom_profiler** is a simple, interactive and lightweight (the only dependency is psutil) way of profiling the memory and execution time of your python code.

<p align="center"><img src="/gif/demoProf.gif?raw=true"/></p>

## Installation :

For user :
```bash
pip install git+https://github.com/KarGeekrie/customProfiler.git
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
    time.sleep(1)
    del b
    time.sleep(5)
    return a

a = my_func()
```

Your log :
```bash
 ⚡        my_func        took :        4.12s  consumes :  Δ 7.8M / peak 160.3M

 ⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        4.15s  / max memory use   172.2M  ⚡⚡⚡⚡⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡            fct name             | Nb call  |      mean time / global       |   mem Δ /  peak    ⚡
 ⚡ =============================================================================================== ⚡
 ⚡             my_func             |    1     |        4.12s  /        4.12s  |    7.8M /  160.3M  ⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

```

## Profil row code (with context managers) :

Profil row code with minimal impact :

```python
import time
from custom_profiler import magic_profiler

with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(3)
    del e
```

Your log :
```bash
 ⚡    my_code_to_prof    took :        3.12s  consumes :  Δ 7.8M / peak 160.3M

 ⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        3.16s  / max memory use   172.0M  ⚡⚡⚡⚡⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡            fct name             | Nb call  |      mean time / global       |   mem Δ /  peak    ⚡
 ⚡ =============================================================================================== ⚡
 ⚡         my_code_to_prof         |    1     |        3.12s  /        3.12s  |    7.8M /  160.3M  ⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

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
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : my_func from test_custromProfiler.py
 ⚡ l 7       a = [1] * (10 ** 6)                  took :        3.10ms consumes : 7.5M
 ⚡ l 8       b = [2] * (2 * 10 ** 7)              took :       39.74ms consumes : 152.5M
 ⚡ l 9       time.sleep(2)                        took :        2.00s  consumes : 0.0B
 ⚡ l 10      del b                                took :       52.63ms consumes : -152.3M
 ⚡ l 11      time.sleep(2)                        took :        2.01s  consumes : 0.0B
 ⚡ l 12      return a                             took :        1.07ms consumes : 0.0B
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡ line per line : end
 ⚡        my_func        took :        4.14s  consumes : 8.0M

 ⚡⚡⚡⚡⚡⚡ customProfiler log : global timer        4.16s  / max memory use   172.3M  ⚡⚡⚡⚡⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
 ⚡            fct name             | Nb call  |      mean time / global       |   mem Δ /  peak    ⚡
 ⚡ =============================================================================================== ⚡
 ⚡          my_func l 7            |    1     |        3.10ms /        3.10ms |    7.5M /     N.A  ⚡
 ⚡          my_func l 8            |    1     |       39.74ms /       39.74ms |  152.5M /     N.A  ⚡
 ⚡          my_func l 9            |    1     |        2.00s  /        2.00s  |    0.0B /     N.A  ⚡
 ⚡          my_func l 10           |    1     |       52.63ms /       52.63ms | -152.3M /     N.A  ⚡
 ⚡          my_func l 11           |    1     |        2.01s  /        2.01s  |    0.0B /     N.A  ⚡
 ⚡          my_func l 12           |    1     |        1.07ms /        1.07ms |    0.0B /     N.A  ⚡
 ⚡             my_func             |    1     |        4.14s  /        4.14s  |    8.0M /     N.A  ⚡
 ⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡

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

```python
import time
import logging

from custom_profiler import profiler, profiler_lbl, magic_profiler, profiler_collecteur, INTERACTIVITY_OPT_ENUM

loggername = " ⚡" # logger name
addCustumLvl = False # add "PROFILER" level in logger

pc = profiler_collecteur()
pc.options(interractivity = INTERACTIVITY_OPT_ENUM.ENABLE # ENABLE / MF_NO_INTERAC / DISABLE / AUTO
          , useLogger = True
          , loggername = loggername
          , addCustumLvl = addCustumLvl
          , profilerlvl = 25)

logInConsol = True

logger = logging.getLogger(loggername)
if logInConsol: #Log in consol
    logging.basicConfig()
else : #Log in file
    logging.basicConfig(filename='custom_profiler.log', filemode='w')

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

#if you want log summary in your logger :
if addCustumLvl :
    logger.profiler(pc.__str__())
else :
    logger.info(pc.__str__())
```

