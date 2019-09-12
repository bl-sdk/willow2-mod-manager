import sys
import unrealsdk
from unrealsdk import *

""" A list of the currently loaded modules. """ 
def getLoadedMods():
    modules = [m for m in sys.modules.values() if m]
    loadedMods = dict()
    for module in modules:
        try:
            # We don't want ourselves.
            if module.__file__.find("Win32\\Mods") != -1 and module.__file__.find("Win32\\Mods\\__init__.py") == -1:
                properties = module.__dir__()
                for mod in unrealsdk.Mods: 
                    if mod.Status != "Disabled" and mod.__class__.__name__ in properties:
                        loadedMods[mod] = module
                        break
        except AttributeError:
            continue
    return loadedMods
