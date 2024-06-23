# ruff: noqa: N802, N803, D102, D103, N999

from types import ModuleType

import unrealsdk as new_unrealsdk  # noqa: F401  # pyright: ignore[reportUnusedImport]

from legacy_compat import unrealsdk as old_unrealsdk

from . import ModObjects, Options
from .DeprecationHelper import Deprecated, NameChangeMsg, PrintWarning
from .HookManager import AnyHook, Hook, HookFunction, HookMethod, RegisterHooks, RemoveHooks
from .KeybindManager import Keybind, KeybindCallback
from .ModObjects import EnabledSaveType, Game, ModPriorities, Mods, ModTypes, RegisterMod, SDKMod

__all__: tuple[str, ...] = (
    "AnyHook",
    # "ClientMethod",
    "Deprecated",
    "EnabledSaveType",
    "Game",
    # "GetOrderedModList",
    # "GetSettingsFilePath",
    "Hook",
    "HookFunction",
    "HookMethod",
    # "InputEvent",
    "Keybind",
    "KeybindCallback",
    # "LoadModSettings",
    "ModPriorities",
    "Mods",
    "ModTypes",
    "NameChangeMsg",
    "Options",
    "PrintWarning",
    "RegisterHooks",
    "RegisterMod",
    # "RegisterNetworkMethods",
    "RemoveHooks",
    # "SaveAllModSettings",
    # "SaveModSettings",
    "SDKMod",
    # "ServerMethod",
    # "UnregisterNetworkMethods",
)

VERSION_MAJOR = 3
VERSION_MINOR = 0

ModObjects.BL2MOD = ModObjects.SDKMod  # type: ignore
old_unrealsdk.BL2MOD = ModObjects.SDKMod  # type: ignore

old_unrealsdk.Mods = ModObjects.Mods  # type: ignore
old_unrealsdk.ModTypes = ModObjects.ModTypes  # type: ignore
old_unrealsdk.RegisterMod = ModObjects.RegisterMod  # type: ignore

OptionManager = ModuleType("OptionManager")
OptionManager.Options = Options  # type: ignore

# When removing this, also make sure to edit `Spinner.__init__()`
_msg = NameChangeMsg("Spinner.StartingChoice", "Spinner.StartingValue")
Options.Spinner.StartingChoice = property(  # type: ignore
    Deprecated(_msg, lambda self: self.StartingValue),  # type: ignore
    Deprecated(_msg, lambda self, val: self.__setattr__("StartingValue", val)),  # type: ignore
)
