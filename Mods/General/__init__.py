from ..ModManager import BL2MOD, RegisterMod
from importlib import reload
from sys import modules

import unrealsdk

class DefaultMod(BL2MOD):

    Name = "General"
    Status = ""
    Description = "Welcome to the Borderlands 2 Mod Manager\n\nSee below for options."
    SettingsInputs = {"O": "Open Mods Folder", "R": "Reload Mods", "H": "Help"}
    Types = []
    Author = "Abahbob"

    def SettingsInputPressed(self, name):
        if name == "Open Mods Folder":
            os.startfile(ModsDirectory)
        elif name == "Reload Mods":
            for mod in list(modules.keys()):
                if mod.startswith('Mods.'):
                    del modules[mod]
            unrealsdk.Mods = []
            modules["Mods"] = reload(modules["Mods"])
        elif name == "Help":
            webbrowser.open("https://github.com/bl-sdk/BL2-Python-Plugins/wiki")


RegisterMod(DefaultMod())