import sys
import time
from collections import OrderedDict

from threading import Thread
from threading import Event

import resource
import psutil
from psutil._common import bytes2human
process = psutil.Process()

import logging

from .human_readable_time import human_time_duration as htd
from .custumlogger import addLoggingLevel

class INTERACTIVITY_OPT_ENUM :
    AUTO          = "AUTO"          # if console in file (sys.stdout.isatty() == false) -> "MF_NO_INTERAC" else "ENABLE" 
    ENABLE        = "ENABLE"        # thread and interacrtif print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory follow with thread, no interacrtif print
    DISABLE       = "DISABLE"       # no thread no interacrtif print


def getEnumList(ENUM):
    return [key for key in ENUM.__dict__ if key not in ["__main__", "__module__", "__doc__", '__dict__', '__weakref__']]


class profiler_collecteur(object):
    _instance = None

    def __new__(self):
        if self._instance is None:
            self._instance = super(profiler_collecteur, self).__new__(self)
            self.profData = OrderedDict()
            self.profThread = OrderedDict()
            self.interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
            self.logger = None
            self.start_time = time.perf_counter()
        return self._instance

    def options(self, interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
                , useLogger=False
                , loggername = "⚡"
                , addCustumLvl= True
                , profilerlvl = 25):
        
        assert interractivity in getEnumList(INTERACTIVITY_OPT_ENUM), f'interractivity {interractivity} must be in INTERACTIVITY_OPT_ENUM : {getEnumList(INTERACTIVITY_OPT_ENUM)}'
        
        if interractivity == INTERACTIVITY_OPT_ENUM.AUTO :
            if sys.stdout.isatty():
                self.interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
            else :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC

        if useLogger:
            if self.interractivity == INTERACTIVITY_OPT_ENUM.ENABLE :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC
            if addCustumLvl :
                addLoggingLevel('PROFILER', profilerlvl)
                logging.getLogger().setLevel("PROFILER")  
                self.logger = logging.getLogger(loggername).profiler
            else :
                self.logger = logging.getLogger(loggername).info
        else :
            self.logger = None

    def save(self, fname, deltaTime, deltaMem):
        if fname in self.profData.keys():
            self.profData[fname]["dt"] += deltaTime
            self.profData[fname]["dm"] += deltaMem
            self.profData[fname]["nbCall"] += 1
        else :
            self.profData[fname] = {"dt": deltaTime ,"dm": deltaMem ,"nbCall": 1}

        t_str = htd(deltaTime)
        value = f"{t_str}"
        strmen = bytes2human(deltaMem)
        self.print_line(fname, value, strmen)

    def thread_view(self, fname, deltaMem):
        if fname in self.profThread.keys():
            if deltaMem > self.profThread[fname]:
                self.profThread[fname] = deltaMem
        else :
            self.profThread[fname] = deltaMem

    def get_global_info(self):
        run_time = htd(time.perf_counter() - self.start_time)
        mem_peack = bytes2human(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 0.0009765625) # in bytes
        return run_time, mem_peack

    def print_line(self, fname, delta_time, delta_mem, end='\n', color=""):
        toprint = f"{color} ⚡ fct : {fname: ^20.20} took : {delta_time:<10} consumes : {delta_mem:<10} \033[0m"
        if self.logger:
            self.logger(toprint)
        else:
            print(toprint, end=end)

    def __str__(self):
        run_time, mem_peack = self.get_global_info()
        str = ("\n " + "⚡" * 5 + f" customProfiler log : global timer {run_time} / max memory use {mem_peack:^10}"+ "⚡" * 4)
        str += "\n " + "⚡" * 47
        str += "\n ⚡ {:^20} | {:8} | {:^29} | {:^13} ⚡".format("fct name"
                                                    , "Nb call"
                                                    , "mean time / global"
                                                    , " mem Δ /  peak ")
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
                strmaxmem = "N.A"
            str += f"| {strmen:>6} / {strmaxmem:>6} ⚡"
        str += "\n " + "⚡" * 47
        return str

    def __del__(self):
        if self.logger:
            self.logger(self.__str__())
        else:
            print(self)

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


def profiler(func):
    def wrapper(*args, **kwargs):
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            tm = thread_mananger(func.__name__, time.perf_counter(), process.memory_info().rss)
        
        start_mem = process.memory_info().rss
        start_time = time.perf_counter()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        end_mem = process.memory_info().rss

        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            tm.end()

        profC.save(func.__name__, end_time - start_time, end_mem - start_mem)

        return result
    return wrapper


class magic_profiler:
    def __init__(self, func_name):
        self.func_name = func_name

    def __enter__(self):
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            self.tm = thread_mananger(self.func_name, time.perf_counter(), process.memory_info().rss)
        self.start_mem = process.memory_info().rss
        self.start_time = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_mem = process.memory_info().rss
        if profC.interractivity != INTERACTIVITY_OPT_ENUM.DISABLE :
            self.tm.end()
        profC.save(self.func_name, end_time - self.start_time, end_mem - self.start_mem)


if __name__ == "__main__":

    pass