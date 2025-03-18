from dataclasses import dataclass
from typing import Any

from unrealsdk import make_struct
from unrealsdk.hooks import Type, prevent_hooking_direct_calls

from mods_base import (
    JSON,
    BoolOption,
    ButtonOption,
    HiddenOption,
    SliderOption,
    SpinnerOption,
    ValueOption,
    get_pc,
    hook,
)

any_option_changed: bool = False


def can_save() -> bool:
    """Checks if a character is loaded that we can save to."""
    pc = get_pc()
    if not pc:
        return False
    cached_save = pc.GetCachedSaveGame()
    # SaveGameId of -1 is used when a new game is selected but user exits before starting the game
    return not (not cached_save or cached_save.SaveGameId == -1)


def trigger_save() -> None:
    """
    Trigger a save game that stores our current save option values.

    When in the main menu, this will just overwrite the save options values and leave the rest of
    the save untouched. When in game, pc.SaveGame() is called and the save game is generated from
    the current state as usual.
    """

    if not can_save():
        return

    pc = get_pc()
    # When in game, just use standard machinery to save
    if pc.MyWillowPawn:
        pc.SaveGame()
        return

    # When not in game, we need to load from file to get full save. Cached save game is partial.
    save_manager = pc.GetWillowGlobals().GetWillowSaveGameManager()
    setattr(save_manager, "__OnLoadComplete__Delegate", save_manager.OnLoadComplete)

    # Loading the save game is an async operation, we need to hook OnLoadComplete to have access
    # to the result
    @hook(
        "WillowGame.WillowSaveGameManager:OnLoadComplete",
        Type.POST,
        immediately_enable=True,
    )
    def on_load_complete(*_: Any) -> None:
        on_load_complete.disable()
        setattr(save_manager, "__OnLoadComplete__Delegate", None)
        # Need to prevent our hook on EndLoadGame to avoid reloading previous save option values
        with prevent_hooking_direct_calls():
            player_save_game = save_manager.EndLoadGame(
                pc.GetMyControllerId(),
                make_struct("LoadInfo"),
                0,
            )[0]
        save_manager.SaveGame(
            pc.GetMyControllerId(),
            player_save_game,
            save_manager.LastLoadedFilePath,
            -1,
        )

    save_manager.BeginLoadGame(pc.GetMyControllerId(), save_manager.LastLoadedFilePath, -1)


class SaveOptionMeta(type(ValueOption)):
    """
    Metaclass to create save option classes.

    Enforces that usages of SaveOption are always paired with a subclass of ValueOption, with
    SaveOption coming first.
    """

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        super().__init__(name, bases, namespace)

        # Ignore itself
        if not bases:
            return

        # Ensure SaveOption comes before ValueOption in the inheritance
        base_names = [base.__name__ for base in bases]
        if "SaveOption" in base_names:
            index_saveoption = base_names.index("SaveOption")

            if not any(
                issubclass(bases[i], ValueOption) for i in range(index_saveoption + 1, len(bases))
            ):
                raise TypeError(
                    f"Class {name} must inherit from {SaveOption.__name__} before"
                    f" {ValueOption.__name__}",
                )


@dataclass
class SaveOption(metaclass=SaveOptionMeta):
    """
    Mixin class to make an option per-save, and disguise it as a button when saves are unavailable.

    Must be inherited from *before* BaseOption, i.e.
        class MySaveOption(SaveOption, SliderOption): ...
    """

    def __setattr__(self, name: str, value: Any) -> None:
        # Overriding __setattr__ from ValueOption so that we can set our var to tell if a value
        # has been changed, which is then used to save the file when we leave the options menu.

        # This calls the version from ValueOption due to Python's MRO. Our metaclass ensures that
        # we're paired with ValueOption
        super().__setattr__(name, value)

        # We're editing this var to track if an option has changed since the last time the game
        # was saved. Saving when the menu closes instead of on change of each item.
        global any_option_changed
        any_option_changed = True

    def __getattribute__(self, item: str) -> Any:
        # The __class__ variable is whatever the main class in most cases, and a ButtonOption
        # when we can't save. ButtonOption implements only on_press and __call__ from BaseOption.
        # We don't need the latter since it will be overridden by whatever ValueOption this is
        # mixed with.
        if can_save():
            return super().__getattribute__(item)
        if item == "__class__":
            return ButtonOption
        if item == "description":
            return "Per save setting not available without a character loaded"
        if item == "on_press":
            return None
        return super().__getattribute__(item)


