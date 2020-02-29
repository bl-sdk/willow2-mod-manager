import traceback
import unrealsdk

# Hack for backwards compatibility
import sys
sys.modules['bl2sdk'] = unrealsdk

""" Increment this version any time you update ANY core Python API """
unrealsdk.PythonManagerVersion = 1


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
        unrealsdk.Log(f"Failed to import mod: {module}")
        tb = traceback.format_exc()
        tb = tb.split('\n')
        unrealsdk.Log("    " + tb[len(tb) - 3].strip())
        unrealsdk.Log("    " + tb[len(tb) - 2].strip())