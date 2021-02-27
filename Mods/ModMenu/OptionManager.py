from __future__ import annotations

import unrealsdk
from typing import Any, List, Sequence, Tuple

from . import MenuManager, ModObjects, Options, SettingsManager

__all__: Tuple[str, ...] = ()


_modded_data_provider_stack: List[unrealsdk.UObject] = []
_nested_options_stack: List[Options.Nested] = []

_MOD_OPTIONS_EVENT_ID: int = 1417
_MOD_OPTIONS_MENU_NAME: str = "MODS"

_INDENT: int = 2


class _ModHeader(Options.Field):
    def __init__(self, Caption: str) -> None:
        self.Caption = Caption
        self.Description = ""
        self.IsHidden = False


def _create_data_provider(name: str) -> unrealsdk.UObject:
    """
    Helper function that creates a new data provider and adds it to the stack.

    Args:
        name: The menu name to give the new data provider.
    Returns:
        The data provider.
    """
    provider = unrealsdk.ConstructObject(
        Class=unrealsdk.FindClass("WillowScrollingListDataProviderOptionsBase")
    )
    # See issue #45
    unrealsdk.GetEngine().GamePlayers[0].Actor.ServerRCon(
        f"set {provider.PathName(provider)} MenuDisplayName {name}"
    )
    _modded_data_provider_stack.append(provider)
    return provider


def _is_anything_shown(option_list: Sequence[Options.Base]) -> bool:
    """
    Helper function that recursively checks if anything in the provided option list is shown.

    Args:
        option_list: The list of options to check.
    Returns:
        True if at least one of the options in the list, or in any nested lists, is shown.
    """
    for option in option_list:
        if option.IsHidden:
            continue
        if isinstance(option, Options.Nested):
            if _is_anything_shown(option.Children):
                return True
        else:
            return True
    return False


