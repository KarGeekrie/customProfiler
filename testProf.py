import time
from customProfiler import profiler, magic_profiler, profiler_collecteur

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
