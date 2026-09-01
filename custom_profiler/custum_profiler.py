"""Deprecated alias for :mod:`custom_profiler._profiler`.

Kept so ``from custom_profiler.custum_profiler import ...`` keeps working.
Scheduled for removal in 2.0.
"""

import warnings

from custom_profiler._profiler import (profC, profiler, magic_profiler, task,
                                       thread_mananger, POLL_S, REFRESH_S)

warnings.warn("custom_profiler.custum_profiler is deprecated, "
              "use custom_profiler._profiler (or the package root)",
              DeprecationWarning, stacklevel=2)
