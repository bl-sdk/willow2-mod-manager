import bl2sdk
from bl2sdk import *
import os
import json
import sys
import mypy
import webbrowser
from enum import Enum

def log(s):
    s = str(s)
    if not s.endswith("\n"):
        s += "\n"
    bl2sdk.Log(s)

print = log

""" The path to our mods folder, determined via the directory containing the current executable (Borderlands2.exe)."""
Win32Directory = os.path.dirname(sys.executable)
ModsDirectory = os.path.join(Win32Directory, "Mods")


class ModTypes(Enum):
    """ A generic Enum type that's useful for giving plugins specific types, especially useful for sorting in the mod manager menu. """

    Utility = 1
    Content = 2
    Gameplay = 3

class Options:
    """ A generic helper class that stores all of the option types available in the `PLUGINS` menu. """

    # Helpful boolean to tell the `SETTINGS` menu that the currently selected menu is the plugin menu.
    # We want to know this just so we can possibly remove all items in the `PLUGIN` menu, but not the `GAMEPLAY` menu.
    isMenuPluginMenu = False
    # We want this boolean to properly sort the PLUGINS menu. The menu should go after the `GAMEPAD` menu if its enabled.
    isGamepadConnected = False

    class Slider:
        """ This class is a holder for all slider option types, useful for specifying integer/float values. """

        EventID = 0
        OptionType = 3

        def __init__(
            self,
            Caption: str,
            Description: str,
            StartingValue: float,
            MinValue: float,
            MaxValue: float,
            Increment: float,
        ):
            self.Caption = Caption
            self.StartingValue = StartingValue
            self.MinValue = MinValue
            self.MaxValue = MaxValue
            self.Increment = Increment
            self.Description = Description
            self.CurrentValue = StartingValue

    class Spinner:
        """ This option is especially useful when you want the user to choose between two or more, specified options. """

        EventID = 0
        OptionType = 0

        def __init__(
            self,
            Caption: str,
            Description: str,
            StartingChoice: str,
            Choices: list,
        ):
            self.Caption = Caption
            self.StartingChoice = StartingChoice
            self.CurrentValue = StartingChoice
            self.Choices = Choices
            self.Description = Description

    class Boolean:
        """ This class is pretty much just a SpinnerOption, but is cleaner and more useful if you want a toggleable feature in your plugin. """

        EventID = 0
        OptionType = 0

        def __init__(self, Caption: str, Description: str, StartingValue: bool):
            self.Caption = Caption
            self.StartingChoiceIndex = int(StartingValue)
            self.CurrentValue = int(StartingValue)
            self.Description = Description
            self.Choices = ["Off", "On"]
    
    class Hidden:
        """ This class is a type of option that is never shown to the user but is specified in the settings.json file. 
        You can use this to store things the user has no need to see but is still important to have persistent. """
        OptionType = -1

        def __init__(self, valueName: str, StartingValue):
            self.Caption = valueName
            self._currentValue = StartingValue

        @property
        def CurrentValue(self):
            return self._currentValue

        @CurrentValue.setter
        def CurrentValue(self, value):
            self._currentValue = value
            storeModSettings()


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

    Mods may also register for in-game key bindings by invoking their own
    `RegisterGameInput` method (and also unregister them via
    `UnregisterGameInput`). They may respond to their bindings being rebound by
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
        elif name == "Disable":
            self.Status = "Disabled"
            self.SettingsInputs = {"Enter": "Enable"}
            self.Disable()

    def RegisterGameInput(self, name: str, key: str = None):
        """Adds a key binding option to the Keyboard Settings menu, allowing the
        mod to respond to a key chosen by the user.

        Mods call this method specifying the name of the binding (shown to the
        user as well as used within the mod):

            self.RegisterGameInput("Do Something In Game")

        Optionally, a mod may specify a default key:

            self.RegisterGameInput("Do Something Else In Game", key="J")

        Parameters
        ----------
        name : str
            The name of the action called by the key the user defines. This is
            displayed in the Keyboard Settings menu, and also passed to this
            mod's `GameInputRebound`, `GameInputPressed`, and
            `GameInputReleased` methods.

        key: str, optional
            The key to attempt to bind the action to. This is ignored if the
            user has another action bound to the same key. For a list of key
            names, see: wiki.unrealengine.com/List_of_Key/Gamepad_Input_Names

        """
        for tag, binding in GameInputBinding.ByTag.items():
            if binding.Mod is self and binding.Name == name:
                return
        GameInputBinding(self, name, key)

    def UnregisterGameInput(self, name: str):
        """Removes a key binding option from the Keyboard Settings menu.

        Parameters
        ----------
        name : str
            The name of the action as provided to `RegisterGameInput` when the
            binding was registered for.
        """
        unregisteredTag = None
        for tag, binding in GameInputBinding.ByTag.items():
            if binding.Mod is self and binding.Name == name:
                unregisteredTag = tag
                if binding.Key in GameInputBinding.ByKey:
                    del GameInputBinding.ByKey[binding.Key]
                break
        del GameInputBinding.ByTag[unregisteredTag]

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
            The name of the action the user has rebound. This is the name that
            was provided to `RegisterGameInput` when the binding was registered.
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
            The name of the action the user has pressed the key for. This is the
            name that was provided to `RegisterGameInput` when the binding was
            registered.
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
            The name of the action the user has pressed the key for. This is the
            name that was provided to `RegisterGameInput` when the binding was
            registered.
        """
        pass

    def RegisterGameConfigOption(self, Option: Options):
        """Adds a given option to the `PLUGINS` menu, allowing the mod to change specific properties in the menu. """
        for modOption, mod in ModOptionsBinding.OptionList.items():
            if mod is self and modOption.Caption == Option.Caption:
                return
        ModOptionsBinding(self, Option)

    def UnregisterGameConfigOption(self, Option: Options):
        """Removes a given option from the `PLUGINS` menu. """
        for option, mod in ModOptionsBinding.OptionList.items():
            if mod is self and option.Caption is Option.Caption:
                del ModOptionsBinding.OptionList[Option]
                return

    def ModOptionChanged(self, Option: Options, newValue):
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

class GameInputBinding:
    """An object that describes a key binding registered by a mod.

    Each binding object is assigned a unique "tag" string upon creation; this is
    used to refer to the binding from game objects that accept strings.
    """

    TagIndex = 0
    """An integer incremented upon binding creation, in order to generate a
    unique tag for each one."""
    ByTag = dict()
    """A dictionary for looking up bindings by their tag."""
    ByKey = dict()
    """A dictionary for looking up bindings by their currently assigned key."""
    ByMod = dict()
    """A dictionary that looks up the mod names by their tags. """

    def __init__(self, mod: BL2MOD, name: str, key: str):
        self.Mod = mod
        self.Name = name

        # Generate our tag using the current tag index, associate ourselves with
        # it in the dictionary, and increment the tag index for the next one.
        tag = "bl2sdk%s" % GameInputBinding.TagIndex
        GameInputBinding.ByTag[tag] = self
        GameInputBinding.ByMod[tag] = self.Mod.Name
        GameInputBinding.TagIndex += 1
        # Onto restoring our configs from the settings if they exist.

        # A variable for our current module for the mod.
        modModule = getModModule(mod)

        try: 
            modDirectory = os.path.dirname(os.path.realpath(modModule.__file__))
            settingsPath = os.path.join(modDirectory, "settings.json")
            with open(settingsPath) as configFile:
                settings = json.load(configFile)
                keybinds = settings.get("Keybinds", dict())
                for keybindName, keybind in keybinds.items():
                    if keybindName == name:
                        key = str(keybind)
        except: pass

        # If no default key was requested, default to "None"
        if key == None:
             self.Key = "None"
        # If a requested key is already in use by another binding, default it
        # to "None" and notify the mod of the rebinding.
        elif key in GameInputBinding.ByKey:
            self.Key = "None"
            mod.GameInputRebound(name, "None")
        # Otherwise, associate this binding with the key.
        else:
            self.Key = key
            GameInputBinding.ByKey[key] = self

class ModOptionsBinding:
    """An object that describes a option registered by a mod.

    Each option object gets given a mod that the option is linked. This gets used to order all of our config options.
    All of the menu options are bound to a specific mod as well. This is used to use sub-menus for our options menu.
    """

    OptionList = dict()

    def __init__(self, mod: BL2MOD, option: Options):
        self.Options = option

        modModule = getModModule(mod)
        try: 
            modDirectory = os.path.dirname(os.path.realpath(modModule.__file__))
            settingsPath = os.path.join(modDirectory, "settings.json")
            with open(settingsPath) as configFile:
                settings = json.load(configFile)
                options = settings.get("Options", dict())
                for optionName, optionValue in options.items():
                    if optionName == option.Caption and type(option) != Options.Hidden:
                        if isinstance(optionValue, bool):
                            option.CurrentValue = optionValue
                        elif isinstance(optionValue, str):
                            option.CurrentValue = option.Choices[option.Choices.index(optionValue)]
                        elif isinstance(optionValue, int) or isinstance(optionValue, float):
                            option.CurrentValue = float(optionValue)
                    elif optionName == option.Caption and type(option) == Options.Hidden:
                        option.CurrentValue = optionValue
        except: pass

        ModOptionsBinding.OptionList[self.Options] = mod

class ModOptions(BL2MOD):

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
            pass
        elif name == "Help":
            webbrowser.open("https://github.com/bl-sdk/BL2-Python-Plugins/wiki")


bl2sdk.BL2MOD = BL2MOD
bl2sdk.ModTypes = ModTypes
bl2sdk.Options = Options
bl2sdk.Mods = [ModOptions()]
bl2sdk.ModMenuOpened = []


""" A generic helper function that removes a hook (if it exists) and then re-registers it. """

def RunHook(functionName, name, function):
    RemoveHook(functionName, name)
    RegisterHook(functionName, name, function)


""" Here we populate our mod manager with all of our mods that we've got loaded. """

