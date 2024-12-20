import sys
import time

from functools import wraps

import threading
from threading import Thread
from threading import Event

import psutil
from psutil._common import bytes2human
process = psutil.Process()

from custom_profiler.line_by_line import trace_calls
from custom_profiler.collecteur import profiler_collecteur, INTERACTIVITY_OPT_ENUM
from custom_profiler.human_readable_time import human_time_duration as htd


profC = profiler_collecteur()


def task(event, fname, start_time, start_mem):
    i = 0
    while True :
        time.sleep(0.01)
        if i % 100 == True :
            t_str = htd(time.perf_counter() - start_time)
            dm = process.memory_info().rss - start_mem
            profC.thread_view(fname, dm) #sauvegarde delta mem max
            strmen = bytes2human(dm)
            if profC.interractivity == INTERACTIVITY_OPT_ENUM.ENABLE :
                if threading.active_count() < 3:
                    profC.print_line(fname, t_str, strmen, end="\r", color="\033[93m")

        i += 1
        if event.is_set():
            break


class thread_mananger:
    def __init__(self, fname, start_time, start_mem):
        self.event = Event()
        self.t = Thread(target=task, args=(self.event, fname, start_time, start_mem))
        self.t.daemon = True
        self.t.start()

    def end(self):
        self.event.set()
        self.t.join()

#https://stackoverflow.com/questions/5929107/decorators-with-parameters
def profiler(func, linePerline):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE and linePerline == False:
            tm = thread_mananger(func.__name__, time.perf_counter(), process.memory_info().rss)
        
        profC.incr()
        start_mem = process.memory_info().rss
        start_time = time.perf_counter()

        if linePerline :
            sys.settrace(trace_calls)
        result = func(*args, **kwargs)
        if linePerline :
            sys.settrace(None)

        end_time = time.perf_counter()
        end_mem = process.memory_info().rss

        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE and linePerline == False :
            tm.end()

        profC.save(func.__name__, end_time - start_time, end_mem - start_mem)

        return result
    return wrapper


class magic_profiler():

    def __init__(self, func_name):
        self.func_name = func_name

    def __enter__(self):
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            self.tm = thread_mananger(self.func_name, time.perf_counter(), process.memory_info().rss)
        profC.incr()
        self.start_mem = process.memory_info().rss
        self.start_time = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_mem = process.memory_info().rss
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            self.tm.end()
        profC.save(self.func_name, end_time - self.start_time, end_mem - self.start_mem)
