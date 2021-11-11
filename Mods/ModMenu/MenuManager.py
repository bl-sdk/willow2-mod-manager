import unrealsdk
import json
import os
import re
import sys
import webbrowser
from functools import cmp_to_key
from typing import Dict, List, Set, Tuple

from . import VERSION_MAJOR, VERSION_MINOR
from . import DeprecationHelper as dh
from . import KeybindManager, ModObjects

__all__: Tuple[str, ...] = ()


_MODS_EVENT_ID: int = 1417
_MODS_MENU_NAME: str = "MODS"
_FAVOURITES_FILE: str = os.path.join(os.path.dirname(os.path.realpath(__file__)), "favourites.json")

_current_mod_list: List[ModObjects.SDKMod] = []
_favourite_mods: Set[str] = set()


def GetOrderedModList() -> List[ModObjects.SDKMod]:
    """
    Gets the list of mods properly ordered by favourite status, priority, and name.

    The first section of the list contains the favourited mods, the second all others. Each section
     is sorted by priority first, with higher priority appearing earlier in the list, and
     alphabetically by name second.

    Returns:
        The ordered list of mods.
    """
    def cmp(a: ModObjects.SDKMod, b: ModObjects.SDKMod) -> int:
        if a.Name in _favourite_mods and b.Name not in _favourite_mods:
            return -1
        elif a.Name not in _favourite_mods and b.Name in _favourite_mods:
            return 1

        if a.Priority == b.Priority:
            # Do some basic html stripping, so recolouring a name doesn't send the mod to the top
            # You can definitely fool this but it should be good enough
            a_stripped = re.sub("<.+?>", '', a.Name)
            b_stripped = re.sub("<.+?>", '', b.Name)
            if a_stripped < b_stripped:
                return -1
            elif a_stripped > b_stripped:
                return 1
            return 0

        return b.Priority - a.Priority

    return sorted(ModObjects.Mods, key=cmp_to_key(cmp))


class _General(ModObjects.SDKMod):
    Name: str = "General"
    Author: str = "PythonSDK"
    Description: str = (
        "Welcome to the Borderlands 2 SDK Mod Manager\n"
        "\n"
        "See below for options.\n"
    )
    Version: str = f"{VERSION_MAJOR}.{VERSION_MINOR}"

    SupportedGames: ModObjects.Game = (
        ModObjects.Game.BL2 | ModObjects.Game.TPS | ModObjects.Game.AoDK
    )
    Types: ModObjects.ModTypes = ModObjects.ModTypes.All

    Status: str = ""
    SettingsInputs: Dict[str, str] = {
        "H": "Help",
        "O": "Open Mods Folder",
    }

    def SettingsInputPressed(self, action: str) -> None:
        if action == "Help":
            webbrowser.open("http://bl-sdk.github.io/")
        elif action == "Open Mods Folder":
            os.startfile(os.path.join(os.path.dirname(sys.executable), "Mods"))


_general_instance = _General()


def _save_favourite_mods() -> None:
    """ Saves all favourited mods to disk. """
    if len(_favourite_mods) == 0:
        os.remove(_FAVOURITES_FILE)
    else:
        with open(_FAVOURITES_FILE, "w") as file:
            json.dump(list(_favourite_mods), file, indent=4)


def _load_favourite_mods() -> None:
    """ Loads all favourited mods from disk. """
    global _favourite_mods

    try:
        _favourite_mods = set()
        with open(_FAVOURITES_FILE) as file:
            names = json.load(file)
            # This looks redundant, but it makes sure only loaded mods are in the list
            for mod in ModObjects.Mods:
                if mod.Name in names:
                    _favourite_mods.add(mod.Name)

    except (FileNotFoundError, json.JSONDecodeError):
        pass


