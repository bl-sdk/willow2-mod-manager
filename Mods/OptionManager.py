import unrealsdk
from unrealsdk import *
import json

from .Util import getLoadedMods
from .SaveManager import storeModSettings

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
        EventID = -700000
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


unrealsdk.Options = Options

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
    if correctMenuLocation:
        for mod in getLoadedMods():
            if mod.Options:            
                caller.AddListItem(0, "PLUGINS", False, False)
                break
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
        for mod in getLoadedMods():
            for option in mod.Options:
                if option.OptionType == -1:
                    continue
                caption = (mod.Name + ": " + option.Caption).upper()
                option.EventID = startingIndex
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
    for mod in getLoadedMods():
        for option in mod.Options:
            if option.EventID == params.EventID:
                if params.NewSliderValue != None:
                    option.CurrentValue = float(params.NewSliderValue)
                    mod.ModOptionChanged(option, float(params.NewSliderValue))
                    return True
                elif params.NewChoiceIndex != None:
                    if type(option) is Options.Boolean:
                        option.CurrentValue = bool(int(params.NewChoiceIndex))
                        mod.ModOptionChanged(option, bool(params.NewChoiceIndex))
                    elif type(option) is Options.Spinner:
                        option.CurrentValue = option.Choices[params.NewChoiceIndex]
                        mod.ModOptionChanged(option, option.Choices[params.NewChoiceIndex])
                    elif type(option) is Options.Hidden:
                        continue
                    else:
                        option.CurrentValue = int(params.NewChoiceIndex)
                        mod.ModOptionChanged(option, int(params.NewChoiceIndex))
                    return True
    return True

RunHook("WillowGame.WillowScrollingListDataProviderGameOptions.HandleSpinnerChange", "HookValueChange", HookValueChange)
RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.HandleSliderChange","HookValueChange", HookValueChange)
