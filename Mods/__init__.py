import traceback
import bl2sdk

""" Increment this version any time you update ANY core Python API """
bl2sdk.PythonManagerVersion = 1


from .ModManager import *
from .OptionManager import *
from .KeybindManager import *
from .ModMenuManager import *
from .SaveManager import *

from .General import *

import os, importlib


for module in os.listdir(os.path.dirname(__file__)):
    absolute_file = f"{os.path.dirname(__file__)}\\{module}"
    if not os.path.isdir(absolute_file) or module == 'General':
        continue
    try:
        importlib.import_module(f".{module}", "Mods")
    except Exception as ex:
        bl2sdk.Log(f"Failed to import mod: {module}")
        tb = traceback.format_exc()
        tb = tb.split('\n')
        bl2sdk.Log("    " + tb[len(tb) - 3].strip())
        bl2sdk.Log("    " + tb[len(tb) - 2].strip())