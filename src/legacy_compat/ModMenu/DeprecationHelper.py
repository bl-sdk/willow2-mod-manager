import unrealsdk
import functools
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

__all__: Tuple[str, ...] = (
    "Deprecated",
    "NameChangeMsg",
    "PrintWarning",
)

_printed_deprecation_warnings: Set[str] = set()


def PrintWarning(msg: str) -> None:
    """
    Prints a warning containing the provided message. Will only happen once per message.

    Args:
        msg: The message to print.
    """
    if msg not in _printed_deprecation_warnings:
        _printed_deprecation_warnings.add(msg)
        unrealsdk.Log(f"[Warning] {msg}")


def NameChangeMsg(old_name: str, new_name: str) -> str:
    """
    Helper returning a generic deprecation message for when something's name changed.

    Args:
        old_name: The deprecated name.
        new_name: The new name.
    Returns:
        The name change deprecation message.
    """
    return f"Use of '{old_name}' is deprecated, use '{new_name}' instead."


def Deprecated(
    msg: str,
    func: Optional[Callable[..., Any]] = None
) -> Callable[..., Any]:
    """
    Decorator that prints a deprecation message when it's wrapped function is called.

    Can also be called with the function as an argument.

    Args:
        msg: The message to print.
        func: The function to wrap.
    Returns:
        The wrapped function
    """
    def decorator(old_func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(old_func)
        def new_func(*args: List[Any], **kwargs: Dict[str, Any]) -> Any:
            PrintWarning(msg)
            return old_func(*args, **kwargs)
        return new_func

    if func is None:
        return decorator
    else:
        return decorator(func)
