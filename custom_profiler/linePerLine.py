import inspect
import time

tic = 0
src = []

def trace_lines(frame, event, arg):
    global tic, src

    if event != "line":
        print(f"{src[-1]} l{frame.f_lineno} took : {time.perf_counter() - tic:0.4f}s") 
        return
    
    code_source, lineStart = inspect.getsourcelines(frame.f_code)
    src.append(code_source[frame.f_lineno - lineStart].split('\n')[0])

    if len(src) == 1 :
        head = code_source[1].split('\n')[0]
        print(f"{head}") 
    else :
        print(f"{src[-2]} l{frame.f_lineno-1} took : {time.perf_counter() - tic:0.4f}s") 

    tic = time.perf_counter()


  
def trace_calls(frame, event, arg):
    if event != "call":
        return
    return trace_lines

import sys


def lpl(fonction):
    def wrapper(*args, **kwargs):
        sys.settrace(trace_calls)
        resultat = fonction(*args, **kwargs)
        sys.settrace(None)
        return resultat
    return wrapper

import time

@lpl
def ma_fonction():
    time.sleep(1)
    a = 10
    print(a)
    b = 20
    c = a + b
    print(c)
    time.sleep(2)
    #woot
    #d = "doudou"
    #return "gg"


ma_fonction()