def LoadModList(caller: UObject, function: UFunction, params: FStruct) -> bool:
    caller.ClearFilters()
    caller.SetFilterFromString("compatibility", "Utility Mods", "isCompatibility:1")
    caller.SetFilterFromString("seasonpass", "Gameplay Mods", "isSeasonPass:1")
    caller.SetFilterFromString("addon", "Content Mods", "isAddon:1")
    caller.SetFilterFromStringAndSortNew("all", "All Mods", "")

    caller.SetStoreHeader("Mods", 0, "By Abahbob", "Mod Manager")

    translationContext = GetEngine().GamePlayers[0].GetTranslationContext()
    for idx, mod in enumerate(bl2sdk.Mods):
        obj, _ = caller.CreateMarketplaceItem(())
        obj.SetString(caller.Prop_offeringId, str(idx), translationContext)
        obj.SetString(caller.Prop_contentTitleText, mod.Name, translationContext)
        fullDescription = mod.Description + "\n\nCreated by: " + mod.Author
        obj.SetString(caller.Prop_descriptionText, fullDescription, translationContext)
        if mod.Status == "Enabled" or mod.Status == "":
            obj.SetString(
                caller.Prop_statusText, '<font color="#00FF00">Enabled</font>'
            )
            obj.SetString(
                caller.Prop_messageText, '<font color="#00FF00">Enabled</font>'
            )
        else:
            obj.SetString(
                caller.Prop_statusText, '<font color="#FF0000">Disabled</font>'
            )
            obj.SetString(
                caller.Prop_messageText, '<font color="#FF0000">Disabled</font>'
            )
        try:
            obj.SetFloat(caller.Prop_isSeasonPass, int(ModTypes.Gameplay in mod.Types))
            obj.SetFloat(caller.Prop_isAddOn, int(ModTypes.Content in mod.Types))
            obj.SetFloat(
                caller.Prop_isCompatibility, int(ModTypes.Utility in mod.Types)
            )
        except AttributeError:
            pass
        caller.AddContentData(obj)
    caller.PostContentLoaded(True)
    return False


