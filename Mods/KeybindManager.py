import unrealsdk
from unrealsdk import *
from collections import namedtuple

from .Util import getLoadedMods

KeybindBinding = namedtuple('KeybindBinding', ['Name', 'Key'])

""" This function adds all of our keybinds to the keybind menu. """

def HookInitKeyBinding(caller: UObject, function: UFunction, params: FStruct) -> bool:
    for mod in getLoadedMods():
        if mod.Keybinds:
            tag = f"unrealsdk.seperator.{mod.Name}"
            caller.AddKeyBindEntry(tag, tag, mod.Name)
        for GameInput in mod.Keybinds:
            InputName, InputKey = GameInput
            tag = f"unrealsdk.input.{mod.Name}.{InputName}"
            caller.AddKeyBindEntry(tag, tag, f"        {InputName}")
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
        if keyBind.Tag.startswith("unrealsdk"):
            if keyBind.Tag.startswith("unrealsdk.seperator"):
                keyBind.Object.SetString("value", "")
                keyBind.Object.SetVisible(False)
            else:
                for mod in getLoadedMods():
                    if mod.Name == keyBind.Tag.split('.')[2]:
                        for GameInput in mod.Keybinds:
                            if keyBind.Tag == f"unrealsdk.input.{mod.Name}.{GameInput[0]}":
                                keyBind.CurrentKey = GameInput[1]
        if keyBind.CurrentKey != "None":
            for mod in getLoadedMods():
                for GameInput in mod.Keybinds:
                    if keyBind.CurrentKey == GameInput[0]:
                        GameInput[1] = "None"
                        mod.GameInputRebound(binding.Name[0], "None")
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
    if selectedKeyBind.Tag.startswith("unrealsdk.seperator"):
        return False

    PreviousKeyBinds = {bind.Tag: bind.CurrentKey for bind in caller.KeyBinds}

    DoInjectedCallNext()
    caller.BindCurrentSelection(params.Key)

    for bind in caller.KeyBinds:
        if bind.Tag.startswith("unrealsdk") and bind.Tag in PreviousKeyBinds.keys() and PreviousKeyBinds[bind.Tag] != bind.CurrentKey:
            for mod in getLoadedMods():
                if mod.Name == bind.Tag.split('.')[2]:
                    for GameInput in mod.Keybinds:
                        if bind.Tag == f"unrealsdk.input.{mod.Name}.{GameInput[0]}":
                            GameInput[1] = bind.CurrentKey
                            mod.GameInputRebound(GameInput[0], bind.CurrentKey)

    translationContext = GetEngine().GamePlayers[0].GetTranslationContext()

    for keyBind in caller.KeyBinds:
        keyBind.Object.SetString(
            "value",
            GetFixedLocalizedKeyName(caller, keyBind.CurrentKey),
            translationContext,
        )

    caller.ControllerMappingClip.InvalidateKeyData()
    return False

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.BindCurrentSelection", "HookBindCurrentSelection",HookBindCurrentSelection)


def HookDoBind(caller: UObject, function: UFunction, params: FStruct) -> bool:
    if caller.KeyBinds[caller.CurrentKeyBindSelection].Tag.startswith("unrealsdk.seperator"):
        return False
    return True

RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.DoBind","HookDoBind",HookDoBind)


""" Hook onto player input so we know when a mod's keybinds were pressed. """

def HookInputKey(caller: UObject, function: UFunction, params: FStruct) -> bool:
    # If we do not have a binding associated with this key, we ignore it.
    for mod in getLoadedMods():
        for GameInput in mod.Keybinds:
            if GameInput[1] == params.Key:
                # An event of 0 correlates to the key being pressed.
                if params.Event == 0:
                    mod.GameInputPressed(KeybindBinding(*GameInput))
                # An event of 0 correlates to the key being released.
                elif params.Event == 1:
                    mod.GameInputReleased(KeybindBinding(*GameInput))
                return False
    return True

RunHook("WillowGame.WillowUIInteraction.InputKey", "HookInputKey", HookInputKey)