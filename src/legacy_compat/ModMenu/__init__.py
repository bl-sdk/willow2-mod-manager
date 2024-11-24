# ruff: noqa: N802, N803, D102, D103, N999

from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType

from legacy_compat import compat_handlers
from legacy_compat import unrealsdk as old_unrealsdk

from . import ModObjects, Options
from .DeprecationHelper import Deprecated, NameChangeMsg, PrintWarning
from .HookManager import AnyHook, Hook, HookFunction, HookMethod, RegisterHooks, RemoveHooks
from .KeybindManager import InputEvent, Keybind, KeybindCallback
from .ModObjects import EnabledSaveType, Game, ModPriorities, Mods, ModTypes, RegisterMod, SDKMod
from .NetworkManager import (
    ClientMethod,
    RegisterNetworkMethods,
    ServerMethod,
    UnregisterNetworkMethods,
)
from .SettingsManager import (
    GetSettingsFilePath,
    LoadModSettings,
    SaveAllModSettings,
    SaveModSettings,
)

__all__: tuple[str, ...] = (
    "AnyHook",
    "ClientMethod",
    "Deprecated",
    "EnabledSaveType",
    "Game",
    "GetSettingsFilePath",
    "Hook",
    "HookFunction",
    "HookMethod",
    "InputEvent",
    "Keybind",
    "KeybindCallback",
    "LoadModSettings",
    "ModPriorities",
    "ModTypes",
    "Mods",
    "NameChangeMsg",
    "Options",
    "PrintWarning",
    "RegisterHooks",
    "RegisterMod",
    "RegisterNetworkMethods",
    "RemoveHooks",
    "SDKMod",
    "SaveAllModSettings",
    "SaveModSettings",
    "ServerMethod",
    "UnregisterNetworkMethods",
)

VERSION_MAJOR = 3
VERSION_MINOR = 0

ModObjects.BL2MOD = ModObjects.SDKMod  # type: ignore
old_unrealsdk.BL2MOD = ModObjects.SDKMod  # type: ignore

old_unrealsdk.Mods = ModObjects.Mods  # type: ignore
old_unrealsdk.ModTypes = ModObjects.ModTypes  # type: ignore
old_unrealsdk.RegisterMod = ModObjects.RegisterMod  # type: ignore

old_unrealsdk.__all__ += (
    "BL2MOD",
    "Mods",
    "ModTypes",
    "RegisterMod",
)

OptionManager = ModuleType("OptionManager")
OptionManager.Options = Options  # type: ignore

# When removing this, also make sure to edit `Spinner.__init__()`
_msg = NameChangeMsg("Spinner.StartingChoice", "Spinner.StartingValue")
Options.Spinner.StartingChoice = property(  # type: ignore
    Deprecated(_msg, lambda self: self.StartingValue),  # type: ignore
    Deprecated(_msg, lambda self, val: self.__setattr__("StartingValue", val)),  # type: ignore
)


@contextmanager
def _game_get_current_compat_handler() -> Iterator[None]:
    Game.GetCurrent = Game.get_current  # type: ignore
    try:
        yield
    finally:
        del Game.GetCurrent  # type: ignore


compat_handlers.append(_game_get_current_compat_handler)
