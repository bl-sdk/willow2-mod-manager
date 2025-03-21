import contextlib
import inspect
from collections.abc import Callable, Sequence
from typing import Any

from unrealsdk import logging

from mods_base import BaseOption, GroupedOption, Mod, NestedOption
from save_options.options import SaveOption

# Allowing GroupedOption and NestedOption if all their children are SaveOption
ModSaveOptions = dict[str, BaseOption]
registered_save_options: dict[str, ModSaveOptions] = {}

SaveCallback = Callable[[], None]
save_callbacks: dict[str, SaveCallback] = {}

LoadCallback = Callable[[], None]
load_callbacks: dict[str, LoadCallback] = {}

registered_mods: dict[str, Mod] = {}


def _treat_as_save_option(obj: Any) -> bool:
    """
    Determines whether an object should be treated as a save option.

    - If the object is an instance of SaveOption, returns True.
    - If the object is a GroupedOption or NestedOption, recursively checks all children:
        - If all children are considered SaveOptions, returns True.
        - If only some children are SaveOptions (partial mix), logs an error indicating that the
          option contains a mix of regular BaseOption and SaveOption children, and that SaveOption
          instances will be ignored.
    - Otherwise, returns False.

    Args:
        obj: The object to evaluate.

    Returns:
        bool: True if the object or its children should be treated as SaveOption, False otherwise.
    """

    if isinstance(obj, SaveOption):
        return True
    if isinstance(obj, GroupedOption | NestedOption):
        if all(_treat_as_save_option(child) for child in obj.children):
            return True
        if any(_treat_as_save_option(child) for child in obj.children):
            logging.dev_warning(
                f"Option {obj.identifier} has both regular BaseOption and SaveOption"
                f" defined as children. SaveOption instances will be ignored.",
            )
    return False


def register_save_options(  # noqa: C901, D417
    mod: Mod,
    *,
    save_options: Sequence[BaseOption] | None = None,
    on_save: Callable[[], None] | None = None,
    on_load: Callable[[], None] | None = None,
    mod_identifier: str | None = None,
) -> Mod:
    """
    Registers save options and save/load callbacks.

    Positional arg:
        mod: The Mod instance.

    Keyword Args:
        save_options: A sequence of SaveOption instances to register.
        on_save: A callback to run any time the game is saved. Intended usage is to update
                 SaveOption values before they are written to the save file.
        on_load: A callback to run immediately after player's save data is applied to the player
                 upon entering the game. Intended use is to apply loaded SaveOption values to the
                 player.
        mod_identifier: A string to identify the mod in the save file.

    The above keyword args are gathered in two ways, in order of priority:
    - Args directly to this function
    - Variables in the calling module's scope

    Arg            | Module Scope
    ---------------|---------------------
    save_options   | SaveOption instances
    on_save        | on_save
    on_load        | on_load
    mod_identifier | module.__name__
    """

    # Get calling module and identifier
    module = inspect.getmodule(inspect.stack()[1].frame)
    if module is None:
        raise ValueError("Unable to find calling module when registering save options!")

    if not mod_identifier:
        mod_identifier = module.__name__

    # Maintaining a registry of mods that call this so that we can identify which mods are enabled
    # when it's time to call the callbacks.
    registered_mods[mod_identifier] = mod

    new_save_options: list[BaseOption] = []
    # Use save_options if provided, otherwise do a module search.
    if save_options is not None:
        for option in save_options:
            if _treat_as_save_option(option):
                new_save_options.append(option)
            else:
                logging.dev_warning(f"Cannot register {option} as a SaveOption")
    else:
        for _, value in inspect.getmembers(module):
            if isinstance(value, GroupedOption | NestedOption):
                logging.dev_warning(
                    f"{module.__name__}: {type(value).__name__} instances must be explicitly"
                    f" specified in the options list!",
                )
            elif _treat_as_save_option(value):
                new_save_options.append(value)

    registered_save_options[mod_identifier] = {
        save_opt.identifier: save_opt for save_opt in new_save_options
    }

    # Register on_save callback. Module search if not given as an arg.
    if on_save is None:
        with contextlib.suppress(AttributeError):
            save_callbacks[mod_identifier] = module.on_save
    else:
        save_callbacks[mod_identifier] = on_save

    # Register on_load callback. Module search if not given as an arg.
    if on_load is None:
        with contextlib.suppress(AttributeError):
            load_callbacks[mod_identifier] = module.on_load
    else:
        load_callbacks[mod_identifier] = on_load

    return mod
