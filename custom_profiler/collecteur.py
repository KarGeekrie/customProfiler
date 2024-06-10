import time
import sys
if sys.platform == 'linux':
    import resource
import logging
from collections import OrderedDict

import psutil
from psutil._common import bytes2human
process = psutil.Process()

from custom_profiler.custum_logger import add_logging_level
from custom_profiler.human_readable_time import human_time_duration as htd


class INTERACTIVITY_OPT_ENUM :
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interacrtif print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interacrtif print
    AUTO          = "AUTO"          # if console is redirect in file (sys.stdout.isatty() == false) AUTO is equivalente to MF_NO_INTERAC else is equivalente to ENABLE

def get_ENUM_list(ENUM):
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
                , loggername = " ⚡"
                , addCustumLvl= True
                , profilerlvl = 25):
        
        assert interractivity in get_ENUM_list(INTERACTIVITY_OPT_ENUM), f'interractivity {interractivity} must be in INTERACTIVITY_OPT_ENUM : {getEnumList(INTERACTIVITY_OPT_ENUM)}'
        
        if interractivity == INTERACTIVITY_OPT_ENUM.AUTO :
            if sys.stdout.isatty():
                self.interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
            else :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC

        if useLogger:
            if self.interractivity == INTERACTIVITY_OPT_ENUM.ENABLE :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC
            if addCustumLvl :
                add_logging_level('PROFILER', profilerlvl)
                logging.getLogger().setLevel("PROFILER")  
                self.logger = logging.getLogger(loggername).profiler
            else :
                logging.getLogger().setLevel("INFO")  
                self.logger = logging.getLogger(loggername).info
        else :
            self.logger = None

    def save(self, fname, deltaTime, deltaMem, long_fname=None):
        if fname in self.profData.keys():
            self.profData[fname]["dt"] += deltaTime
            self.profData[fname]["dm"] += deltaMem
            self.profData[fname]["dm_list"].append(deltaMem)
            self.profData[fname]["nbCall"] += 1
        else :
            self.profData[fname] = {"dt": deltaTime ,"dm": deltaMem, "dm_list": [deltaMem], "nbCall": 1}

        t_str = htd(deltaTime)
        value = f"{t_str}"
        strmen = bytes2human(deltaMem)
        if long_fname == None :
            long_fname = fname
        self.print_line(long_fname, value, strmen)

    def thread_view(self, fname, deltaMem):
        if fname in self.profThread.keys():
            if deltaMem > self.profThread[fname]:
                self.profThread[fname] = deltaMem
        else :
            self.profThread[fname] = deltaMem

    def get_global_info(self):
        run_time = htd(time.perf_counter() - self.start_time)
        if sys.platform == 'win32':
            mem_peack = bytes2human(process.memory_info().peak_wset)
        else :
            mem_peack = bytes2human(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 0.0009765625) # in bytes
        return run_time, mem_peack
    
    def _print(self, toprint, end='\n'):
        if self.logger:
            self.logger(toprint)
        else:
            print(toprint, end=end)

    def print_line(self, fname, delta_time, delta_mem, end='\n', color=""):
        delta_mem = " Δ " + f"{delta_mem:>7}"
        if fname in self.profThread.keys():
            mmax = 0.
            if fname in self.profData.keys(): 
                mmax = max(self.profData[fname]["dm_list"])
            if mmax < self.profThread[fname] :
                mmax = self.profThread[fname]
            delta_mem += " / peak " +  f"{bytes2human(mmax):>7}"
        toprint = f"{color} ⚡ {fname: ^21} took : {delta_time:<10} consumes : {delta_mem} \033[0m"
        self._print(toprint, end)
    
    def __str__(self):
        run_time, mem_peack = self.get_global_info()
        str = ("\n " + "⚡" * 6 + f" customProfiler log : global timer {run_time} / max memory use {mem_peack:^10}"+ "⚡" * 6)
        str += "\n " + "⚡" * 50
        str += "\n ⚡ {:^31} | {:8} | {:<29} | {:^17} ⚡".format("fct name"
                                                    , "Nb call"
                                                    , "  time : mean / global"
                                                    , "mem : mean / max")
        str += "\n ⚡ "+ "="*95 + "⚡"
        for key, val in self.profData.items():
            t_str = htd(val["dt"])
            t_p_call_str = htd(val["dt"]/val['nbCall'])
            str += f"\n ⚡ {key: ^31.31} | {val['nbCall']:^8} "
            str += f"| {t_p_call_str} / {t_str} "
            strmen = bytes2human(self.profData[key]["dm"]/val['nbCall'])
            mmax = max(self.profData[key]["dm_list"])
            if key in self.profThread.keys():
                if mmax < self.profThread[key] :
                    mmax = self.profThread[key]
            strmaxmem = bytes2human(mmax)
            str += f"| {strmen:>7} / {strmaxmem:>7} ⚡"
        str += "\n " + "⚡" * 50
        return str

    def __del__(self):
        print(self)
