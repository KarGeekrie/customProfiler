import sys
import time
from collections import OrderedDict

from threading import Thread
from threading import Event

import psutil
from psutil._common import bytes2human
process = psutil.Process()

from .human_readable_time import human_time_duration as htd


class profiler_collecteur(object):
    _instance = None

    def __new__(self, threadForPrint=None):
        if self._instance is None:
            self._instance = super(profiler_collecteur, self).__new__(self)
            self.profData = OrderedDict()
            self.profThread = OrderedDict()
            self.printOnline = True
            if threadForPrint == None :
                self.threadForPrint = sys.stdout.isatty()
            else : 
                self.threadForPrint = threadForPrint
        return self._instance

    def save(self, fname, deltaTime, deltaMem):
        if fname in self.profData.keys():
            self.profData[fname]["dt"] += deltaTime
            self.profData[fname]["dm"] += deltaMem
            self.profData[fname]["nbCall"] += 1
        else :
            self.profData[fname] = {"dt": deltaTime ,"dm": deltaMem ,"nbCall": 1}

        if self.printOnline :
            t_str = htd(deltaTime)
            value = f"{t_str}"
            strmen = bytes2human(deltaMem)
            self.printLine(fname, value, strmen)

    def threadview(self, fname, deltaMem):
        if fname in self.profThread.keys():
            if deltaMem > self.profThread[fname]:
                self.profThread[fname] = deltaMem
        else :
            self.profThread[fname] = deltaMem
            

    def printLine(self, fname, delta_time, delta_mem, end='\n', color=""):
        print(f"{color} ⚡ fct : {fname: ^20.20} took : {delta_time:<10} consumes : {delta_mem:<10} \033[0m", end=end)

    def __str__(self):
        str = ("\n " + "⚡" * 17 + " customProfiler log : "+ "⚡" * 19)
        str += "\n " + "⚡" * 47
        str += "\n ⚡ {:^20} | {:8} | {:^29} | {:^13} ⚡".format("fct name"
                                                    , "Nb call"
                                                    , "mean time / global"
                                                    , " Δ : mean / max memory")
        str += "\n ⚡ "+ "="*89 + "⚡"
        for key, val in self.profData.items():
            t_str = htd(val["dt"])
            t_p_call_str = htd(val["dt"]/val['nbCall'])
            str += f"\n ⚡ {key: ^20.20} | {val['nbCall']:^8} "
            str += f"| {t_p_call_str} / {t_str} "
            strmen = bytes2human(self.profData[key]["dm"]/val['nbCall'])
            if key in self.profThread.keys():
                strmaxmem = bytes2human(self.profThread[key])
            else :
                strmaxmem = "not avail"
            str += f"| {strmen:^9} / {strmaxmem:^10} ⚡"
        str += "\n " + "⚡" * 47
        return str

    def __del__(self):
        print(self)

profC = profiler_collecteur(threadForPrint=True)


def task(event, fname, start_time, start_mem):
    i = 0
    while True :
        time.sleep(0.01)
        if i % 100 == True :
            t_str = htd(time.perf_counter() - start_time)
            dm = process.memory_info().rss - start_mem
            profC.threadview(fname, dm) #sauvegarde delta mem max
            strmen = bytes2human(dm)
            profC.printLine(fname, t_str, strmen, end="\r", color="\033[93m")
            
        i += 1
        if event.is_set():
            break

      
class threadMananger:
    def __init__(self, fname, start_time, start_mem):
        self.event = Event()
        self.t = Thread(target=task, args=(self.event, fname, start_time, start_mem))
        self.t.daemon = True
        self.t.start()

    def end(self):
        self.event.set()
        self.t.join()


def profiler(func):
    def wrapper(*args, **kwargs):
        if profC.threadForPrint:
            tm = threadMananger(func.__name__, time.perf_counter(), process.memory_info().rss)
        
        start_mem = process.memory_info().rss
        start_time = time.perf_counter()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        end_mem = process.memory_info().rss

        if profC.threadForPrint:
            tm.end()

        profC.save(func.__name__, end_time - start_time, end_mem - start_mem)

        return result
    return wrapper


class magic_profiler:
    def __init__(self, func_name):
        self.func_name = func_name

    def __enter__(self):
        if profC.threadForPrint:
            self.tm = threadMananger(self.func_name, time.perf_counter(), process.memory_info().rss)
        self.start_mem = process.memory_info().rss
        self.start_time = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_mem = process.memory_info().rss
        if profC.threadForPrint:
            self.tm.end()
        profC.save(self.func_name, end_time - self.start_time, end_mem - self.start_mem)


if __name__ == "__main__":

    pass