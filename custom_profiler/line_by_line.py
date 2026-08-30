import inspect
import time
import sys

import psutil
process = psutil.Process()

from custom_profiler.collecteur import profiler_collecteur

profC = profiler_collecteur()


_source_cache = {}


def get_source(code):
    """inspect.getsourcelines() is far too slow to call on every line event."""
    if code not in _source_cache:
        try:
            _source_cache[code] = inspect.getsourcelines(code)
        except (OSError, TypeError):
            _source_cache[code] = ([], 0)
    return _source_cache[code]


def strip_literals(line):
    """Drop string contents and comments, so brackets can be counted safely."""
    out = []
    quote = None
    i = 0
    while i < len(line):
        char = line[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#":
            break
        else:
            out.append(char)
        i += 1
    return "".join(out)


def get_statement(code, lineno):
    """Source of the statement starting at `lineno`, and its last line number.

    The continuation lines of a multi-line statement are read from the source
    rather than waited for: CPython may emit a single "line" event for the whole
    statement, or several out-of-order ones, so they cannot be counted from the
    trace events themselves.
    """
    code_source, lineStart = get_source(code)
    idx = lineno - lineStart
    if idx < 0 or idx >= len(code_source):
        return "", lineno

    src = []
    paren_count = 0
    backslash = False
    while idx < len(code_source):
        current_line = code_source[idx].strip()
        continued = current_line.endswith('\\')
        if continued:
            current_line = current_line[:-1] + "[...]"
        if not backslash:
            src.append(current_line)

        clean = strip_literals(current_line)
        paren_count += (clean.count('(') + clean.count('[') + clean.count('{')
                        - clean.count(')') - clean.count(']') - clean.count('}'))
        if continued:
            backslash = True
        elif paren_count <= 0:
            break
        idx += 1
    return ' '.join(src), lineStart + idx


class tracer_state(object):
    """State of the line tracer. Only one frame is traced at a time."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.frame = None
        self.co_name = ""
        self.lineno = None
        self.line_end = None
        self.statement = ""
        self.tic = 0.
        self.tic_mem = 0


state = tracer_state()


def save_line(frame):
    t   = time.perf_counter() - state.tic
    men = process.memory_info().rss - state.tic_mem
    fname     = f"l {state.lineno:<3} {state.statement:40}"
    fnameSave = f"{state.co_name} l {state.lineno:<3}"
    # keep_deep: a traced line is not a nesting level, so it must not decrement
    # the depth counter the enclosing function pushed
    profC.save(fnameSave, t, men, fname, keep_deep=True)


def trace_lines(frame, event, arg):

    if event == "line":
        if state.lineno is not None and state.lineno <= frame.f_lineno <= state.line_end:
            return trace_lines  # still running the same multi-line statement

        if state.lineno is None:
            profC._print(" " + "⚡"*20 + f" line per line : {state.co_name} from {frame.f_code.co_filename}")
        else:
            save_line(frame)

        state.lineno = frame.f_lineno
        state.statement, state.line_end = get_statement(frame.f_code, frame.f_lineno)
        state.tic = time.perf_counter()
        state.tic_mem = process.memory_info().rss

    elif event == "return":
        if state.lineno is not None:
            save_line(frame)
            profC._print(" " + "⚡"*20 + f" line per line : end")
        state.reset()

    # "exception" events do not end a statement (think try/except): ignore them
    return trace_lines


def trace_calls(frame, event, arg):
    if event != "call":
        return
    if state.frame is not None:
        return  # a nested call: only the decorated function is traced

    state.reset()
    state.frame = frame
    state.co_name = frame.f_code.co_name
    return trace_lines


def lpl(fonction):
    def wrapper(*args, **kwargs):
        sys.settrace(trace_calls)
        try:
            resultat = fonction(*args, **kwargs)
        finally:
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