RunHook("WillowGame.MarketplaceGFxMovie.OnDownloadableContentListRead", "InjectMods", LoadModList)

""" This function controls mod specific keybinds in the mod manager. """

def HookShopInputKey(caller: UObject, function: UFunction, params: FStruct) -> bool:
    key = params.ukey
    event = params.uevent

    if key in ["Escape", "Up", "Down"]:
        return True

    selectedObject = caller.GetSelectedObject()
    try:
        modIndex = int(selectedObject.GetString(caller.Prop_offeringId))
    except:
        return False

    mod = bl2sdk.Mods[modIndex]

    if key in mod.SettingsInputs:
        if event == 0:
            inputName = mod.SettingsInputs[key]
            mod.SettingsInputPressed(inputName)
            obj = caller.GetSelectedObject()
            translationContext = GetEngine().GamePlayers[0].GetTranslationContext()
            obj.SetString(caller.Prop_contentTitleText, mod.Name, translationContext)

            fullDescription = mod.Description + "\n\nCreated by: " + mod.Author
            if mod.Status == "Enabled" or mod.Status == "":
                obj.SetString(
                    caller.Prop_statusText, '<font color="#00FF00">Enabled</font>'
                )
                obj.SetString(
                    caller.Prop_messageText, '<font color="#00FF00">Enabled</font>'
                )
            else:
                obj.SetString(
                    caller.Prop_statusText, '<font color="#FF0000">Disabled</font>'
                )
                obj.SetString(
                    caller.Prop_messageText, '<font color="#FF0000">Disabled</font>'
                )
            try:
                obj.SetFloat(
                    caller.Prop_isSeasonPass, int(ModTypes.Gameplay in mod.Types)
                )
                obj.SetFloat(caller.Prop_isAddOn, int(ModTypes.Content in mod.Types))
                obj.SetFloat(
                    caller.Prop_isCompatibility, int(ModTypes.Utility in mod.Types)
                )
            except AttributeError:
                pass
            caller.RefreshDLC()

    elif key != "Enter":
        return True

    return False


