# ruff: noqa: N802, N803, D102, D103, N999

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, ClassVar

from mods_base import EInputEvent, KeybindType

from .DeprecationHelper import Deprecated, PrintWarning

if TYPE_CHECKING:
    from mods_base.keybinds import KeybindCallback_Event, KeybindCallback_NoArgs

    from .ModObjects import SDKMod

__all__: tuple[str, ...] = (
    "InputEvent",
    "Keybind",
    "KeybindCallback",
)


class InputEvent(IntEnum):
    Pressed = EInputEvent.IE_Pressed
    Released = EInputEvent.IE_Released
    Repeat = EInputEvent.IE_Repeat
    DoubleClick = EInputEvent.IE_DoubleClick
    Axis = EInputEvent.IE_Axis


KeybindCallback = Callable[[], None] | Callable[[InputEvent], None]


@dataclass
class Keybind:
    Name: str
    Key: str = "None"
    IsRebindable: bool = True
    IsHidden: bool = False

    OnPress: KeybindCallback | None = None

    DefaultKey: str = field(default=Key, init=False)

    _list_deprecation_warning: ClassVar[str] = (
        "Using lists for keybinds is deprecated, use 'ModMenu.Keybind' instances instead."
    )

    def __post_init__(self) -> None:
        self.DefaultKey = self.Key

    @Deprecated(_list_deprecation_warning)
    def __getitem__(self, i: int) -> str:
        if not isinstance(i, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"list indices must be integers or slices, not {type(i)}")
        if i == 0:
            return self.Name
        elif i == 1:  # noqa: RET505
            return self.Key
        else:
            raise IndexError("list index out of range")

    @Deprecated(_list_deprecation_warning)
    def __setitem__(self, i: int, val: str) -> None:
        if not isinstance(i, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"list indices must be integers or slices, not {type(i)}")
        if i == 0:
            self.Name = val
        elif i == 1:
            self.Key = val
        else:
            raise IndexError("list index out of range")


def convert_to_new_style_keybind(
    bind: Keybind | list[str],
    mod: "SDKMod | None" = None,
) -> KeybindType:
    if isinstance(bind, Keybind):

        def set_key(new_key: str | None) -> None:
            bind.Key = new_key or "None"
    else:
        PrintWarning(Keybind._list_deprecation_warning)  # pyright: ignore[reportPrivateUsage]

        def set_key(new_key: str | None) -> None:
            return bind.__setitem__(1, new_key or "None")

        bind = Keybind(bind[0], bind[1])

    callback: KeybindCallback_Event | KeybindCallback_NoArgs | None
    event_filter: EInputEvent | None

    # Man this is awful
    if bind.OnPress is not None:
        if len(inspect.signature(bind.OnPress).parameters) < 1:
            on_press_no_event: Callable[[], None] = bind.OnPress  # type: ignore
            callback = on_press_no_event
            event_filter = EInputEvent.IE_Pressed
        else:
            on_press_event: Callable[[InputEvent], None] = bind.OnPress  # type: ignore
            callback = lambda event: on_press_event(InputEvent(event))  # noqa: E731
            event_filter = None
    elif mod is not None:
        game_input = functools.partial(mod.GameInputPressed, bind)

        if len(inspect.signature(game_input).parameters) < 1:
            game_input_no_event: Callable[[], None] = game_input  # type: ignore
            callback = game_input_no_event
            event_filter = EInputEvent.IE_Pressed
        else:
            game_input_event: Callable[[InputEvent], None] = game_input  # type: ignore
            callback = lambda event: game_input_event(InputEvent(event))  # noqa: E731
            event_filter = None
    else:
        callback = None
        event_filter = EInputEvent.IE_Pressed

    new_bind = KeybindType(
        bind.Name,
        bind.Key,
        callback,
        is_hidden=bind.IsHidden,
        is_rebindable=bind.IsRebindable,
        event_filter=event_filter,
    )
    new_bind._rebind = set_key  # pyright: ignore[reportPrivateUsage]
    return new_bind