def _update_mod_list_item(
    mod: ModObjects.SDKMod,
    item: unrealsdk.UObject,
    movie: unrealsdk.UObject,
    translation_context: unrealsdk.UObject
) -> None:
    """ Updates a mod GFxObject to use all the latest fields from it's SDKMod. """
    item.SetString(movie.Prop_contentTitleText, mod.Name, translation_context)
    item.SetString(movie.Prop_costText, "By " + mod.Author, translation_context)
    item.SetString(movie.Prop_descriptionText, mod.Description, translation_context)
    item.SetString(
        movie.Prop_statusText,
        f"<font color=\"#A1E4EF\">{mod.Version}</font>",  # Make this the same colour as author
        translation_context
    )

    status = mod.Status
    if mod.Status == "Enabled":
        status = "<font color=\"#00FF00\">Enabled</font>"
    elif mod.Status == "Disabled":
        status = "<font color=\"#FF0000\">Disabled</font>"
    item.SetString(movie.Prop_messageText, status, translation_context)

    if isinstance(mod.Types, list):
        dh.PrintWarning(
            "Using lists for mod types is deprecated, combine types with bitwise or instead."
        )

    # For some odd reason these take in floats, but treat them as bools
    item.SetFloat(movie.Prop_isCompatibility, float(ModObjects.ModTypes.Utility in mod.Types))
    item.SetFloat(movie.Prop_isAddOn, float(ModObjects.ModTypes.Content in mod.Types))
    item.SetFloat(movie.Prop_isSeasonPass, float(ModObjects.ModTypes.Gameplay in mod.Types))
    item.SetFloat(movie.Prop_isMisc, float(ModObjects.ModTypes.Library in mod.Types))
    item.SetFloat(movie.Prop_isNewOffer, float(mod.Name in _favourite_mods or mod == _general_instance))