RunHook("WillowGame.MarketplaceGFxMovie.ShopInputKey", "HookShopInputKey", HookShopInputKey)

""" Now we replace the DLC menu with the mods. """

def ReplaceDLCWithMods(caller: UObject, function: UFunction, params: FStruct) -> bool:
    Caption = params.Caption
    bNew = params.bNew
    if Caption == "$WillowMenu.WillowScrollingListDataProviderFrontEnd.DLC":
        Caption = "MODS"
        bNew = False
    DoInjectedCallNext()
    caller.AddListItem(params.EventID, Caption, params.bDisabled, bNew)
    return False


""" An efficient function that notifies us when we're in the main menu to populate the DLC menu. """

def HookMainMenuPopulateForMods(caller: UObject, function: UFunction, params: FStruct) -> bool:
    for modFunc in bl2sdk.ModMenuOpened:
        try:
            modFunc()
        except:
            pass
    RegisterHook(
        "WillowGame.WillowScrollingList.AddListItem",
        "ReplaceDLCWithMods",
        ReplaceDLCWithMods,
    )
    DoInjectedCallNext()
    caller.Populate(params.TheList)
    RemoveHook("WillowGame.WillowScrollingList.AddListItem", "ReplaceDLCWithMods")
    return False


RunHook("WillowGame.WillowScrollingListDataProviderFrontEnd.Populate","HookMainMenuPopulateForMods",HookMainMenuPopulateForMods)

seperatorNames = [""]

""" Hook whenever we change the currently selected mod in the mod manager.  """

def HookModSelected(caller: UObject, function: UFunction, params: FStruct) -> bool:
    selectedObject = caller.GetSelectedObject()
    try:
        modIndex = int(selectedObject.GetString(caller.Prop_offeringId))
    except TypeError:
        return

    mod = bl2sdk.Mods[modIndex]

    inputs = mod.SettingsInputs.copy()
    inputs["Escape"] = "Cancel"
    inputs["Q"] = "Filter"
    leftColumn = True
    leftColumnEntries = []
    rightColumnEntries = []

    for key, action in inputs.items():
        entries = leftColumnEntries if leftColumn else rightColumnEntries
        entries.append("[%s] %s" % (key, action))
        leftColumn = not leftColumn

    leftColumnText = "\n".join(leftColumnEntries)
    rightColumnText = "\n".join(rightColumnEntries)
    caller.SetTooltips(leftColumnText, rightColumnText)
    return False


RunHook("WillowGame.MarketplaceGFxMovie.extOnOfferingChanged","HookModSelected", HookModSelected)

