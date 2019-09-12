import unrealsdk
import webbrowser
from enum import Enum
import sys
import os
import json

""" The path to our mods folder, determined via the directory containing the current executable (Borderlands2.exe)."""
Win32Directory = os.path.dirname(sys.executable)
ModsDirectory = os.path.join(Win32Directory, "Mods")


class ModTypes(Enum):
    """ A generic Enum type that's useful for giving plugins specific types, especially useful for sorting in the mod manager menu. """

    Utility = 1
    Content = 2
    Gameplay = 3

class BL2MOD:
    """An object that describes a mod to be represented in the BL2 Mod Manager.

    All mods should set their Name and Description fields.

    By default, mods are given a `Status` of "Disabled", and respond to the
    Enter key in the mod menu, which toggles their Status and calls the
    `Enabled` and `Disabled` methods as appropriate. Mods should define
    these methods to make use of this functionality.

    For more complex interaction in the mods menu, mods should define their
    `SettingsInputs` property and `SettingsInputPressed` method. (This will
    override the `Enabled` and `Disabled` behavior described above.) They may
    also display status text by setting their `Status` text.

    Mods may respond to their bindings being rebound by
    the user, pressed, and released, by defining the `GameInputRebound`,
    `GameInputPressed`, and `GameInputReleased` methods, respectively.
    """

    Name = ""
    """The name of the mod to display in the mod manager."""
    Description = ""
    """The description of the mod to display in the mod manager."""
    Status = "Disabled"
    """The status of the mod to display in the mod manager."""
    SettingsInputs = {"Enter": "Enable"}
    """A dictionary that describes inputs the mod responds to in the mod
    manager, in the format { '[Key]': '[Action]' }. For example:

        SettingsInputs = { 'Enter': "Do Something", "H": "Do Something Else" }
    """
    Types = []
    """A list that specifies all the mod types that the mod is. 
    For a list of mod types, see the ModTypes enum.
    """
    Author = "Unknown"
    """The author(s) of the mod which is displayed in the mod manager menu. """

    Options = []

    Keybinds = []

    def Enable(self):
        """Called by the mod manager to enable the mod.

        Only invoked if the mod does not implement custom interaction via its 
        `SettingsInputPressed` property and `SettingsInputPressed` method.
        """
        pass

    def Disable(self):
        """Called by the mod manager to disable the mod.

        Only invoked if the mod does not implement custom interaction via its 
        `SettingsInputPressed` property and `SettingsInputPressed` method.
        """
        pass

    def SettingsInputPressed(self, name: str):
        """Called by the mod manager when one of the actions the mod has
        registered for has been invoked via its associated key.

        Mods may define this method to respond to user actions like so:

            def SettingsInputPressed(self, name):
                if name == "Do Something":
                    ...
                elif name == "Do Something Else":
                    ...

        Parameters
        ----------
        name : str
        The name of the action that was associated with a key in the
        `SettingsInputs` property, that has now been pressed by the user.
        """
        if name == "Enable":
            self.Status = "Enabled"
            self.SettingsInputs = {"Enter": "Disable"}
            self.Enable()
            for option in self.Options:
                self.ModOptionChanged(option, option.CurrentValue)
        elif name == "Disable":
            self.Status = "Disabled"
            self.SettingsInputs = {"Enter": "Enable"}
            self.Disable()

    def GameInputRebound(self, name: str, key: str):
        """Called when the user rebinds the key for the registered action.

        Mods may define this method if, for example, they would like to save
        their settings to reflect the user's preference:

            def GameInputRebound(self, name, key):
                MySettings.KeyBindings[name] = key
                MySettings.Save()

        Parameters
        ----------
        name : str
            The name of the action the user has rebound.
        key : str
            The key the user bebound the action to.
        """
        pass

    def GameInputPressed(self, name: str):
        """Called when the user presses the key for a key binding the mod has
        registered for.

        Mods should define this method to perform actions when the user
        initially presses the key of their choosing:

            def GameInputPressed(self, name):
                if name == "Do Something In Game":
                    ...
                elif name == "Do Something Else In Game":
                    ...

        Parameters
        ----------
        name : str
            The name of the action the user has pressed the key for.
        """
        pass

    def GameInputReleased(self, name: str):
        """Called when the user releases the key for a key binding the mod has
        registered for.

        Mods should define this method to perform actions when the user
        releases the key of their choosing:

            def GameInputReleased(self, name):
                if name == "Do Something In Game":
                    ...
                elif name == "Do Something Else In Game":
                    ...

        Parameters
        ----------
        name : str
            The name of the action the user has pressed the key for.
        """
        pass


    def ModOptionChanged(self, Option, newValue):
        """Called when the user changes the value of our option for the given setting. 

        Mods may define this method, if for example they want to save the state of a given setting:
            
            def ModOptionChanged(self, Option, newValue):
                currentModValue = newValue
                MySettings.Save(currentModValue)

        Parameters
        ----------
        Option: Options
            A class that is used to specify a type of a given setting. 
        newValue:
            If the changed option is a boolean/spinner option, it's the value in the `Choices` array.
            If the changed option is a slider option, the value of the slider (float) that the value was changed to. """
        pass

def getModModule(mod):
    modModule = ""
    modules = [m for m in sys.modules.values() if m]
    for module in modules:
        try:
            if module.__file__.find("Win32\\Mods") != -1 and module.__file__.find("Win32\\Mods\\__init__.py") == -1:
                if mod.__class__.__name__ in module.__dir__():
                    modModule = module
                    break
        except AttributeError: continue 
    return modModule

unrealsdk.Mods = []

def RegisterMod(mod: BL2MOD):
    modModule = getModModule(mod)
    modDirectory = os.path.dirname(os.path.realpath(modModule.__file__))
    settingsPath = os.path.join(modDirectory, "settings.json")
    if os.path.isfile(settingsPath):
        with open(settingsPath) as configFile:
            settings = json.load(configFile)
            options = settings.get("Options", dict())
            for optionName, optionValue in options.items():
                for option in mod.Options:
                    if optionName in option.Caption:
                        if type(option) != unrealsdk.Options.Hidden:
                            if isinstance(optionValue, bool):
                                option.CurrentValue = optionValue
                            elif isinstance(optionValue, str):
                                option.CurrentValue = option.Choices[option.Choices.index(optionValue)]
                            elif isinstance(optionValue, int) or isinstance(optionValue, float):
                                option.CurrentValue = float(optionValue)
                        else:
                            option.CurrentValue = optionValue
            keybinds = settings.get("Keybinds", dict())
            for keybindName, keybind in keybinds.items():
                for GameInput in mod.Keybinds:
                    if keybindName == GameInput[0]:
                        GameInput[1] = str(keybind)
    unrealsdk.Mods.append(mod)


unrealsdk.BL2MOD = BL2MOD
unrealsdk.ModTypes = ModTypes
unrealsdk.ModMenuOpened = []
unrealsdk.RegisterMod = RegisterMod