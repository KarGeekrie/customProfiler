"""Time and memory profiler.

    from custom_profiler import profiler, profiler_lbl, magic_profiler
    from custom_profiler import profiler_collecteur

Set ``CUSTOM_PROFILER=0`` in the environment to strip the decorators entirely.
"""

from typing import Any, Callable, Optional, TypeVar, Union

from custom_profiler import _profiler
from custom_profiler import collecteur
from custom_profiler.collecteur import Interactivity, INTERACTIVITY_OPT_ENUM

try:
    from importlib.metadata import PackageNotFoundError, version as _version
    try:
        __version__ = _version("custom_profiler")
    except PackageNotFoundError:  # running from a source tree, not installed
        __version__ = "0.0.0.dev0"
except ImportError:  # pragma: no cover - python < 3.8
    __version__ = "0.0.0.dev0"

__all__ = ["profiler", "profiler_lbl", "magic_profiler", "profiler_collecteur",
           "Interactivity", "INTERACTIVITY_OPT_ENUM", "__version__"]

F = TypeVar("F", bound=Callable[..., Any])

magic_profiler = _profiler.magic_profiler


def profiler(func: Optional[F] = None, *,
             name: Optional[str] = None) -> Union[F, Callable[[F], F]]:
    """Profile a function's time and memory.

    Usable bare (``@profiler``) or called (``@profiler(name="my label")``).
    """
    return _profiler.profiler(func, name=name, linePerline=False)


def profiler_lbl(func: Optional[F] = None, *,
                 name: Optional[str] = None) -> Union[F, Callable[[F], F]]:
    """Profile a function line by line. No memory peak in this mode."""
    return _profiler.profiler(func, name=name, linePerline=True)


profiler_collecteur = collecteur.profiler_collecteur()
profiler_collecteur.options(interactivity=Interactivity.AUTO)
