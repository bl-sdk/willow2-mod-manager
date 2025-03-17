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
    if isinstance(obj, SaveOption):
        return True
    if isinstance(obj, GroupedOption | NestedOption):
        if all(_treat_as_save_option(child) for child in obj.children):
            return True
        logging.error(
            f"Option {obj.identifier} has both regular BaseOption and SaveOption"
            f"defined as children. SaveOption instances will be ignored"  # noqa: COM812
        )
    return False


def register_save_options(  # noqa: D417
    mod: Mod,
    *,
    save_options: Sequence[BaseOption] | None = None,
    on_save: Callable[[], None] | None = None,
    on_load: Callable[[], None] | None = None,
    mod_identifier: str | None = None,
) -> None:
    """
    Registers save options - values stored on the save options are saved to the character save file.

    Positional arg:
        mod: The Mod instance.

    Keyword Args:
        save_options: A sequence of SaveOption instances to register. If None, variables in the
                      calling module's scope are searched, and any SaveOption found is appended.
        on_save: A callback to run any time the game is saved. Intended use is to update any
                 SaveOption values before they are written to the save file. If None, we search the
                calling module's scope for "on_save".
        on_load: A callback to run right after the player's save data is applied to the player upon
                 entering the game. Intended use is to apply any custom save option values to the
                 player. If None, we search the calling module's scope for "on_load".
        mod_identifier: A string to identify the mod in the save file. If None, module.__name__ is
                        used.
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
    # Grab any save options in mod.options. If a save option is in a nested or grouped option,
    # we are going to register the parent iff all children are save options. Otherwise we'll log
    # an error.
    if isinstance(mod, Mod): # type: ignore
        new_save_options.extend([option for option in mod.options if _treat_as_save_option(option)])

    # If save_options not given, module search for any other save options defined
    if save_options is None:
        new_save_options.extend(
            [value for _, value in inspect.getmembers(module) if _treat_as_save_option(value)],
        )
    else:
        for option in save_options:
            if _treat_as_save_option(option):
                new_save_options.append(option)
            else:
                logging.error(f"Cannot register {option} as a SaveOption")

    # If the same save_option is gathered twice above, this will deduplicate
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
