import time
import custom_profiler

def my_func():
    a = [1] * (10 ** 6)
    b = [2] * (2 * 10 ** 7)  
    time.sleep(2)
    del b
    time.sleep(2)
    return a