def _TopLevelOptionsPopulate(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """ This function is called to create the options menu. We use it to inject our `MODS` menu. """
    # If not mods have accessable options, we want to disable the mods entry
    disabled = True
    for mod in ModObjects.Mods:
        if not mod.IsEnabled:
            continue
        if _is_anything_shown(mod.Options):
            disabled = False
            break

    def AddListItem(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        """
        This function is called every time an item is added to *any* menu list - we obviously can't
         use a generic hook.
        Using it cause it simplifies the code to add our own entry.
        """
        if params.Caption == "$WillowGame.WillowScrollingList.BackCaption":
            caller.AddListItem(_MOD_OPTIONS_EVENT_ID, _MOD_OPTIONS_MENU_NAME, disabled, False)

        return True

    unrealsdk.RunHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.OptionManager", AddListItem)

    unrealsdk.DoInjectedCallNext()
    caller.Populate(params.TheList)

    unrealsdk.RemoveHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.OptionManager")
    return False


def _WillowScrollingListOnClikEvent(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called on a few different events to do with these scrolling lists. We're
     interested in it to detect when you open up one of our modded menus.
    """
    global isMenuPluginMenu

    if params.Data.Type != "itemClick":
        return True

    # For some reason `caller.GetCurrentDataProvider()` returns a null object?
    provider = None
    for obj in caller.DataProviderStack:
        provider = obj.DataProvider.ObjectPointer
    if provider is None:
        return True

    if provider in _modded_data_provider_stack:
        # If you pressed the back button
        if params.Data.Index == len(_nested_options_stack[-1].Children):
            return True

        option = _nested_options_stack[-1].Children[params.Data.Index]
        if isinstance(option, Options.Nested):
            _nested_options_stack.append(option)
            caller.MyOwnerMovie.PlayUISound("MenuOpen")
            caller.PushDataProvider(_create_data_provider(option.Caption))
            return False
        elif isinstance(option, Options.Field):
            return False

    elif (
        provider.Class.Name == "WillowScrollingListDataProviderTopLevelOptions"
        and caller.IndexToEventId[params.Data.Index] == _MOD_OPTIONS_EVENT_ID
    ):
        caller.MyOwnerMovie.PlayUISound("MenuOpen")
        caller.PushDataProvider(_create_data_provider(_MOD_OPTIONS_MENU_NAME))
        return False

    return True


def _DataProviderOptionsBasePopulate(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to fill in a few of a scrolling lists. Our custom data providers are of
     this type, so we use it to populate the lists ourselves.
    """
    if caller not in _modded_data_provider_stack:
        return True

    # If we're on the first level we need to setup the inital list
    if len(_nested_options_stack) == 0:
        all_options: List[Options.Base] = []
        for mod in MenuManager.GetOrderedModList():
            if not mod.IsEnabled:
                continue

            one_shown = False
            for option in mod.Options:
                if option.IsHidden:
                    continue
                if not one_shown:
                    one_shown = True
                    all_options.append(_ModHeader(mod.Name))
                all_options.append(option)

        _nested_options_stack.append(Options.Nested(_MOD_OPTIONS_MENU_NAME, "", all_options))

    first_level = len(_nested_options_stack) == 1
    for idx, option in enumerate(_nested_options_stack[-1].Children):
        if option.IsHidden:
            continue

        indent = " " * _INDENT if first_level and not isinstance(option, _ModHeader) else ""

        if isinstance(option, Options.Spinner):
            spinner_idx: int
            if isinstance(option, Options.Boolean):
                spinner_idx = int(option.CurrentValue)
            else:
                spinner_idx = option.Choices.index(option.CurrentValue)

            params.TheList.AddSpinnerListItem(
                idx, indent + option.Caption, False, spinner_idx, option.Choices
            )
        elif isinstance(option, Options.Slider):
            params.TheList.AddSliderListItem(
                idx,
                indent + option.Caption,
                False,
                option.CurrentValue,
                option.MinValue,
                option.MaxValue,
                option.Increment,
            )
        elif isinstance(option, Options.Field):
            disabled = False
            if isinstance(option, Options.Nested):
                disabled = not _is_anything_shown(option.Children)
            params.TheList.AddListItem(idx, indent + option.Caption, disabled, False)

        caller.AddDescription(idx, option.Description)

    return False


def _DataProviderOptionsBaseOnPop(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when the data provider is popped off the stack, when you leave the menu.
    Unsuprisingly, we do the same with our stacks. We can also use it to save settings when you
     leave the outermost menu.
    """
    if caller in _modded_data_provider_stack:
        _modded_data_provider_stack.pop()
        _nested_options_stack.pop()
        if len(_modded_data_provider_stack) == 0:
            SettingsManager.SaveAllModSettings()

    return True


def _HandleSpinnerSliderChange(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    The two functions that have this hook get called when a spinner or slider changes value. We use
     the hook to update our version of the objects.
    """
    if caller not in _modded_data_provider_stack:
        return True

    changed_option = _nested_options_stack[-1].Children[params.EventID]

    new_value: Any
    if isinstance(changed_option, Options.Slider):
        new_value = int(params.NewSliderValue)
    elif isinstance(changed_option, Options.Boolean):
        new_value = bool(params.NewChoiceIndex)
    elif isinstance(changed_option, Options.Spinner):
        new_value = changed_option.Choices[params.NewChoiceIndex]
    else:
        raise RuntimeError(f"Option of bad type '{type(changed_option)}' somehow changed value.")

    def in_option_list(option_list: Sequence[Options.Base]) -> bool:
        return any(
            in_option_list(option.Children)
            if isinstance(option, Options.Nested)
            else option == changed_option
            for option in option_list
        )

    for mod in ModObjects.Mods:
        if in_option_list(mod.Options):
            # Calling this before updating the value
            mod.ModOptionChanged(changed_option, new_value)
            changed_option.CurrentValue = new_value
            break

    return True


unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderTopLevelOptions.Populate", "ModMenu.OptionManager", _TopLevelOptionsPopulate)
unrealsdk.RunHook("WillowGame.WillowScrollingList.OnClikEvent", "ModMenu.OptionManager", _WillowScrollingListOnClikEvent)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.Populate", "ModMenu.OptionManager", _DataProviderOptionsBasePopulate)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.OnPop", "ModMenu.OptionManager", _DataProviderOptionsBaseOnPop)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.HandleSpinnerChange", "ModMenu.OptionManager", _HandleSpinnerSliderChange)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderOptionsBase.HandleSliderChange", "ModMenu.OptionManager", _HandleSpinnerSliderChange)
