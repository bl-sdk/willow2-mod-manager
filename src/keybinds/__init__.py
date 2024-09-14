from functools import wraps
from typing import TYPE_CHECKING, Any

from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import EInputEvent, KeybindType, hook
from mods_base.mod_list import base_mod

if TYPE_CHECKING:
    from mods_base.keybinds import KeybindCallback_Event, KeybindCallback_NoArgs

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

base_mod.components.append(base_mod.ComponentInfo("Keybinds", __version__))

active_keybinds: list[KeybindType] = []


@hook("WillowGame.WillowUIInteraction:InputKey", Type.PRE)
def ui_interaction_input_key(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> None:
    key: str = args.Key
    event: EInputEvent = args.Event

    for bind in active_keybinds:
        if bind.key != key:
            continue
        if bind.event_filter == event:
            callback_no_args: KeybindCallback_NoArgs = bind.callback  # type: ignore
            callback_no_args()
        elif bind.event_filter is None:
            callback_event: KeybindCallback_Event = bind.callback  # type: ignore
            callback_event(event)


ui_interaction_input_key.enable()


@wraps(KeybindType.enable)
def enable_keybind(self: KeybindType) -> None:
    if self not in active_keybinds:
        active_keybinds.append(self)


@wraps(KeybindType.disable)
def disable_keybind(self: KeybindType) -> None:
    active_keybinds.remove(self)


KeybindType.enable = enable_keybind
KeybindType.disable = disable_keybind
