import time
import sys
if sys.platform != 'win32':
    import resource
import logging
import threading
from collections import OrderedDict
import atexit

import psutil
process = psutil.Process()

from custom_profiler.custum_logger import add_logging_level
from custom_profiler.human_readable_time import human_time_duration as htd


# ru_maxrss is in kibibytes on Linux and in bytes on macOS/BSD
RU_MAXRSS_UNIT = 1 if sys.platform == 'darwin' else 1024


class INTERACTIVITY_OPT_ENUM :
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interacrtif print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interacrtif print
    AUTO          = "AUTO"          # if console is redirect in file (sys.stdout.isatty() == false) AUTO is equivalente to MF_NO_INTERAC else is equivalente to ENABLE

def get_ENUM_list(ENUM):
    return [key for key in ENUM.__dict__ if key not in ["__main__", "__module__", "__doc__", '__dict__', '__weakref__']]


_UNITS = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')

def _bytes2human(nbytes):
    # vendored from psutil._common.bytes2human, which is private API
    for i in range(len(_UNITS) - 1, 0, -1):
        step = 1 << (i * 10)
        if abs(nbytes) >= step:
            return f"{nbytes / step:.1f}{_UNITS[i]}"
    return f"{nbytes:.1f}B"

def bytes2human(deltaMem):
    strToAdd = "-"
    if abs(deltaMem) == 0 or deltaMem / abs(deltaMem) == 1. :
        strToAdd = ""
    return strToAdd+_bytes2human(abs(deltaMem))

