import unrealsdk
from unrealsdk import *

""" Here we populate our mod manager with all of our mods that we've got loaded. """

def LoadModList(caller: UObject, function: UFunction, params: FStruct) -> bool:
    caller.ClearFilters()
    caller.SetFilterFromString("compatibility", "Utility Mods", "isCompatibility:1")
    caller.SetFilterFromString("seasonpass", "Gameplay Mods", "isSeasonPass:1")
    caller.SetFilterFromString("addon", "Content Mods", "isAddon:1")
    caller.SetFilterFromStringAndSortNew("all", "All Mods", "")

    caller.SetStoreHeader("Mods", 0, "By Abahbob", "Mod Manager")

    translationContext = GetEngine().GamePlayers[0].GetTranslationContext()
    for idx, mod in enumerate(unrealsdk.Mods):
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

    ControllerKeyMap = {
        "Gamepad_LeftStick_Up": "Up",
        "Gamepad_LeftStick_Down": "Down",
        "XboxTypeS_A": "Enter",
        "XboxTypeS_B": "Escape",
        "XboxTypeS_Y": "Q",
        "XboxTypeS_LeftTrigger": "PageUp",
        "XboxTypeS_RightTrigger": "PageDown"
    }
    if key in ControllerKeyMap:
        key = ControllerKeyMap[key]

    if key in ("Escape", "Up", "Down"):
        return True

    if event == 0 or event == 2:
        # These two are bugged on gearbox's end, we manually fix them
        if key == "PageUp":
            caller.ScrollDescription(True)
            return False
        elif key == "PageDown":
            caller.ScrollDescription(False)
            return False

    selectedObject = caller.GetSelectedObject()
    try:
        modIndex = int(selectedObject.GetString(caller.Prop_offeringId))
    except:
        return False

    mod = unrealsdk.Mods[modIndex]

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

    elif key not in ("Enter", "E", "XboxTypeS_Start", "XboxTypes_X"):
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
    for modFunc in unrealsdk.ModMenuOpened:
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

""" Hook whenever we change the currently selected mod in the mod manager.  """

def HookModSelected(caller: UObject, function: UFunction, params: FStruct) -> bool:
    selectedObject = caller.GetSelectedObject()
    try:
        modIndex = int(selectedObject.GetString(caller.Prop_offeringId))
    except TypeError:
        return

    mod = unrealsdk.Mods[modIndex]

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

def HookHandleClick(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if params.EventID == 4:
        gfxmovie = params.TheList.MyOwnerMovie
        if(gfxmovie.IsOverlayMenuOpen() == False):
            WPCOwner = unrealsdk.GetEngine().GamePlayers[0].Actor
            gfxmovie.CheckDownloadableContentListCompleted(WPCOwner.GetMyControllerId(), True)
        return False
    else:
        return True

RunHook("WillowGame.WillowScrollingListDataProviderFrontEnd.HandleClick", "HookHandleClick", HookHandleClick)


def HookGetSubmenuForEvent(caller: UObject, function: UFunction, params: FStruct) -> bool:
    return (params.EventID != 4)

RunHook("WillowGame.WillowScrollingListDataProviderFrontEnd.GetSubmenuForEvent", "HookGetSubmenuForEvent", HookGetSubmenuForEvent)

def HookContentMenu(caller: UObject, function: UFunction, params: FStruct) -> bool:
    WPCOwner = unrealsdk.GetEngine().GamePlayers[0].Actor
    caller.CheckDownloadableContentListCompleted(WPCOwner.GetMyControllerId(), True)
    return False

RunHook("WillowGame.FrontendGFxMovie.ShowMarketplaceMovie","HookContentMenu", HookContentMenu)


def HookMainMenuInput(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if params.ukey == "M" and params.uevent == 1:
        gfxmovie = caller
        if(gfxmovie.IsOverlayMenuOpen() == False):
            WPCOwner = unrealsdk.GetEngine().GamePlayers[0].Actor
            gfxmovie.CheckDownloadableContentListCompleted(WPCOwner.GetMyControllerId(), True)
    return True


RunHook("WillowGame.FrontendGFxMovie.SharedHandleInputKey", "ModMenuBind", HookMainMenuInput)
