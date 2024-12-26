# ruff: noqa: N802, N803, D102, D103, N999

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, ClassVar

from legacy_compat import legacy_compat
from mods_base import EInputEvent, KeybindType
from mods_base.keybinds import KeybindCallback_Event, KeybindCallback_NoArgs

from .DeprecationHelper import Deprecated, PrintWarning

if TYPE_CHECKING:
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


def convert_new_style_callbacks(
    bind: Keybind,
    mod: "SDKMod | None" = None,
) -> tuple[KeybindCallback_Event | KeybindCallback_NoArgs | None, EInputEvent | None]:
    """
    Converts a legacy keybind to a new-style callback and event filter.

    Args:
        bind: The legacy keybind.
        mod: The legacy mod object to send change callbacks to.
    Returns:
        A tuple of the callback and the event filter.
    """

    # Man this is awful
    if bind.OnPress is not None:
        if len(inspect.signature(bind.OnPress).parameters) < 1:

            def on_press_no_event() -> None:
                with legacy_compat():
                    bind.OnPress()  # type: ignore

            return on_press_no_event, EInputEvent.IE_Pressed
        else:  # noqa: RET505

            def on_press_event(event: EInputEvent) -> None:
                with legacy_compat():
                    bind.OnPress(InputEvent(event))  # type: ignore

            return on_press_event, None
    elif mod is not None:
        game_input = functools.partial(mod.GameInputPressed, bind)

        if len(inspect.signature(game_input).parameters) < 1:

            def game_input_no_event() -> None:
                with legacy_compat():
                    game_input()  # type: ignore

            return game_input_no_event, EInputEvent.IE_Pressed
        else:  # noqa: RET505

            def game_input_event(event: EInputEvent) -> None:
                with legacy_compat():
                    game_input(InputEvent(event))

            return game_input_event, None
    else:
        return None, EInputEvent.IE_Pressed


def convert_to_new_style_keybind(
    bind: Keybind | list[str],
    mod: "SDKMod | None" = None,
) -> KeybindType:
    """
    Converts a legacy keybind, of either type, to a new-style keybind.

    Args:
        bind: The legacy keybind.
        mod: The legacy mod object to send change callbacks to.
    Returns:
        The new-style keybind.
    """

    if isinstance(bind, Keybind):

        def set_key(new_key: str | None) -> None:
            bind.Key = new_key or "None"
    else:
        PrintWarning(Keybind._list_deprecation_warning)  # pyright: ignore[reportPrivateUsage]

        def set_key(new_key: str | None) -> None:
            return bind.__setitem__(1, new_key or "None")

        bind = Keybind(bind[0], bind[1])

    callback, event_filter = convert_new_style_callbacks(bind, mod)

    new_bind = KeybindType(
        bind.Name,
        None if bind.Key == "None" else bind.Key,
        callback,
        is_hidden=bind.IsHidden,
        is_rebindable=bind.IsRebindable,
        event_filter=event_filter,
    )
    new_bind._rebind = set_key  # pyright: ignore[reportPrivateUsage]
    new_bind.default_key = None if bind.DefaultKey == "None" else bind.DefaultKey
    return new_bind