class profiler_collecteur(object):
    _instance = None

    def __new__(self):
        if self._instance is None:
            self._instance = super(profiler_collecteur, self).__new__(self)
            self.profData = OrderedDict()
            self.profThread = OrderedDict()
            self.interractivity = INTERACTIVITY_OPT_ENUM.DISABLE
            self.logger = None
            self.start_time = time.perf_counter()
            self.forcePrintInCsl = False
            self.noSummaryInLog = False
            # nesting depth and re-entrancy are per thread: two threads calling
            # the same profiled function are not nested inside one another
            self._local = threading.local()
            self._lock = threading.RLock()
            atexit.register(self._instance._report_at_exit)

        return self._instance

    @property
    def deep(self):
        """[current depth, previous depth], for this thread."""
        deep = getattr(self._local, "deep", None)
        if deep is None:
            deep = [-1, -1]
            self._local.deep = deep
        return deep

    @deep.setter
    def deep(self, value):
        self._local.deep = list(value)

    @property
    def _active(self):
        """How many frames of each name are currently running, in this thread."""
        active = getattr(self._local, "active", None)
        if active is None:
            active = {}
            self._local.active = active
        return active

    def incr(self, fname=None):
        """Enter a profiled block. Returns False for a re-entrant (recursive) call."""
        self.deep[0] += 1
        if fname is None:
            return True

        active = self._active
        running = active.get(fname, 0)
        active[fname] = running + 1
        return running == 0

    def save(self, fname, deltaTime, deltaMem, long_fname=None, outermost=True, keep_deep=False):
        """Record one call. A re-entrant call only bumps nbCall: its duration is
        already counted by the outermost frame, and adding it would count the same
        seconds several times over."""
        with self._lock :
            if fname in self.profData.keys():
                self.profData[fname]["nbCall"] += 1
                if outermost :
                    self.profData[fname]["dt"] += deltaTime
                    self.profData[fname]["dm_list"].append(deltaMem)
                    self.profData[fname]["deep"].append(self.deep[0])
            else :
                self.profData[fname] = {"dt": deltaTime if outermost else 0.,
                                        "dm_list": [deltaMem] if outermost else [],
                                        "nbCall": 1,
                                        "deep": [self.deep[0]] if outermost else []}

            active = self._active
            if fname in active :
                active[fname] -= 1
                if active[fname] <= 0 :
                    del active[fname]

            if outermost :
                t_str = htd(deltaTime)
                value = f"{t_str}"
                strmen = bytes2human(deltaMem)
                if long_fname == None :
                    long_fname = fname
                self.print_line(long_fname, value, strmen)

        if not keep_deep :
            self.deep[0] -= 1

    def thread_view(self, fname, deltaMem):
        with self._lock :
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
        else :
            mem_peack_b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * RU_MAXRSS_UNIT
        mem_peack = bytes2human(mem_peack_b)
        return {"global_run_time": run_time, 
                "global_run_time_s": run_time_s, 
                "memory_peack": mem_peack,
                "memory_peack_b": mem_peack_b}
    
    def _print(self, toprint, end='\n'):
        if self.logger:
            self.logger("  " + toprint)
        if self.forcePrintInCsl or not self.logger:
            print(" ⚡" + toprint, end=end)

    def print_line(self, fname, delta_time, delta_mem, end='\n', color=""):
        delta_mem_str = " Δ " + f"{delta_mem:>7}"
        if fname in self.profThread.keys():
            mmax = 0.
            if fname in self.profData.keys(): 
                mmax = max(self.profData[fname]["dm_list"] or [0])
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
        colorEnd = "" if color == "" else "\033[0m"
        toprint = f"{color} {fname: <45.45} | takes : {delta_time} | consumes : {delta_mem_str} {colorEnd}"
        self.deep[1] = self.deep[0]
        self._print(toprint, end)

    def __strMaxMemory(self, key, rbytes=False):
        val = self.profData[key]
        mmax = max(val["dm_list"] or [0])
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
            str += f" customProfiler log : global timer {ggi['global_run_time']} / memory peack {ggi['memory_peack']:^10}"
            # str += f"\n ⚡ {'':^45} | {'':7} | {'time':^29} | {'mem. consumption':^17}"
            str += "\n " + "⚡" * 8
            str += (f"\n ⚡ {'fct name':^45} | {'Nb call':7} | " +
                    f"{'  time : mean / global':<29} | {'mem. max :  Δ / Th':^17}")
            str += "\n ⚡ "+ "="*108
            for key, val in self.profData.items():
                t_str = htd(val["dt"])
                t_p_call_str = htd(val["dt"]/val['nbCall'])

                dp = list(sorted(set(val["deep"])))
                dp_str = ''.join(["+" if i in dp else "-" for i in range(4)])

                str += f"\n ⚡ {dp_str} {key: ^40.40} | {val['nbCall']:^7} "
                str += f"| {t_p_call_str} / {t_str} "
                strmen = bytes2human(max(val["dm_list"] or [0]))
                strmaxmem = self.__strMaxMemory(key)
                str += f"| {strmen:>7}  / {strmaxmem:>7}"
            str += "\n " + "⚡" * 8
        else :
            str = ("\n " + "⚡" * 2 + f" customProfiler log : global timer {ggi['global_run_time']} / max memory use {ggi['memory_peack']:^10}")
        return str

    def _report_at_exit(self):
        """The end of run summary. atexit, never __del__: at interpreter teardown
        the module globals __del__ needs may already be gone."""
        if self.logger and not self.noSummaryInLog :
            spaceSize = " " * (len(self.lvl) + len(self.loggername))
            logSummary = self.__str__()
            logSummary = logSummary.replace('⚡', '  ').replace('\n ', f'\n{spaceSize}⚡:')
            logSummary = logSummary.replace('              customProfiler', 'customProfiler')
            logSummary = logSummary.splitlines()
            self.logger("\n".join(logSummary[:-1]))

        if self.forcePrintInCsl or not self.logger:
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
                 "max_memory": bytes2human(max(val['dm_list'] or [0])),
                 "max_memory_b": val['dm_list'],
                 "peack_memory": self.__strMaxMemory(key),
                 "peack_memory_b": self.__strMaxMemory(key, rbytes=True)}

    def options(self, interractivity = INTERACTIVITY_OPT_ENUM.AUTO
                , useLogger=False
                , loggername = " ⚡"
                , addCustumLvl= True
                , profilerlvl = 25
                , forcePrintInCsl = False
                , noSummaryInLog = False):
        
        assert interractivity in get_ENUM_list(INTERACTIVITY_OPT_ENUM), f'interractivity {interractivity} must be in INTERACTIVITY_OPT_ENUM : {get_ENUM_list(INTERACTIVITY_OPT_ENUM)}'
        
        self.interractivity = interractivity
        self.forcePrintInCsl = forcePrintInCsl
        self.noSummaryInLog = noSummaryInLog
        self.loggername = loggername

        if interractivity == INTERACTIVITY_OPT_ENUM.AUTO :
            if sys.stdout.isatty():
                self.interractivity = INTERACTIVITY_OPT_ENUM.ENABLE
            else :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC

        if useLogger:
            if self.interractivity == INTERACTIVITY_OPT_ENUM.ENABLE :
                self.interractivity = INTERACTIVITY_OPT_ENUM.MF_NO_INTERAC
            if addCustumLvl :
                self.lvl = 'PROFILER'
                add_logging_level(self.lvl, profilerlvl)
                logging.getLogger().setLevel(self.lvl)  
                self.logger = logging.getLogger(loggername).profiler
            else :
                self.lvl = 'INFO'
                logging.getLogger().setLevel(self.lvl)  
                self.logger = logging.getLogger(loggername).info
        else :
            self.logger = None
