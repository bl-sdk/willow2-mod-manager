import save_options.hooks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from mods_base.mod_list import base_mod
from save_options.options import (
    BoolSaveOption,
    DropdownSaveOption,
    HiddenSaveOption,
    KeybindSaveOption,
    SaveOption,
    SliderSaveOption,
    SpinnerSaveOption,
)
from save_options.registration import register_save_options

__all__: tuple[str, ...] = (
    "BoolSaveOption",
    "DropdownSaveOption",
    "HiddenSaveOption",
    "KeybindSaveOption",
    "SaveOption",
    "SliderSaveOption",
    "SpinnerSaveOption",
    "__author__",
    "__version__",
    "__version_info__",
    "register_save_options",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

"""
This library allows for any arbitrary JSON encodable data to be saved in the character's save
file. You will manage the data that will be written to the save file by storing values in special
SaveOption objects. These objects all inherit from ValueOption objects as defined in mods_base,
but provide some additional functionality:

- Values from the options will be saved to and loaded from the character save files. If the option
  is also registered in the mod as a regular option (i.e., in Mod.options), the options will also
  save to the mod's settings file. These values will be loaded for any character that has not had
  any values saved yet. If you don't want a save option to be stored in the mod settings file, make
  sure it is not added to Mod.options.

- When no player save is available (main menu with no character), the options behave as button
  options, with a message showing that a player needs to be loaded.

If you have custom option subclasses, you can turn any of them into a save option simply by
also inheriting from the SaveOption mixin class. Note you only need to do this for ValueOptions -
the base GroupedOption/NestedOption classes are treated as containers already, and ButtonOptions
would have no effect.

Two optional callbacks can be defined:
- on_save: runs before the save file is written. You can use this callback to do any just-in-time
  updates of the save entries (e.g., get data from the WPC that you would like saved).

- on_load: runs immediately after regular save data is applied to the character upon loading into
  the game.

Example usage for saving anarchy stacks:
```
anarchy_save_option = HiddenSaveOption("anarchy", 0)
def on_save():
    anarchy_save_option.value = get_anarchy_stacks()

def on_load():
    set_anarchy_stacks(anarchy_save_option.value)

mod = build_mod()
register_save_options(mod)
```
"""

base_mod.components.append(base_mod.ComponentInfo("Save Options", __version__))
