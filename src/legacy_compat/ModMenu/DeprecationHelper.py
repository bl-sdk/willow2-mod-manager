# ruff: noqa: N802, D103, N999

import functools
import warnings
from collections.abc import Callable
from typing import Any

__all__: tuple[str, ...] = (
    "Deprecated",
    "NameChangeMsg",
    "PrintWarning",
)


def PrintWarning(msg: str) -> None:
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def NameChangeMsg(old_name: str, new_name: str) -> str:
    return f"Use of '{old_name}' is deprecated, use '{new_name}' instead."


def Deprecated(msg: str, func: Callable[..., Any] | None = None) -> Callable[..., Any]:
    def decorator(old_func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(old_func)
        def new_func(*args: Any, **kwargs: Any) -> Any:
            PrintWarning(msg)
            return old_func(*args, **kwargs)

        return new_func

    if func is None:
        return decorator
    return decorator(func)