@dataclass
class HiddenSaveOption[J: JSON](SaveOption, HiddenOption[J]):
    """
    A generic save option which is always hidden.

    Use this to persist arbitrary (JSON-encodable) data in the character save file. This class
    is explicitly intended to be modified programmatically, unlike the other options
    which are generally only modified by the mod menu.

    Args:
        identifier: The option's identifier.
        value: The option's value.
    Keyword Args:
        display_name: The option name to use for display. Defaults to copying the identifier.
        description: A short description about the option.
        description_title: The title of the description. Defaults to copying the display name.
    Extra Attributes:
        is_hidden: Always true.
        mod: The mod this option stores it's settings in, or None if not (yet) associated with one.
    """

    def save(self) -> None:
        """
        Base HiddenOption has a method to save mod settings.

        We're overriding to re-save the player save game and save our options on the character save
        file.
        """
        trigger_save()


@dataclass
class SliderSaveOption(SaveOption, SliderOption):
    """
    A save option selecting a number within a range.

    Value is stored on a per save basis when using this instead of the mod's settings file.

    Args:
        identifier: The option's identifier.
        value: The option's value.
        min_value: The minimum value.
        max_value: The maximum value.
        step: How much the value should move each step of the slider.
        is_integer: If True, the value is treated as an integer.
    Keyword Args:
        display_name: The option name to use for display. Defaults to copying the identifier.
        description: A short description about the option.
        description_title: The title of the description. Defaults to copying the display name.
        is_hidden: If true, the option will not be shown in the options menu.
        on_change: If not None, a callback to run before updating the value. Passed a reference to
                   the option object and the new value. May be set using decorator syntax.
    Extra Attributes:
        mod: The mod this option stores it's settings in, or None if not (yet) associated with one.
        default_value: What the value was originally when registered. Does not update on change.
    """


@dataclass
class SpinnerSaveOption(SaveOption, SpinnerOption):
    """
    A save option selecting one of a set of strings.

    Typically implemented as a spinner. Value is stored on a per save basis when using this
    instead of the mod's settings file.

    Also see DropDownSaveOption, which may be more suitable for larger numbers of choices.

    Args:
        identifier: The option's identifier.
        value: The option's value.
        choices: A list of choices for the value.
        wrap_enabled: If True, allows moving from the last choice back to the first, or vice versa.
    Keyword Args:
        display_name: The option name to use for display. Defaults to copying the identifier.
        description: A short description about the option.
        description_title: The title of the description. Defaults to copying the display name.
        is_hidden: If true, the option will not be shown in the options menu.
        on_change: If not None, a callback to run before updating the value. Passed a reference to
                   the option object and the new value. May be set using decorator syntax.
    Extra Attributes:
        mod: The mod this option stores it's settings in, or None if not (yet) associated with one.
        default_value: What the value was originally when registered. Does not update on change.
    """


@dataclass
class BoolSaveOption(SaveOption, BoolOption):
    """
    A save option toggling a boolean value.

    Typically implemented as an "on/off" spinner. Value is stored on a per save basis when using
    this instead of the mod's settings file.

    Args:
        identifier: The option's identifier.
        value: The option's value.
        true_text: If not None, overwrites the default text used for the True option.
        false_text: If not None, overwrites the default text used for the False option.
    Keyword Args:
        display_name: The option name to use for display. Defaults to copying the identifier.
        description: A short description about the option.
        description_title: The title of the description. Defaults to copying the display name.
        is_hidden: If true, the option will not be shown in the options menu.
        on_change: If not None, a callback to run before updating the value. Passed a reference to
                   the option object and the new value. May be set using decorator syntax.
    Extra Attributes:
        mod: The mod this option stores it's settings in, or None if not (yet) associated with one.
        default_value: What the value was originally when registered. Does not update on change.
    """