""" This function adds all of our keybinds to the keybind menu. """

def HookInitKeyBinding(caller: UObject, function: UFunction, params: FStruct) -> bool:
    seperatorNames.clear()
    lastModName = ""
    for tag, binding in GameInputBinding.ByTag.items():
        modName = GameInputBinding.ByMod[tag]
        if lastModName != modName:
            lastModName = modName
            nameOfSeperator = modName
            seperatorNames.append(nameOfSeperator)
            caller.AddKeyBindEntry(nameOfSeperator, nameOfSeperator, nameOfSeperator)
        DoInjectedCallNext()
        caller.AddKeyBindEntry(tag, tag, str("        " + binding.Name))
    return True

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.InitKeyBinding","HookInitKeyBinding",HookInitKeyBinding)

""" A function that gets localized versions of keys as not all keys are supported. """

def GetFixedLocalizedKeyName(menu, key):
    if key == "None":
        return ""
    if key == "Quote":
        return "'"
    try:
        name = menu.GetLocalizedKeyName(key)
        return "" if name is None else name
    except:
        return ""

""" A function that hooks into the creation of config options. """

def HookOnPopulateKeys(caller: UObject, function: UFunction, params: FStruct) -> bool:
    DoInjectedCallNext()
    caller.extOnPopulateKeys()

    translationContext = GetEngine().GamePlayers[0].GetTranslationContext()

    for keyBind in caller.KeyBinds:
        if keyBind.Tag in seperatorNames:
            keyBind.Object.SetString("value", "")
            keyBind.Object.SetVisible(False)
        if keyBind.Tag in GameInputBinding.ByTag:
            binding = GameInputBinding.ByTag[keyBind.Tag]
            keyBind.CurrentKey = binding.Key
        elif keyBind.CurrentKey in GameInputBinding.ByKey:
            binding = GameInputBinding.ByKey[keyBind.CurrentKey]
            binding.Key = "None"
            del GameInputBinding.ByKey[keyBind.CurrentKey]
            binding.Mod.GameInputRebound(binding.Name, "None")
        keyBind.Object.SetString(
            "value",
            GetFixedLocalizedKeyName(caller, keyBind.CurrentKey),
            translationContext,
        )

    return False

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.extOnPopulateKeys","HookOnPopulateKeys",HookOnPopulateKeys,)

""" A function that changes a mod's keybinds in the configuration menu. """

def HookBindCurrentSelection(caller: UObject, function: UFunction, params: FStruct) -> bool:
    selectedKeyBind = caller.KeyBinds[caller.CurrentKeyBindSelection]
    if selectedKeyBind.Tag in seperatorNames:
        return False
    selectedBinding = None

    oldKey = selectedKeyBind.CurrentKey
    newKey = params.Key

    DoInjectedCallNext()
    caller.BindCurrentSelection(newKey)

    if newKey == oldKey:
        return False

    if selectedKeyBind.Tag in GameInputBinding.ByTag:
        selectedBinding = GameInputBinding.ByTag[selectedKeyBind.Tag]
        if selectedBinding.Key in GameInputBinding.ByKey:
            del GameInputBinding.ByKey[selectedBinding.Key]

    if newKey in GameInputBinding.ByKey:
        exchangedBinding = GameInputBinding.ByKey[newKey]
        del GameInputBinding.ByKey[newKey]

        exchangedBinding.Key = oldKey
        if oldKey != "None":
            GameInputBinding.ByKey[oldKey] = exchangedBinding
        try:
            exchangedBinding.Mod.GameInputRebound(exchangedBinding.Name, oldKey)
        except:
            bl2sdk.Log("Error notifying %s of key rebind." % exchangedBinding.Mod.Name)

    if selectedBinding != None:
        selectedBinding.Key = newKey
        GameInputBinding.ByKey[newKey] = selectedBinding
        selectedBinding.Mod.GameInputRebound(selectedBinding.Name, newKey)

    translationContext = GetEngine().GamePlayers[0].GetTranslationContext()

    for keyBind in caller.KeyBinds:
        if keyBind.Tag in GameInputBinding.ByTag:
            binding = GameInputBinding.ByTag[keyBind.Tag]
            keyBind.CurrentKey = binding.Key
        keyBind.Object.SetString(
            "value",
            GetFixedLocalizedKeyName(caller, keyBind.CurrentKey),
            translationContext,
        )

    caller.ControllerMappingClip.InvalidateKeyData()
    return False

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.BindCurrentSelection", "HookBindCurrentSelection",HookBindCurrentSelection)


