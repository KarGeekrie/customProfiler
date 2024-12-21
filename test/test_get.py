import time
import pprint
from custom_profiler import profiler, magic_profiler, profiler_collecteur

@profiler
def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    with magic_profiler("d_sleep") :
        time.sleep(2)
    del b
    time.sleep(2)
    return a

a = my_func()

@profiler
def f_f():
    b = [2] * (2 * 10 ** 7)  
    with magic_profiler("sleep") :
        time.sleep(1)
    a = my_func()
    time.sleep(1)

f_f()

with magic_profiler("my_code_to_prof") :
    d = [1] * (10 ** 6)
    e = [2] * (2 * 10 ** 7)  
    time.sleep(1)
    del e

pprint.pprint(profiler_collecteur["my_code_to_prof"])
pprint.pprint(profiler_collecteur.get_global_info())
# pprint.pprint(prof_coll["frac"])