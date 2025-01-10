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
    current_line = code_source[frame.f_lineno - lineStart].strip()
    co_name  = frame.f_code.co_name

    if event != "line":
        fname = f"l {frame.f_lineno:<3} {profC.__src[-1]:40}"
        fnameSave  = f"{co_name} l {frame.f_lineno:<3}"
        t     = time.perf_counter() - profC.__tic
        men   = process.memory_info().rss - profC.__tic_mem
        profC.save(fnameSave, t, men, fname)
        profC._print( " " + "⚡"*20 + f" line per line : end") 
        return

    if (current_line in profC.__srcMultiLine or (profC.__last_print_line and frame.f_lineno <= profC.__last_print_line)) :
            return

    # Check if the current line is part of a continued statement
    profC.__paren_count += current_line.count('(') - current_line.count(')')

    if profC.__paren_count > 0 :
        profC.__srcMultiLine.append(current_line)
        return
    
    if current_line.endswith('\\') :
        current_line = current_line[:-1] + "[...]"

    combined_line = current_line
    if profC.__srcMultiLine:
        profC.__srcMultiLine.append(current_line)
        combined_line = ' '.join(profC.__srcMultiLine)
        profC.__srcMultiLine = []

    profC.__src.append(combined_line)

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
    profC.__last_print_line = frame.f_lineno

  
def trace_calls(frame, event, arg):
    profC.__tic = 0.
    profC.__tic_mem = 0.
    profC.__src = []
    profC.__srcMultiLine = []
    profC.__paren_count = 0
    profC.__last_print_line = None

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

    @lpl
    def my_func2():
        a = [1] * (10 ** 6)
        b = [2] * (2 * 10 ** 7)
        time.sleep(1)
        del b
        a = ([1] * (10 ** 6) +
            [2] * (2 * 10 ** 7)) + [0] * (
                1+1 )
        a =  1 + \
             2 + \
                1+1
        print(a) 
        return a
    
    my_func2()