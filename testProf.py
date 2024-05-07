import time
from custom_profiler import profiler, magic_profiler, profiler_collecteur, INTERACTIVITY_OPT_ENUM
import logging

pc = profiler_collecteur()
pc.options(interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
          , useLogger=True
          , loggername = "⚡"
          , addCustumLvl= True
          , profilerlvl = 25)

ch = logging.StreamHandler()
logger = logging.getLogger("⚡")
logger.addHandler(ch)

#logging.getLogger("⚡").setLevel(logging.PROFILER)

@profiler
def test(t):
    time.sleep(t)

test(1e-9)
test(1e-1)
test(5)

@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(1)
    del b
    # time.sleep(5)
    return a

a = my_func()

with magic_profiler("mon code a prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(1)
    del e
    # time.sleep(5)


