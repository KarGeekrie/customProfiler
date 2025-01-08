from . import custum_profiler
from . import collecteur

from functools import partial

profiler = partial(custum_profiler.profiler, linePerline=False)
profiler_lbl = partial(custum_profiler.profiler, linePerline=True)
magic_profiler = custum_profiler.magic_profiler
profiler_collecteur = collecteur.profiler_collecteur()
INTERACTIVITY_OPT_ENUM = collecteur.INTERACTIVITY_OPT_ENUM
profiler_collecteur.options(interractivity = INTERACTIVITY_OPT_ENUM.AUTO)