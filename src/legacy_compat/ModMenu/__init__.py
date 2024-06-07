import unrealsdk
import sys
from typing import Tuple

__all__: Tuple[str, ...] = (
    "AnyHook",
    "ClientMethod",
    "Deprecated",
    "EnabledSaveType",
    "Game",
    "GetOrderedModList",
    "GetSettingsFilePath",
    "Hook",
    "HookFunction",
    "HookMethod",
    "InputEvent",
    "Keybind",
    "KeybindCallback",
    "LoadModSettings",
    "ModPriorities",
    "Mods",
    "ModTypes",
    "NameChangeMsg",
    "Options",
    "PrintWarning",
    "RegisterHooks",
    "RegisterMod",
    "RegisterNetworkMethods",
    "RemoveHooks",
    "SaveAllModSettings",
    "SaveModSettings",
    "SDKMod",
    "ServerMethod",
    "UnregisterNetworkMethods",
)


# Need to define these up here so that they're accessable when importing the other files
VERSION_MAJOR = 2
VERSION_MINOR = 5

unrealsdk.Log(f"[ModMenu] Version: {VERSION_MAJOR}.{VERSION_MINOR}")

from . import DeprecationHelper as dh  # noqa: E402
from . import OptionManager, Options, SettingsManager  # noqa: E402
from .DeprecationHelper import Deprecated, NameChangeMsg, PrintWarning  # noqa: E402
from .HookManager import (AnyHook, Hook, HookFunction, HookMethod, RegisterHooks,  # noqa: E402
                          RemoveHooks)
from .KeybindManager import InputEvent, Keybind, KeybindCallback  # noqa: E402
from .MenuManager import GetOrderedModList  # noqa: E402
from .ModObjects import (EnabledSaveType, Game, ModPriorities, Mods, ModTypes,  # noqa: E402
                         RegisterMod, SDKMod)
from .NetworkManager import (ClientMethod, RegisterNetworkMethods, ServerMethod,  # noqa: E402
                             UnregisterNetworkMethods)
from .SettingsManager import (GetSettingsFilePath, LoadModSettings,  # noqa: E402
                              SaveAllModSettings, SaveModSettings)

from . import ModObjects  # noqa: E402  # isort: skip  # Avoid circular import

"""
From this point on this file defines just aliases, most of which should be considered deprecated.


When enabling a mod, the default `SettingsInputPressed` calls `ModOptionChanged` on every option.
This behaviour should be considered deprecated, move it into your `Enable` if you need it.
Unfortuantly there's no easy way to detect mods that rely on this to print a warning, and it's not
 something that can be aliased, so this text warning will have to do.
"""


sys.modules["bl2sdk"] = unrealsdk
sys.modules["Mods.ModManager"] = ModObjects
sys.modules["Mods.OptionManager"] = OptionManager
sys.modules["Mods.SaveManager"] = SettingsManager

unrealsdk.PythonManagerVersion = VERSION_MAJOR

ModObjects.BL2MOD = ModObjects.SDKMod  # type: ignore
unrealsdk.BL2MOD = ModObjects.SDKMod

unrealsdk.Mods = ModObjects.Mods
unrealsdk.ModTypes = ModObjects.ModTypes
unrealsdk.RegisterMod = ModObjects.RegisterMod


OptionManager.Options = Options
unrealsdk.Options = Options

# When removing this, also make sure to edit `Spinner.__init__()`
_msg = dh.NameChangeMsg("Spinner.StartingChoice", "Spinner.StartingValue")
Options.Spinner.StartingChoice = property(  # type: ignore
    dh.Deprecated(_msg, lambda self: self.StartingValue),
    dh.Deprecated(_msg, lambda self, val: self.__setattr__("StartingValue", val))
)
_msg = dh.NameChangeMsg("Boolean.StartingChoiceIndex", "Boolean.StartingValue")
Options.Boolean.StartingChoiceIndex = property(  # type: ignore
    dh.Deprecated(_msg, lambda self: self.StartingValue),
    dh.Deprecated(_msg, lambda self, val: self.__setattr__("StartingValue", val))
)
del _msg


SettingsManager.storeModSettings = SettingsManager.SaveAllModSettings  # type: ignore
storeModSettings = SettingsManager.SaveAllModSettings  # noqa: N816
