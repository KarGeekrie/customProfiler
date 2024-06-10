import inspect
import time
import sys

import psutil
from psutil._common import bytes2human
process = psutil.Process()

from custom_profiler.collecteur import profiler_collecteur
from custom_profiler.human_readable_time import human_time_duration as htd

profC = profiler_collecteur()


def trace_lines(frame, event, arg):

    code_source, lineStart = inspect.getsourcelines(frame.f_code)
    co_name  = frame.f_code.co_name

    if event != "line":
        fname = f"l {frame.f_lineno:<3} {profC.__src[-1]:40}"
        fnameSave  = f"{co_name} l {frame.f_lineno:<3}"
        t     = time.perf_counter() - profC.__tic
        men   = process.memory_info().rss - profC.__tic_mem
        profC.save(fnameSave, t, men, fname)
        profC._print( " " + "⚡"*20 + f" line per line : end") 
        return

    profC.__src.append(code_source[frame.f_lineno - lineStart].split('\n')[0])

    if len(profC.__src) == 1 :
        head = code_source[1].split('\n')[0]
        profC._print( " " + "⚡"*20 + f" line per line : {head.split()[1].split('(')[0]} from {frame.f_code.co_filename}") 
    else :
        fname  = f"l {frame.f_lineno-1:<3} {profC.__src[-2]:40}"
        fnameSave  = f"{co_name} l {frame.f_lineno-1:<3}"
        t  = time.perf_counter() - profC.__tic
        men = process.memory_info().rss - profC.__tic_mem
        profC.save(fnameSave, t, men, fname)

    profC.__tic = time.perf_counter()
    profC.__tic_mem = process.memory_info().rss

  
def trace_calls(frame, event, arg):
    profC.__tic = 0.
    profC.__tic_mem = 0.
    profC.__src = []

    if event != "call":
        return
    return trace_lines


def lpl(fonction):
    def wrapper(*args, **kwargs):
        sys.settrace(trace_calls)
        resultat = fonction(*args, **kwargs)
        sys.settrace(None)
        return resultat
    return wrapper


if __name__ == "__main__":

    @lpl
    def my_func():
        a = [1] * (10 ** 6)
        b = [2] * (2 * 10 ** 7)  
        time.sleep(1)
        del b
        # time.sleep(5)
        return a

    my_func()
