from collections.abc import Callable
from dataclasses import dataclass
from typing import overload

from unrealsdk import logging

from .keybinds import EInputEvent, KeybindBlockSignal

__all__: tuple[str, ...] = (
    "add",
    "pop",
    "push",
)

"""
This module allows for raw access to all key events. It is intended for short term use, to
temporarily add some extra callbacks, primarily to help enhance menus.

Raw keybinds work off of a stack. The top of the stack represents the currently focused menu, only
callbacks within it are processed. On opening a new menu, with different focus, you should push a
new frame, and register callbacks within it. On closing a menu, you should pop it's frame.

Raw keybinds follow the standard blocking logic when multiple callbacks receive the same event. Raw
keybinds are processed *before* gameplay keybinds, so a raw keybind specifying to block the input
will prevent any matching gameplay keybinds from being run.
"""

type RawKeybindCallback_KeyAndEvent = Callable[[str, EInputEvent], KeybindBlockSignal]
type RawKeybindCallback_KeyOnly = Callable[[str], KeybindBlockSignal]
type RawKeybindCallback_EventOnly = Callable[[EInputEvent], KeybindBlockSignal]
type RawKeybindCallback_NoArgs = Callable[[], KeybindBlockSignal]

type RawKeybindCallback_Any = (
    RawKeybindCallback_KeyAndEvent
    | RawKeybindCallback_KeyOnly
    | RawKeybindCallback_EventOnly
    | RawKeybindCallback_NoArgs
)
type RawKeybindDecorator_Any = (
    Callable[[RawKeybindCallback_KeyAndEvent], None]
    | Callable[[RawKeybindCallback_KeyOnly], None]
    | Callable[[RawKeybindCallback_EventOnly], None]
    | Callable[[RawKeybindCallback_NoArgs], None]
)


@dataclass
class RawKeybind:
    key: str | None
    event: EInputEvent | None
    callback: RawKeybindCallback_Any

    # These two functions should get replaced by the keybind implementation
    # The initialization script should make sure to load it before any mods, to make sure they don't
    # end up with references to these functions
    def enable(self) -> None:
        """Enables this keybind."""
        logging.error("No keybind implementation loaded, unable to enable binds")

    def disable(self) -> None:
        """Disables this keybind."""
        logging.error("No keybind implementation loaded, unable to disable binds")


raw_keybind_callback_stack: list[list[RawKeybind]] = []


def push() -> None:
    """Pushes a new raw keybind frame."""
    raw_keybind_callback_stack.append([])


def pop() -> None:
    """Pops the current raw keybind frame."""
    frame = raw_keybind_callback_stack.pop()
    for bind in frame:
        bind.disable()


@overload
def add(
    key: str,
    event: EInputEvent,
    callback: RawKeybindCallback_NoArgs,
) -> None: ...


@overload
def add(
    key: str,
    event: None,
    callback: RawKeybindCallback_EventOnly,
) -> None: ...


@overload
def add(
    key: None,
    event: EInputEvent,
    callback: RawKeybindCallback_KeyOnly,
) -> None: ...


@overload
def add(
    key: None,
    event: None,
    callback: RawKeybindCallback_KeyAndEvent,
) -> None: ...


@overload
def add(
    key: str,
    event: EInputEvent = EInputEvent.IE_Pressed,
    callback: None = None,
) -> Callable[[RawKeybindCallback_NoArgs], None]: ...


@overload
def add(
    key: str,
    event: None = None,
    callback: None = None,
) -> Callable[[RawKeybindCallback_EventOnly], None]: ...


@overload
def add(
    key: None,
    event: EInputEvent = EInputEvent.IE_Pressed,
    callback: None = None,
) -> Callable[[RawKeybindCallback_KeyOnly], None]: ...


@overload
def add(
    key: None,
    event: None = None,
    callback: None = None,
) -> Callable[[RawKeybindCallback_KeyAndEvent], None]: ...


def add(
    key: str | None,
    event: EInputEvent | None = EInputEvent.IE_Pressed,
    callback: RawKeybindCallback_Any | None = None,
) -> RawKeybindDecorator_Any | None:
    """
    Adds a new raw keybind callback in the current frame.

    Args:
        key: The key to filter to, or None to be passed all keys.
        event: The event to filter to, or None to be passed all events.
        callback: The callback to run. If None, this function acts as a decorator factory,
    Returns:
        If the callback was not explicitly provided, a decorator to register it.
    """

    def decorator(callback: RawKeybindCallback_Any) -> None:
        bind = RawKeybind(key, event, callback)
        raw_keybind_callback_stack[-1].append(bind)
        bind.enable()

    if callback is None:
        return decorator
    return decorator(callback)
