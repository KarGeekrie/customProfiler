import os
import time
import sys
import math
import statistics
if sys.platform != 'win32':
    import resource
import logging
import threading
import warnings
from enum import Enum
from collections import OrderedDict
import atexit

import psutil
process = psutil.Process()

from custom_profiler._logging import add_logging_level
from custom_profiler.human_readable_time import human_time_duration as htd


# ru_maxrss is in kibibytes on Linux and in bytes on macOS/BSD
RU_MAXRSS_UNIT = 1 if sys.platform == 'darwin' else 1024


# CUSTOM_PROFILER=0 switches the package off whole: the decorators return the
# function untouched (see _profiler) and no summary is registered, so a program
# that merely imports custom_profiler writes nothing at all
_OFF_VALUES = ("0", "false", "no", "off")
DISABLED = os.environ.get("CUSTOM_PROFILER", "").strip().lower() in _OFF_VALUES


# how often the watcher thread wakes up, and how often it samples memory and
# repaints the interactive line. The sample rate is what the peak column is worth:
# at the 1s default a call shorter than that is sampled once, at its very start
DEFAULT_POLL_S    = 0.01
DEFAULT_REFRESH_S = 1.


# Per-call samples are what median and p95 are computed from. A python float in a
# list costs ~32 bytes, so an uncapped list would be 320 MB after 10 M calls --
# per function, and twice that with memory. Count, sum and max stay exact beyond
# the cap; only the distribution is sampled.
DEFAULT_MAX_SAMPLES = 100_000


# Which per-call time statistic the summary shows before the total. "max" by
# default: it is the only one the other columns cannot reconstruct, since the
# mean is global / Nb call and both are already on the line.
SUMMARY_TIME_STATS   = ("mean", "max", "median", "p95")
DEFAULT_SUMMARY_TIME = ("max",)


def _fixed_width_time(seconds):
    """htd() returns the int 0 for a zero duration, which breaks the columns."""
    return htd(seconds) if seconds else f"{0:11.2f}s "


def _percentile(values, fraction):
    """Nearest rank: deterministic, and defined for a single sample."""
    if not values :
        return 0.
    ordered = sorted(values)
    rank = math.ceil(fraction * len(ordered))
    return ordered[max(0, min(len(ordered) - 1, rank - 1))]


class Interactivity(str, Enum):
    ENABLE        = "ENABLE"        # thread (for memory peak follow) and interactive print
    MF_NO_INTERAC = "MF_NO_INTERAC" # memory peak follow (with thread), no interactive print
    DISABLE       = "DISABLE"       # no thread, no memory peak follow, no interactive print
    AUTO          = "AUTO"          # if the console is redirected (sys.stdout.isatty() == False) AUTO means MF_NO_INTERAC, else ENABLE
    OFF           = "OFF"           # record nothing at all


INTERACTIVITY_OPT_ENUM = Interactivity  # deprecated spelling, removed in 2.0


def get_ENUM_list(ENUM):
    if isinstance(ENUM, type) and issubclass(ENUM, Enum):
        return [member.name for member in ENUM]
    return [key for key in ENUM.__dict__ if key not in ["__main__", "__module__", "__doc__", '__dict__', '__weakref__']]


_UNSET = object()

_LEGACY_OPTIONS = {"interractivity":  "interactivity",
                   "useLogger":       "use_logger",
                   "loggername":      "logger_name",
                   "addCustumLvl":    "add_custom_level",
                   "profilerlvl":     "profiler_level",
                   "forcePrintInCsl": "force_print_in_console",
                   "noSummaryInLog":  "no_summary_in_log"}


