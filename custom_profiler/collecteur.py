import time
import sys
if sys.platform == 'linux':
    import resource
import logging
from collections import OrderedDict

import psutil
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


def bytes2human(deltaMem):
    strToAdd = "-"
    if abs(deltaMem) == 0 or deltaMem / abs(deltaMem) == 1. :
        strToAdd = ""
    return strToAdd+psutil._common.bytes2human(abs(deltaMem))

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
            self.deep = [-1, -1]
        return self._instance

    def options(self, interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
                , useLogger=False
                , loggername = " ⚡"
                , addCustumLvl= True
                , profilerlvl = 25):
        
        assert interractivity in get_ENUM_list(INTERACTIVITY_OPT_ENUM), f'interractivity {interractivity} must be in INTERACTIVITY_OPT_ENUM : {getEnumList(INTERACTIVITY_OPT_ENUM)}'
        
        self.interractivity = interractivity
        
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

    def incr(self):
        self.deep[0] += 1

    def save(self, fname, deltaTime, deltaMem, long_fname=None):
        if fname in self.profData.keys():
            self.profData[fname]["dt"] += deltaTime
            self.profData[fname]["dm_list"].append(deltaMem)
            self.profData[fname]["nbCall"] += 1
            self.profData[fname]["deep"].append(self.deep[0])
        else :
            self.profData[fname] = {"dt": deltaTime , "dm_list": [deltaMem], "nbCall": 1, "deep": [self.deep[0]]}

        t_str = htd(deltaTime)
        value = f"{t_str}"
        strmen = bytes2human(deltaMem)
        if long_fname == None :
            long_fname = fname
        self.print_line(long_fname, value, strmen)
        self.deep[0] -= 1

    def thread_view(self, fname, deltaMem):
        if fname in self.profThread.keys():
            if deltaMem > self.profThread[fname]:
                self.profThread[fname] = deltaMem
        else :
            self.profThread[fname] = deltaMem

    def get_global_info(self):
        run_time_s = time.perf_counter() - self.start_time
        run_time = htd(run_time_s)
        if sys.platform == 'win32':
            mem_peack_b = process.memory_info().peak_wset
            mem_peack = bytes2human(mem_peack_b)
        else :
            mem_peack_b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 0.0009765625
            mem_peack = bytes2human(mem_peack_b) # in bytes
        return {"global_run_time": run_time, 
                "global_run_time_s": run_time_s, 
                "memory_peack": mem_peack,
                "memory_peack_b": mem_peack_b}
    
    def _print(self, toprint, end='\n'):
        if self.logger:
            self.logger(toprint)
        else:
            print(toprint, end=end)

    def print_line(self, fname, delta_time, delta_mem, end='\n', color=""):
        delta_mem_str = " Δ " + f"{delta_mem:>7}"
        if fname in self.profThread.keys():
            mmax = 0.
            if fname in self.profData.keys(): 
                mmax = max(self.profData[fname]["dm_list"])
            if mmax < self.profThread[fname] :
                mmax = self.profThread[fname]
            delta_mem_str += " / peak " +  f"{bytes2human(mmax):>7}"
        elif self.profThread.keys() :
            delta_mem_str += " / peak " +  f"{delta_mem:>7}"
        if self.deep[0] > 0:
            if self.deep[1] != self.deep[0] :
                fname = "  " * self.deep[0] + "┌─" + fname
            else :
                fname = "  " * self.deep[0] + "├─" + fname
        toprint = f"{color} ⚡ {fname: <50.50} took : {delta_time:<10} consumes : {delta_mem_str} \033[0m"
        self.deep[1] = self.deep[0]
        self._print(toprint, end)

    def __strMaxMemory(self, key, rbytes=False):
        val = self.profData[key]
        mmax = max(val["dm_list"])
        if key in self.profThread.keys():
            if mmax < self.profThread[key] :
                mmax = self.profThread[key]
        if rbytes :
            return mmax
        else :
            return bytes2human(mmax)

    def __str__(self):
        ggi = self.get_global_info()
        if self.profData.items() :
            str = "\n " + "⚡" * 8 
            str += f" customProfiler log : global timer {ggi['global_run_time']} / max memory use {ggi['memory_peack']:^10}"
            str += "⚡" * 7 + "\n " + "⚡" * 53
            str += "\n ⚡ {:^37} | {:8} | {:<29} | {:^17} ⚡".format("fct name"
                                                        , "Nb call"
                                                        , "  time : mean / global"
                                                        , "mem : max / maxTh")
            str += "\n ⚡ "+ "="*101 + "⚡"
            for key, val in self.profData.items():
                t_str = htd(val["dt"])
                t_p_call_str = htd(val["dt"]/val['nbCall'])

                dp = list(sorted(set(val["deep"])))
                dp_str = ''.join(["+" if i in dp else "-" for i in range(4)])

                str += f"\n ⚡ {dp_str} {key: ^32.32} | {val['nbCall']:^8} "
                str += f"| {t_p_call_str} / {t_str} "
                strmen = bytes2human(max(val["dm_list"]))
                strmaxmem = self.__strMaxMemory(key)
                str += f"| {strmen:>7} / {strmaxmem:>7} ⚡"
            str += "\n " + "⚡" * 53
        else :
            str = ("\n " + "⚡" * 2 + f" customProfiler log : global timer {ggi['global_run_time']} / max memory use {ggi['memory_peack']:^10}")
        return str

    def __del__(self):
        print(self)

    def __getitem__(self, key):
        try :
            val = self.profData[key]
        except KeyError:
            raise KeyError(f"key avail in collecteur : {list(self.profData.keys())}")

        return { "nb_call": val['nbCall'],
                 "global_time": htd(val["dt"]),
                 "global_time_s": val["dt"],
                 "mean_time": htd(val["dt"]/val['nbCall']),
                 "mean_time_s": val["dt"]/val['nbCall'],
                 "max_memory": bytes2human(max(val['dm_list'])),
                 "max_memory_b": val['dm_list'],
                 "peack_memory": self.__strMaxMemory(key),
                 "peack_memory_b": self.__strMaxMemory(key, rbytes=True)}
