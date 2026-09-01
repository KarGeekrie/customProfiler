"""Deprecated alias for :mod:`custom_profiler._logging`.

Kept so ``from custom_profiler.custum_logger import ...`` keeps working.
Scheduled for removal in 2.0.
"""

import warnings

from custom_profiler._logging import add_logging_level

warnings.warn("custom_profiler.custum_logger is deprecated, "
              "use custom_profiler._logging",
              DeprecationWarning, stacklevel=2)
