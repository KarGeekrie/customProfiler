import os
import sys
import time
import inspect
import warnings

from functools import wraps

import threading
from threading import Thread
from threading import Event

import psutil
process = psutil.Process()

from custom_profiler import line_by_line
from custom_profiler.line_by_line import trace_calls
from custom_profiler.collecteur import (profiler_collecteur, Interactivity,
                                        bytes2human, DISABLED,
                                        DEFAULT_POLL_S, DEFAULT_REFRESH_S)
from custom_profiler.human_readable_time import human_time_duration as htd


profC = profiler_collecteur()


POLL_S    = DEFAULT_POLL_S     # how often the watcher wakes up
REFRESH_S = DEFAULT_REFRESH_S  # default for profC.refresh_interval


def task(event, fname, start_time, start_mem):
    # fixed for the duration of this call: options() applies to the next one
    refresh = profC.refresh_interval
    poll = min(POLL_S, refresh)      # a poll coarser than the refresh caps it

    next_refresh = time.perf_counter()  # sample at once, then every refresh
    while True :
        time.sleep(poll)
        now = time.perf_counter()
        if now >= next_refresh :
            next_refresh = now + refresh
            t_str = htd(now - start_time)
            dm = process.memory_info().rss - start_mem
            profC.thread_view(fname, dm) #sauvegarde delta mem max
            strmen = bytes2human(dm)
            if profC.interractivity == Interactivity.ENABLE :
                if threading.active_count() < 3:
                    profC.print_line(fname, t_str, strmen, end="\r", color="\033[93m")

        if event.is_set():
            break


class _ThreadManager:
    def __init__(self, fname, start_time, start_mem):
        self.event = Event()
        self.t = Thread(target=task, args=(self.event, fname, start_time, start_mem))
        self.t.daemon = True
        self.t.start()

    def end(self):
        self.event.set()
        self.t.join()


thread_mananger = _ThreadManager  # deprecated spelling, removed in 2.0


#https://stackoverflow.com/questions/5929107/decorators-with-parameters
def profiler(func=None, linePerline=False, *, name=None):
    """Profile a function.

    Usable bare (``@profiler``) or called (``@profiler(name="my label")``).

    ``linePerline`` stays positional for the 0.3 spelling profiler(func, True).
    """
    def decorate(fct):
        if DISABLED :
            return fct
        _warn_if_not_measurable(fct)
        return _wrap(fct, name or fct.__name__, linePerline)

    if func is None :
        return decorate
    return decorate(func)


_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def _user_stacklevel():
    """Point a warning at the caller's line, not ours.

    @profiler and @profiler(name=...) do not go through the same number of
    frames, so the level has to be found rather than hard-coded.
    """
    # warn() counts from its own caller, which is one frame below this helper
    level = 0
    frame = inspect.currentframe()
    while frame is not None :
        frame = frame.f_back
        level += 1
        if frame is None :
            break
        if not os.path.abspath(frame.f_code.co_filename).startswith(_PACKAGE_DIR) :
            return level
    return 2


def _warn_if_not_measurable(func):
    """A coroutine or generator function returns its object immediately, so the
    wrapper times the *creation* and reports microseconds for work that took
    seconds. Say so at decoration: the number it prints looks perfectly plausible.
    """
    if inspect.iscoroutinefunction(func) :
        kind = "a coroutine"
    elif inspect.isasyncgenfunction(func) :
        kind = "an async generator"
    elif inspect.isgeneratorfunction(func) :
        kind = "a generator"
    else :
        return

    warnings.warn(
        f"{func.__qualname__} is {kind} function: the profiler will time how long "
        f"it takes to create the object, not to run it, and report microseconds "
        f"for work that takes seconds. Profile the body with magic_profiler "
        f"instead, or the synchronous function underneath.",
        RuntimeWarning, stacklevel=_user_stacklevel())


def _wrap(func, fname, linePerline):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if profC.interractivity == Interactivity.OFF :
            return func(*args, **kwargs)

        # a recursive call is timed by its outermost frame only: adding the inner
        # frames would count the same seconds several times over
        outermost = profC.incr(fname)
        start_mem = process.memory_info().rss
        start_time = time.perf_counter()
        tm = None
        installed = False

        # everything after incr() must run even when it raises, otherwise the
        # watcher thread leaks and neither profC.deep nor the re-entrancy count
        # comes back down
        try :
            if (profC.interractivity != Interactivity.DISABLE
                    and linePerline == False and outermost) :
                tm = _ThreadManager(fname, start_time, start_mem)

            # only the frame that installed the tracer takes it away: a nested or
            # recursive lbl call switching it off under its caller left the
            # tracer state stuck, killing line tracing for the whole process
            if linePerline :
                current = sys.gettrace()
                if current is None :
                    line_by_line.set_pending_label(fname)
                    sys.settrace(trace_calls)
                    installed = True
                elif current is not trace_calls :
                    # someone else's: a debugger, or coverage. We leave it alone
                    # rather than break it, but then we report nothing at all
                    warnings.warn(
                        f"another tracer is installed (a debugger, or coverage), so "
                        f"@profiler_lbl reports no lines for {fname}. Its own timing "
                        f"is still recorded.",
                        RuntimeWarning, stacklevel=2)

            return func(*args, **kwargs)
        finally :
            if installed :
                sys.settrace(None)
                line_by_line.set_pending_label(None)

            end_time = time.perf_counter()
            end_mem = process.memory_info().rss

            if tm is not None :
                tm.end()

            profC.save(fname, end_time - start_time, end_mem - start_mem,
                       outermost=outermost)
    return wrapper


class magic_profiler():

    def __init__(self, func_name):
        self.func_name = func_name
        self.disabled = True

    def __enter__(self):
        self.disabled = DISABLED or profC.interractivity == Interactivity.OFF
        if self.disabled :
            return

        self.outermost = profC.incr(self.func_name)
        self.start_mem = process.memory_info().rss
        self.start_time = time.perf_counter()
        self.tm = None
        if profC.interractivity != Interactivity.DISABLE and self.outermost :
            self.tm = _ThreadManager(self.func_name, self.start_time, self.start_mem)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.disabled :
            return

        end_time = time.perf_counter()
        end_mem = process.memory_info().rss
        if self.tm is not None :
            self.tm.end()
        profC.save(self.func_name, end_time - self.start_time, end_mem - self.start_mem,
                   outermost=self.outermost)