def HookDoBind(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if caller.KeyBinds[caller.CurrentKeyBindSelection].Caption in seperatorNames:
        return False
    return True

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.DoBind","HookDoBind",HookDoBind)

""" Hook onto player input so we know when a mod's keybinds were pressed. """

def HookInputKey(caller: UObject, function: UFunction, params: FStruct) -> bool:
    # If we do not have a binding associated with this key, we ignore it.
    if params.Key not in GameInputBinding.ByKey:
        return True
    # Retrieve the binding data from our dictionary.
    binding = GameInputBinding.ByKey[params.Key]

    # An event of 0 correlates to the key being pressed.
    if params.Event == 0:
        binding.Mod.GameInputPressed(binding)
    # An event of 0 correlates to the key being released.
    elif params.Event == 1:
        binding.Mod.GameInputReleased(binding)

    return False

RunHook("WillowGame.WillowUIInteraction.InputKey", "HookInputKey", HookInputKey)

""" This function adds the `PLUGINS` menu into the options menu. """

def AddModConfigMenu(caller: UObject, function: UFunction, params: FStruct) -> bool:
    Caption = params.Caption
    DoInjectedCallNext()
    caller.AddListItem(params.EventID, Caption, params.bDisabled, params.bNew)
    correctMenuLocation = (
        Caption
        == "$WillowMenu.WillowScrollingListDataProviderTopLevelOptions.KeyboardMouseOptions"
        and Options.isGamepadConnected == False
    ) or (
        Caption
        == "$WillowMenu.WillowScrollingListDataProviderTopLevelOptions.GamepadOptionsPC"
        and Options.isGamepadConnected == True
    )
    if correctMenuLocation and (bool(ModOptionsBinding.OptionList) == True):
        caller.AddListItem(0, "PLUGINS", False, False)
    return False

""" This function hooks onto the options menu to create the `PLUGINS` menu. """

def PopulateGameplayOptions(caller: UObject, function: UFunction, params: FStruct) -> bool:
    RegisterHook("WillowGame.WillowScrollingList.AddListItem", "AddModConfigMenu", AddModConfigMenu)
    DoInjectedCallNext()
    # We'll wanna set our gamepad boolean correctly here since we can't call it in AddListItem.
    Options.isGamepadConnected = caller.IsPCGamepadConnected()
    caller.Populate(params.TheList)
    RemoveHook("WillowGame.WillowScrollingList.AddListItem", "AddModConfigMenu")
    return False

RunHook("WillowGame.WillowScrollingListDataProviderTopLevelOptions.Populate","PopulateGameplayOptions", PopulateGameplayOptions)

""" This function is ran whenever the selection of an item in a WillowScrollingListDataProviderBase, we only care to use this for detecting if our current selection is the `PLUGINS` menu. """

def HandleSelectionChange(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if caller.MenuDisplayName == "OPTIONS":
        selectedIndex = params.TheList.GetSelectedIndex()
        Options.isMenuPluginMenu = (params.EventID == 0 and (selectedIndex == 5 or selectedIndex == 4))
    DoInjectedCallNext()
    return False

RunHook("WillowGame.WillowScrollingListDataProviderBase.HandleSelectionChange","HandleSelectionChange", HandleSelectionChange)

""" This function fills up our game options with the options we want from our given mods. """

def PopulateGameOptions(caller: UObject, function: UFunction, params: FStruct) -> bool:
    # We technically might not want to fully use this now, but it keeps everything safe for the HookValueChange() hook.
    startingIndex = 556
    # If we're in the plugin menu, we shouldn't fill in the other `GAMEPLAY` menu.
    if Options.isMenuPluginMenu == True:
        for option, mod in ModOptionsBinding.OptionList.items():
            caption = (mod.Name + ": " + option.Caption).upper()
            option.EventID = startingIndex
            if option.OptionType == -1:
                continue
            if option.OptionType == 0:
                if type(option) is Options.Spinner:
                    params.TheList.AddSpinnerListItem(
                        startingIndex, caption, False, int(option.Choices.index(option.CurrentValue)), option.Choices
                    )
                else:
                    params.TheList.AddSpinnerListItem(
                        startingIndex, caption, False, int(option.CurrentValue), option.Choices
                    )
            elif option.OptionType == 3:
                params.TheList.AddSliderListItem(
                    startingIndex,
                    caption,
                    False,
                    option.CurrentValue,
                    option.MinValue,
                    option.MaxValue,
                    option.Increment,
                )
            caller.AddDescription(startingIndex, option.Description)
            startingIndex = startingIndex + 1
        DoInjectedCallNext()
    else:
        DoInjectedCallNext()
        caller.Populate(params.TheList)
    return False

RunHook("WillowGame.WillowScrollingListDataProviderGameOptions.Populate","PopulateGameOptions", PopulateGameOptions)

""" This function here hooks onto a player changing the value of a setting. """

def HookValueChange(caller: UObject, function: UFunction, params: FStruct) -> bool:
    for option, mod in ModOptionsBinding.OptionList.items():
        if option.EventID == params.EventID:
            if params.NewSliderValue != None:
                mod.ModOptionChanged(option, float(params.NewSliderValue))
                option.CurrentValue = float(params.NewSliderValue)
                break
            elif params.NewChoiceIndex != None:
                if type(option) is Options.Boolean:
                    option.CurrentValue = bool(int(params.NewChoiceIndex))
                    mod.ModOptionChanged(option, bool(params.NewChoiceIndex))
                elif type(option) is Options.Spinner:
                    option.CurrentValue = option.Choices[params.NewChoiceIndex]
                    mod.ModOptionChanged(option, option.Choices[params.NewChoiceIndex])
                else:
                    option.CurrentValue = int(params.NewChoiceIndex)
                    mod.ModOptionChanged(option, int(params.NewChoiceIndex))
                break
    DoInjectedCallNext()
    return True

RunHook("WillowGame.WillowScrollingListDataProviderGameOptions.HandleSpinnerChange", "HookValueChange", HookValueChange)
RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.HandleSliderChange","HookValueChange", HookValueChange)

""" Here goes all of our mod / keybind settings savings. """


""" A list of the currently loaded modules. """ 
def getLoadedMods():
    modules = [m for m in sys.modules.values() if m]
    loadedMods = dict()
    for module in modules:
        try:
            # We don't want ourselves.
            if module.__file__.find("Win32\\Mods") != -1 and module.__file__.find("Win32\\Mods\\__init__.py") == -1:
                properties = module.__dir__()
                for mod in bl2sdk.Mods: 
                    if mod.Status != "Disabled" and mod.__class__.__name__ in properties:
                        loadedMods[mod] = module
                        break
        except AttributeError:
            continue
    return loadedMods

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

""" Save all of our mod settings, keybinds, etc"""
def storeModSettings():
    loadedMods = getLoadedMods()
    for mod in loadedMods:
        if (mod not in ModOptionsBinding.OptionList.values()) and (mod.Name not in GameInputBinding.ByMod.values()):
            continue
        modSettings = {}
        modSettings["Options"] = {}
        modSettings["Keybinds"] = {}
        if mod in ModOptionsBinding.OptionList.values():
            settingsList = [key for(key, value) in ModOptionsBinding.OptionList.items() if value == mod]
            for setting in settingsList:
                if type(setting) is Options.Spinner:
                    currentVal = setting.Choices[setting.Choices.index(setting.CurrentValue)]
                    modSettings["Options"].update( {setting.Caption : currentVal } )
                else:
                    modSettings["Options"].update( {setting.Caption : setting.CurrentValue } )
        if mod.Name in GameInputBinding.ByMod.values():
            for tag, binding in GameInputBinding.ByTag.items():
                if GameInputBinding.ByMod[tag] == mod.Name:                 
                    taggedValue = GameInputBinding.ByTag[tag]
                    modSettings["Keybinds"].update( {taggedValue.Name : taggedValue.Key } ) 
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