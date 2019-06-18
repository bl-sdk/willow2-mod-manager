import os
import json
from bl2sdk import *
import bl2sdk
from .Util import getLoadedMods

from .OptionManager import *

""" Save all of our mod settings, keybinds, etc"""
def storeModSettings():
    loadedMods = getLoadedMods()
    for mod in loadedMods:
        if not (mod.Options or mod.Keybinds):
            continue
        modSettings = {}
        modSettings["Options"] = {}
        modSettings["Keybinds"] = {}
        for setting in mod.Options:
            if type(setting) is bl2sdk.Options.Spinner:
                currentVal = setting.Choices[setting.Choices.index(setting.CurrentValue)]
                modSettings["Options"].update( {setting.Caption : currentVal } )
            else:
                modSettings["Options"].update( {setting.Caption : setting.CurrentValue } )
        for keybind in mod.Keybinds:
            modSettings["Keybinds"].update( {keybind[0] : keybind[1] } ) 
        modDirectory = os.path.dirname(os.path.realpath(loadedMods[mod].__file__))
        settingsPath = os.path.join(modDirectory, "settings.json")
        
        with open(settingsPath, "w") as configFile:
            json.dump(modSettings, configFile, indent=4)

""" This function is called whenever the user leaves the KB&M / Gameplay (Plugins) menu"""
def HookOnPop(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if caller.MenuDisplayName == "GAMEPLAY" or caller.MenuDisplayName == "PLUGINS" or caller.MenuDisplayName == "KEYBOARD & MOUSE":
        storeModSettings()
    return True

RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.OnPop", "HookOnPop", HookOnPop)