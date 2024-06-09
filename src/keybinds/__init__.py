from functools import wraps
from typing import Any, cast

from mods_base import EInputEvent, KeybindType, hook
from mods_base.keybinds import KeybindBlockSignal, KeybindCallback_Event, KeybindCallback_NoArgs
from mods_base.mod_list import base_mod
from mods_base.raw_keybinds import (
    RawKeybind,
    RawKeybindCallback_EventOnly,
    RawKeybindCallback_KeyAndEvent,
    RawKeybindCallback_KeyOnly,
    RawKeybindCallback_NoArgs,
)
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

base_mod.components.append(base_mod.ComponentInfo("Keybinds", __version__))

active_raw_keybinds: list[RawKeybind] = []
active_keybinds: list[KeybindType] = []


def process_raw_bind(key: str, event: EInputEvent) -> KeybindBlockSignal:
    """
    Processes a raw keybind event.

    Args:
        key: The key which was pressed.
        event: What type this event is.
    Return:
        If to block
    """
    block: KeybindBlockSignal = None
    for bind in active_raw_keybinds:
        if bind.key is None:
            if bind.event is None:
                block = cast(RawKeybindCallback_KeyAndEvent, bind.callback)(key, event) or block
            else:
                block = cast(RawKeybindCallback_KeyOnly, bind.callback)(key) or block
        elif bind.event is None:
            block = cast(RawKeybindCallback_EventOnly, bind.callback)(event) or block
        else:
            block = cast(RawKeybindCallback_NoArgs, bind.callback)() or block
    return block


@hook("WillowGame.WillowUIInteraction:InputKey", Type.PRE)
def ui_interaction_input_key(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> Block | type[Block] | None:
    key: str = args.Key
    event: EInputEvent = args.Event

    # print("ui", key, event)

    block = process_raw_bind(key, event)
    if block is not None:
        return block

    block: KeybindBlockSignal = None
    for bind in active_keybinds:
        if bind.key != key:
            continue
        if bind.event_filter == event:
            block = cast(KeybindCallback_NoArgs, bind.callback)() or block
        elif bind.event_filter is None:
            block = cast(KeybindCallback_Event, bind.callback)(event) or block

    return block


@hook("WillowGame.WillowGameViewportClient:InputKey", Type.PRE)
def game_viewport_input_key(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> Block | type[Block] | None:
    if obj.ViewportConsole.bCaptureKeyInput:
        return None

    key: str = args.Key
    event: EInputEvent = args.EventType

    print("viewport", key, event)

    return process_raw_bind(key, event)


ui_interaction_input_key.enable()
# game_viewport_input_key.enable()


@wraps(KeybindType.enable)
def enable_keybind(self: KeybindType) -> None:
    if self not in active_keybinds:
        active_keybinds.append(self)


@wraps(KeybindType.disable)
def disable_keybind(self: KeybindType) -> None:
    active_keybinds.remove(self)


@wraps(RawKeybind.enable)
def enable_raw_keybind(self: RawKeybind) -> None:
    if self not in active_raw_keybinds:
        active_raw_keybinds.append(self)


@wraps(RawKeybind.disable)
def disable_raw_keybind(self: RawKeybind) -> None:
    active_raw_keybinds.remove(self)


KeybindType.enable = enable_keybind
KeybindType.disable = disable_keybind

RawKeybind.enable = enable_raw_keybind
RawKeybind.disable = disable_raw_keybind
