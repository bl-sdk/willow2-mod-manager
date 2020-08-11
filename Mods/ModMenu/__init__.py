import unrealsdk
import sys


# Need to define these up here so that they're accessable when importing the other files
VERSION_MAJOR = 2
VERSION_MINOR = 1

unrealsdk.Log(f"[ModMenu] Version: {VERSION_MAJOR}.{VERSION_MINOR}")

# Exports
from . import Options as Options  # noqa: F401, E402
from .DeprecationHelper import Deprecated as Deprecated  # noqa: F401, E402
from .DeprecationHelper import NameChangeMsg as NameChangeMsg  # noqa: F401, E402
from .DeprecationHelper import PrintWarning as PrintWarning  # noqa: F401, E402
from .KeybindManager import InputEvent as InputEvent  # noqa: F401, E402
from .KeybindManager import Keybind as Keybind  # noqa: F401, E402
from .MenuManager import GetOrderedModList as GetOrderedModList  # noqa: F401, E402
from .ModObjects import EnabledSaveType as EnabledSaveType  # noqa: F401, E402
from .ModObjects import Game as Game  # noqa: F401, E402
from .ModObjects import ModPriorities as ModPriorities  # noqa: F401, E402
from .ModObjects import Mods as Mods  # noqa: F401, E402
from .ModObjects import ModTypes as ModTypes  # noqa: F401, E402
from .ModObjects import RegisterMod as RegisterMod  # noqa: F401, E402
from .ModObjects import SDKMod as SDKMod  # noqa: F401, E402
from .SettingsManager import GetSettingsFilePath as GetSettingsFilePath  # noqa: F401, E402
from .SettingsManager import LoadModSettings as LoadModSettings  # noqa: F401, E402
from .SettingsManager import SaveAllModSettings as SaveAllModSettings  # noqa: F401, E402
from .SettingsManager import SaveModSettings as SaveModSettings  # noqa: F401, E402

# Extra imports
from . import DeprecationHelper as dh  # noqa: E402
from . import ModObjects  # noqa: E402
from . import OptionManager  # noqa: E402
from . import SettingsManager  # noqa: E402


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