def _FrontEndPopulate(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to create the front end menu. We use it to replace the DLC caption and
     event id.
    """
    def AddListItem(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        """
        This function is called every time an item is added to *any* menu list - we obviously can't
         use a generic hook.
        Using it cause it simplifies the code to replace the caption.
        """
        if params.Caption == "$WillowMenu.WillowScrollingListDataProviderFrontEnd.DLC":
            return False

        inject_now = False
        if unrealsdk.GetEngine().GetCurrentWorldInfo().NetMode == 3:  # NM_Client
            inject_now = params.Caption == "$WillowMenu.WillowScrollingListDataProviderFrontEnd.Disconnect"
        else:
            inject_now = params.Caption == "$WillowMenu.WillowScrollingListDataProviderFrontEnd.Quit"

        if inject_now:
            caller.AddListItem(_MODS_EVENT_ID, _MODS_MENU_NAME, False, False)

        return True

    unrealsdk.RunHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.MenuManager", AddListItem)

    unrealsdk.DoInjectedCallNext()
    caller.Populate(params.TheList)

    unrealsdk.RemoveHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.MenuManager")
    return False


def _RefreshDLC(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to refresh the DLC menu. We're mostly interested in it because Gearbox
     has amazing code, and calls `OnDownloadableContentListRead` twice if you're offline.

    This happens right at the end of the function, so it's easiest to just recreate it.

    We can ignore the filter stuff, `OnDownloadableContentListRead` overwrites it right after, and
     we can also remove the small meaningless loading message that some people get hung up on.
    """
    if caller.bDelegateFired:
        caller.ShowMarketplaceElements(False)
        caller.SetShoppingTooltips(False, False, False, False, True)
        caller.SetContentData()
        caller.bDelegateFired = False

        # Here's the issue: earlier they setup a delegate for this call, but when it fails they
        #  also manually call the delgate again - we just don't
        caller.WPCOwner.OnlineSub.ContentInterface.ObjectPointer.ReadDownloadableContentList(
            caller.WPCOwner.GetMyControllerId()
        )
    return False


def _OnDownloadableContentListRead(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """ This function is called to fill in the dlc menu, we overwrite it with our mods instead. """
    global _current_mod_list

    _load_favourite_mods()

    caller.ClearFilters()
    caller.SetFilterFromString("compatibility", "Utility Mods", "isCompatibility:1")
    caller.SetFilterFromString("addon", "Content Mods", "isAddOn:1")
    caller.SetFilterFromString("seasonpass", "Gameplay Mods", "isSeasonPass:1")
    caller.SetFilterFromString("misc", "Libraries", "isMisc:1")
    caller.SetFilterFromStringAndSortNew("all", "All Mods", "")

    caller.SetStoreHeader("Mods", False, "By Abahbob", "Mod Manager")

    _current_mod_list = [_general_instance] + GetOrderedModList()  # type: ignore
    translation_context = unrealsdk.GetEngine().GamePlayers[0].GetTranslationContext()

    for idx, mod in enumerate(_current_mod_list):
        # This is weird and crashes if you don't have the second arg, but also crashes most the time
        #  when you try to access something on it - seems like a garbage pointer
        item, _ = caller.CreateMarketplaceItem()

        item.SetString(caller.Prop_offeringId, str(idx), translation_context)
        _update_mod_list_item(mod, item, caller, translation_context)

        caller.AddContentData(item)

    caller.PostContentLoaded(True)
    return False


def _ShopInputKey(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called on pretty much all input in the dlc menu. We use it to add our own
     custom binds, and to refresh mods after running them.
    """
    global _filter_idx
    key = params.ukey
    event = params.uevent

    controller_key_map = {
        "Gamepad_LeftStick_Up": "Up",
        "Gamepad_LeftStick_Down": "Down",
        "XboxTypeS_A": "Enter",
        "XboxTypeS_B": "Escape",
        "XboxTypeS_Y": "Q",
        "XboxTypeS_LeftTrigger": "PageUp",
        "XboxTypeS_RightTrigger": "PageDown"
    }
    if key in controller_key_map:
        key = controller_key_map[key]

    if key in ("Escape", "Up", "Down", "W", "S"):
        return True

    if event in (KeybindManager.InputEvent.Pressed, KeybindManager.InputEvent.Repeat):
        # These two are bugged on gearbox's end, we manually fix them
        if key == "PageUp":
            caller.ScrollDescription(True)
            return False
        elif key == "PageDown":
            caller.ScrollDescription(False)
            return False

    item = caller.GetSelectedObject()
    mod = _current_mod_list[int(item.GetString(caller.Prop_offeringId))]

    def update_item() -> None:
        _update_mod_list_item(
            mod,
            item,
            caller,
            unrealsdk.GetEngine().GamePlayers[0].GetTranslationContext()
        )
        # Unfortuantly it doesn't seem like there's a way to easily scroll back down to where you
        #  were, but we have to call this to actually update the visuals
        # This also resets filters, and for some reason none of the filter functions want to work
        #  right now either :/
        _RefreshDLC(caller, None, None)

    if key == "Q":
        if event == KeybindManager.InputEvent.Released:
            if mod == _general_instance:
                caller.CycleFilter()
            else:
                if mod.Name in _favourite_mods:
                    _favourite_mods.remove(mod.Name)
                else:
                    _favourite_mods.add(mod.Name)
                _save_favourite_mods()
                update_item()

            return False

    elif key in mod.SettingsInputs:
        if event == KeybindManager.InputEvent.Released:
            mod.SettingsInputPressed(mod.SettingsInputs[key])
            update_item()
            return False

    # These keys would try open the store if we let them continue
    elif key in ("Enter", "E"):
        return False

    return True


def _extOnOfferingChanged(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when the currently selected mod is changed. We use it to update the
     settings input tooltips.
    """
    caller.PlayUISound('VerticalMovement')

    try:
        idx = int(params.Data.GetString(caller.Prop_offeringId))
    # This seems to sometimes be called as we're refreshig the menu, making `GetString` return None
    except TypeError:
        return False

    mod = _current_mod_list[idx]

    on_left_column = False
    left_column = ""
    right_column = ""

    if mod == _general_instance:
        left_column = "[Q] Filter\n"
    elif mod.Name in _favourite_mods:
        left_column = "[Q] Unfavourite\n"
    else:
        left_column = "[Q] Favourite\n"

    for key, action in mod.SettingsInputs.items():
        entry = f"[{key}] {action}\n"
        if on_left_column:
            left_column += entry
        else:
            right_column += entry
        on_left_column = not on_left_column

    caller.SetTooltips(left_column, right_column)
    return False


def _FrontEndHandleClick(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when you click on any option on the main menu. We use it to open the dlc
     menu, even if you're offline or on epic.
    """
    if params.EventID == _MODS_EVENT_ID:
        movie = params.TheList.MyOwnerMovie
        if not movie.IsOverlayMenuOpen():
            movie.CheckDownloadableContentListCompleted(movie.WPCOwner.GetMyControllerId(), True)
        return False
    return True


def _SharedHandleInputKey(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called on pretty much all key input events on the main menu. We use it to open
     the dlc menu when you press "M".
    """
    if (
        params.ukey == "M"
        and params.uevent == KeybindManager.InputEvent.Released
        and not caller.IsOverlayMenuOpen()
    ):
        caller.CheckDownloadableContentListCompleted(caller.WPCOwner.GetMyControllerId(), True)
    return True


def _FrontEndUpdateTooltips(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to update the tooltips in the bottom right corner on the main menu. We
     replace it with our own message, adding character/network mode for bl2, and mentioning our new
     `M` for mods menu bind.

    Unfortuantly doing so requires recreating most of the function, there's no nice var we can read
     from - `SetVariableString` adds a bunch of extra formatting that's awkward to parse though if
     you tried using `GetVariableString`.
    """
    tooltip = caller.TooltipSpacing + caller.SelectTooltip

    cancel = caller.CancelString
    if caller.WPCOwner.WorldInfo.NetMode == 3:
        # There's no easy len() :/
        count = 0
        if caller.TheList is not None:
            for _ in caller.TheList.DataProviderStack:
                count += 1  # noqa: SIM113
        if count <= 1:
            cancel = caller.DisconnectString
    tooltip += caller.TooltipSpacing + caller.CancelTooltip.replace("%PLAYER1", cancel)

    tooltip += "\n"

    if caller.CanShowSpectatorControls():
        tooltip += caller.TooltipSpacing + caller.SpectatorTooltip

    if caller.CanShowCharacterSelect(-1):
        tooltip += caller.TooltipSpacing + caller.CharacterSelectTooltip

    if caller.WPCOwner.WorldInfo.NetMode != 3:
        tooltip += caller.TooltipSpacing + caller.NetworkOptionsTooltip

        # Only show on the main menu, not also the pause menu
        if caller.Class.Name == "FrontendGFxMovie":
            tooltip += caller.TooltipSpacing + "[M] Mods"

    if caller.MyFrontendDefinition is not None:
        caller.SetVariableString(
            caller.MyFrontendDefinition.TooltipPath,
            caller.ResolveDataStoreMarkup(tooltip)
        )

    return False


unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderFrontEnd.Populate", "ModMenu.MenuManager", _FrontEndPopulate)
unrealsdk.RunHook("WillowGame.MarketplaceGFxMovie.RefreshDLC", "ModMenu.MenuManager", _RefreshDLC)
unrealsdk.RunHook("WillowGame.MarketplaceGFxMovie.OnDownloadableContentListRead", "ModMenu.MenuManager", _OnDownloadableContentListRead)
unrealsdk.RunHook("WillowGame.MarketplaceGFxMovie.ShopInputKey", "ModMenu.MenuManager", _ShopInputKey)
unrealsdk.RunHook("WillowGame.MarketplaceGFxMovie.extOnOfferingChanged", "ModMenu.MenuManager", _extOnOfferingChanged)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderFrontEnd.HandleClick", "ModMenu.MenuManager", _FrontEndHandleClick)
unrealsdk.RunHook("WillowGame.FrontendGFxMovie.SharedHandleInputKey", "ModMenu.MenuManager", _SharedHandleInputKey)
unrealsdk.RunHook("WillowGame.FrontendGFxMovie.UpdateTooltips", "ModMenu.MenuManager", _FrontEndUpdateTooltips)