class _ProfData(dict):
    """A result dict that still answers to the misspelled keys, with a warning."""

    _DEPRECATED = {"peack_memory":   "peak_memory",
                   "peack_memory_b": "peak_memory_b",
                   "memory_peack":   "memory_peak",
                   "memory_peack_b": "memory_peak_b"}

    def __getitem__(self, key):
        renamed = self._DEPRECATED.get(key)
        if renamed is not None and dict.__contains__(self, renamed):
            warnings.warn(f"the '{key}' key is deprecated, use '{renamed}'",
                          DeprecationWarning, stacklevel=2)
            key = renamed
        return dict.__getitem__(self, key)


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
            self.loggername = " ⚡"
            self.lvl = 'INFO'
            self.refresh_interval = DEFAULT_REFRESH_S
            self.max_samples = DEFAULT_MAX_SAMPLES
            self.summary_time = DEFAULT_SUMMARY_TIME
            # nesting depth and re-entrancy are per thread: two threads calling
            # the same profiled function are not nested inside one another
            self._local = threading.local()
            self._lock = threading.RLock()
            if not DISABLED:
                atexit.register(self._instance._report_at_exit)

        return self._instance

    @property
    def interactivity(self):
        """Correctly spelled alias of `interractivity`."""
        return self.interractivity

    @interactivity.setter
    def interactivity(self, value):
        self.interractivity = value

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
            entry = self.profData.get(fname)
            if entry is None :
                entry = self.profData[fname] = {"dt": 0., "dt_max": None, "dt_list": [],
                                                "dm_max": None, "dm_list": [],
                                                "nbCall": 0, "deep": set()}
            entry["nbCall"] += 1

            if outermost :
                entry["dt"] += deltaTime
                entry["deep"].add(self.deep[0])
                if entry["dt_max"] is None or deltaTime > entry["dt_max"] :
                    entry["dt_max"] = deltaTime
                if entry["dm_max"] is None or deltaMem > entry["dm_max"] :
                    entry["dm_max"] = deltaMem
                # count, sum and max above are exact; the lists only feed the
                # percentiles, so they are the part that gets capped
                if len(entry["dt_list"]) < self.max_samples :
                    entry["dt_list"].append(deltaTime)
                    entry["dm_list"].append(deltaMem)

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
            mem_peak_b = process.memory_info().peak_wset
        else :
            mem_peak_b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * RU_MAXRSS_UNIT
        mem_peak = bytes2human(mem_peak_b)
        return _ProfData({"global_run_time": run_time,
                          "global_run_time_s": run_time_s,
                          "memory_peak": mem_peak,
                          "memory_peak_b": mem_peak_b})
    
    def _write(self, toprint, end='\n'):
        """print(), but never raise on a console that cannot represent ⚡
        (cp1252 on Windows). One replacement char per character, so the columns
        stay aligned."""
        try :
            print(toprint, end=end)
        except UnicodeEncodeError:
            encoding = getattr(sys.stdout, "encoding", None) or "ascii"
            print(toprint.encode(encoding, "replace").decode(encoding), end=end)

    def _print(self, toprint, end='\n'):
        if self.logger:
            self.logger("  " + toprint)
        if self.forcePrintInCsl or not self.logger:
            self._write(" ⚡" + toprint, end=end)

    def print_line(self, fname, delta_time, delta_mem, end='\n', color=""):
        delta_mem_str = " Δ " + f"{delta_mem:>7}"
        if fname in self.profThread.keys():
            mmax = 0.
            if fname in self.profData.keys(): 
                mmax = self.profData[fname]["dm_max"] or 0
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

    def _time_stat(self, val, name):
        if name == "mean" :
            return val["dt"] / val["nbCall"]
        if name == "max" :
            return val["dt_max"] or 0.
        if name == "median" :
            return statistics.median(val["dt_list"]) if val["dt_list"] else 0.
        return _percentile(val["dt_list"], 0.95)

    def __strMaxMemory(self, key, rbytes=False):
        val = self.profData[key]
        mmax = val["dm_max"] or 0
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
            str += f" customProfiler log : global timer {ggi['global_run_time']} / memory peak {ggi['memory_peak']:^10}"
            # str += f"\n ⚡ {'':^45} | {'':7} | {'time':^29} | {'mem. consumption':^17}"
            str += "\n " + "⚡" * 8
            stats = self.summary_time
            time_header = "  time : " + " / ".join(stats) + " / global"
            time_width = 13 * (len(stats) + 1) + 3 * len(stats)

            str += (f"\n ⚡ {'fct name':^45} | {'Nb call':7} | " +
                    f"{time_header:<{time_width}} | {'mem. max :  Δ / Th':^17}")
            str += "\n ⚡ "+ "="*(108 + time_width - 29)
            for key, val in self.profData.items():
                t_str = _fixed_width_time(val["dt"])
                cells = [_fixed_width_time(self._time_stat(val, name)) for name in stats]

                dp = sorted(val["deep"])
                dp_str = ''.join(["+" if i in dp else "-" for i in range(4)])

                str += f"\n ⚡ {dp_str} {key: ^40.40} | {val['nbCall']:^7} "
                str += "| " + " / ".join(cells + [t_str]) + " "
                strmen = bytes2human(val["dm_max"] or 0)
                strmaxmem = self.__strMaxMemory(key)
                str += f"| {strmen:>7}  / {strmaxmem:>7}"
            str += "\n " + "⚡" * 8
        else :
            str = ("\n " + "⚡" * 2 + f" customProfiler log : global timer {ggi['global_run_time']} / max memory use {ggi['memory_peak']:^10}")
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
            self._write(str(self))

    def __getitem__(self, key):
        try :
            val = self.profData[key]
        except KeyError:
            raise KeyError(f"key avail in collecteur : {list(self.profData.keys())}")

        return _ProfData({"nb_call": val['nbCall'],
                          "global_time": htd(val["dt"]),
                          "global_time_s": val["dt"],
                          "mean_time": htd(val["dt"]/val['nbCall']),
                          "mean_time_s": val["dt"]/val['nbCall'],
                          "max_time": htd(val["dt_max"] or 0.),
                          "max_time_s": val["dt_max"] or 0.,
                          "median_time_s": statistics.median(val["dt_list"]) if val["dt_list"] else 0.,
                          "p95_time_s": _percentile(val["dt_list"], 0.95),
                          "per_call_time_s": list(val["dt_list"]),
                          "max_memory": bytes2human(val['dm_max'] or 0),
                          "max_memory_b": val['dm_max'] or 0,
                          "per_call_memory_b": list(val['dm_list']),
                          "peak_memory": self.__strMaxMemory(key),
                          "peak_memory_b": self.__strMaxMemory(key, rbytes=True)})

    def options(self
                , interactivity = _UNSET
                , use_logger = _UNSET
                , logger_name = _UNSET
                , add_custom_level = _UNSET
                , profiler_level = _UNSET
                , force_print_in_console = _UNSET
                , no_summary_in_log = _UNSET
                , refresh_interval = _UNSET
                , max_samples = _UNSET
                , summary_time = _UNSET
                , **legacy):
        """Change the options you pass, and leave the others alone."""

        given = {"interactivity": interactivity,
                 "use_logger": use_logger,
                 "logger_name": logger_name,
                 "add_custom_level": add_custom_level,
                 "profiler_level": profiler_level,
                 "force_print_in_console": force_print_in_console,
                 "no_summary_in_log": no_summary_in_log,
                 "refresh_interval": refresh_interval,
                 "max_samples": max_samples,
                 "summary_time": summary_time}

        for old_name, new_name in _LEGACY_OPTIONS.items():
            if old_name in legacy :
                warnings.warn(f"options({old_name}=...) is deprecated, use {new_name}",
                              DeprecationWarning, stacklevel=2)
                given[new_name] = legacy.pop(old_name)
        if legacy :
            raise TypeError(f"options() got an unexpected keyword argument '{sorted(legacy)[0]}'")

        if given["interactivity"] is not _UNSET :
            value = given["interactivity"]
            assert value in get_ENUM_list(Interactivity), f'interactivity {value} must be in Interactivity : {get_ENUM_list(Interactivity)}'
            if value == Interactivity.AUTO :
                if sys.stdout.isatty():
                    value = Interactivity.ENABLE
                else :
                    value = Interactivity.MF_NO_INTERAC
            self.interractivity = str(Interactivity(value).value)

        if given["force_print_in_console"] is not _UNSET :
            self.forcePrintInCsl = given["force_print_in_console"]
        if given["no_summary_in_log"] is not _UNSET :
            self.noSummaryInLog = given["no_summary_in_log"]
        if given["logger_name"] is not _UNSET :
            self.loggername = given["logger_name"]
        if given["refresh_interval"] is not _UNSET :
            value = given["refresh_interval"]
            assert isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0, \
                f'refresh_interval {value} must be a number of seconds > 0'
            self.refresh_interval = float(value)
        if given["max_samples"] is not _UNSET :
            value = given["max_samples"]
            assert isinstance(value, int) and not isinstance(value, bool) and value > 0, \
                f'max_samples {value} must be an int > 0'
            self.max_samples = value
        if given["summary_time"] is not _UNSET :
            value = given["summary_time"]
            if isinstance(value, str) :
                value = (value,)
            value = tuple(value)
            assert value and all(name in SUMMARY_TIME_STATS for name in value), \
                f'summary_time {value} must be one or more of {SUMMARY_TIME_STATS}'
            self.summary_time = value

        if given["use_logger"] is not _UNSET :
            if given["use_logger"] :
                add_custom_level = given["add_custom_level"]
                if add_custom_level is _UNSET :
                    add_custom_level = True
                profiler_level = given["profiler_level"]
                if profiler_level is _UNSET :
                    profiler_level = 25
                self._enable_logger(add_custom_level, profiler_level)
            else :
                self.logger = None

    def _enable_logger(self, add_custom_level, profiler_level):
        # the interactive line rewrites itself with \r: unusable in a log file
        if self.interractivity == Interactivity.ENABLE :
            self.interractivity = str(Interactivity.MF_NO_INTERAC.value)

        if add_custom_level :
            self.lvl = 'PROFILER'
            if not hasattr(logging, self.lvl) :  # adding it twice raises
                add_logging_level(self.lvl, profiler_level)
        else :
            self.lvl = 'INFO'

        logging.getLogger().setLevel(self.lvl)
        self.logger = getattr(logging.getLogger(self.loggername), self.lvl.lower())

    # --- mapping interface ---------------------------------------------------

    def __len__(self):
        return len(self.profData)

    def __iter__(self):
        return iter(list(self.profData))

    def __contains__(self, key):
        return key in self.profData

    def keys(self):
        return list(self.profData)

    def items(self):
        return [(key, self[key]) for key in self.profData]

    def values(self):
        return [self[key] for key in self.profData]

    def to_dict(self):
        """Everything collected so far, as plain dicts."""
        return {"global_info": dict(self.get_global_info()),
                "profiled": {key: dict(self[key]) for key in list(self.profData)}}

    def reset(self):
        """Drop every measurement collected so far, to profile the next phase on
        its own. The global timer keeps running."""
        with self._lock :
            self.profData = OrderedDict()
            self.profThread = OrderedDict()
        self._local.deep = [-1, -1]
        self._local.active = {}
