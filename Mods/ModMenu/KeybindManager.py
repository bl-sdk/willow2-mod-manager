import unrealsdk
import functools
import inspect
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, ClassVar, Dict, Optional, Tuple, Union

from . import DeprecationHelper as dh
from . import MenuManager, ModObjects, SettingsManager

__all__: Tuple[str, ...] = (
    "InputEvent",
    "Keybind",
    "KeybindCallback",
)


class InputEvent(IntEnum):
    """
    Any enum holding the various input event types.

    Sourced from https://docs.unrealengine.com/en-US/API/Runtime/Engine/Engine/EInputEvent/index.html
    """
    Pressed = 0
    Released = 1
    Repeat = 2
    DoubleClick = 3
    Axis = 4


KeybindCallback = Union[Callable[[], None], Callable[[InputEvent], None]]


@dataclass
class Keybind:
    """
    A simple dataclass representing a keybind.

    Attributes:
        Name: The name of the keybind.
        Key:
            The key this bind is currently bound to. See the following link for reference.
            https://api.unrealengine.com/udk/Three/KeyBinds.html#Mappable%20keys
        IsRebindable:
            If this bind can be rebound. If not, it also won't be placed in the settings file. Note
             that this does not prevent changing the value on this object manually.
        IsHidden: If the keybind should be hidden from the keybinds menu.

        OnPress:
            A callback for when the key is pressed. If provided, it will be called instead of the
             mod's `GameInputPressed`. If it accepts an argument, it will get passed an `InputEvent`
             value, and be called on any event. If it doesn't, it will only be called on `Pressed`
             events.

        DefaultKey: The original value of Key. You do not provide this, it is set automatically.
    """
    Name: str
    Key: str = "None"
    IsRebindable: bool = True
    IsHidden: bool = False

    OnPress: Optional[KeybindCallback] = None

    DefaultKey: str = field(default=Key, init=False)

    _list_deprecation_warning: ClassVar[str] = (
        "Using lists for keybinds is deprecated, use 'ModMenu.Keybind' instances instead."
    )

    def __post_init__(self) -> None:
        self.DefaultKey = self.Key

    @dh.Deprecated(_list_deprecation_warning)
    def __getitem__(self, i: int) -> str:
        if not isinstance(i, int):
            raise TypeError(f"list indices must be integers or slices, not {type(i)}")
        if i == 0:
            return self.Name
        elif i == 1:
            return self.Key
        else:
            raise IndexError("list index out of range")

    @dh.Deprecated(_list_deprecation_warning)
    def __setitem__(self, i: int, val: str) -> None:
        if not isinstance(i, int):
            raise TypeError(f"list indices must be integers or slices, not {type(i)}")
        if i == 0:
            self.Name = val
        elif i == 1:
            self.Key = val
        else:
            raise IndexError("list index out of range")


"""
We put all keybinds into their own "MODDED KEYBINDS" menu.
It's important to realize however that, internally, it's still the exact same menu as the one for
 the normal keybinds.
We have one keybinds menu object with one keybind list, we just, based on which menu item you
 select, filter dowc the keybinds that you can actually see.
"""


_NORMAL_CONTROLLER_NAME = unrealsdk.GetEngine().Localize("KeyBindings", "Caption", "WillowMenu")
_MODDED_CONTROLLER_NAME = "Modded " + _NORMAL_CONTROLLER_NAME

_NORMAL_KEYBINDS_EVENT_ID: int = 1000
_MODDED_EVENT_ID: int = 1417
_MODDED_KEYBINDS_CAPTION: str = _MODDED_CONTROLLER_NAME.upper()

_TAG_MODDED: str = "unrealsdk"
_TAG_SEPERATOR: str = f"{_TAG_MODDED}.seperator"
_TAG_UNREBINDABLE: str = f"{_TAG_MODDED}.unrebindable"
_TAG_INPUT: str = f"{_TAG_MODDED}.input"

_INDENT: int = 4

# Need a dict because normal binds always take the first bunch of indexes
_modded_keybind_map: Dict[int, Keybind] = {}
_is_modded_keybind_menu: bool = False


def _get_fixed_localized_key_name(provider: unrealsdk.UObject, key: str) -> str:
    """
    A wrapper around `GetLocalizedKeyName` that fills a few gaps left by it.

    Args:
        provider: The keyboard/mouse menu data provider.
        key: The key to get the name of.
    Returns:
        The localized key name.
    """

    custom_name_map = {
        "None": "",
        "Quote": "'",
        "Backslash": "\\ "  # The space is important for some reason
    }

    if key.strip() == "" or key is None:
        return ""
    elif key in custom_name_map:
        return custom_name_map[key]

    name = provider.GetLocalizedKeyName(key)
    if name is None:
        return ""
    # TODO: Work out what is causing this to be returned and patch that instead
    elif name.startswith("?INT?"):
        return key
    else:
        return str(name)


def _KeyboardMouseOptionsPopulate(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to create the kb/m settings menu. We use it to inject our own
     "MODDED KEYBINDS" menu.
    """
    # If we have no modded binds, disable the menu
    disabled = True
    for mod in ModObjects.Mods:
        if not mod.IsEnabled:
            continue
        for input in mod.Keybinds:
            if isinstance(input, Keybind) and input.IsHidden:
                continue
            disabled = False
            break
        if not disabled:
            break

    def AddListItem(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        """
        This function is called every time an item is added to *any* menu list - we obviously can't
         use a generic hook.
        Using it cause it simplifies the code to add our own entry.
        """
        if params.Caption != "$WillowMenu.MenuOptionDisplayNames.KeyBinds":
            return True

        # Want ours to display after the normal keybinds option
        unrealsdk.DoInjectedCallNext()
        caller.AddListItem(params.EventID, params.Caption, params.bDisabled, params.bNew)

        caller.AddListItem(_MODDED_EVENT_ID, _MODDED_KEYBINDS_CAPTION, disabled, False)
        return False

    unrealsdk.RunHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.KeybindManager", AddListItem)

    unrealsdk.DoInjectedCallNext()
    caller.Populate(params.TheList)
    caller.AddDescription(_MODDED_EVENT_ID, "$WillowMenu.MenuOptionDisplayNames.KeyBindsDesc")

    unrealsdk.RemoveHook("WillowGame.WillowScrollingList.AddListItem", "ModMenu.KeybindManager")

    return False


def _extOnPopulateKeys(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called to load the list of keybinds. We add our own binds onto the end of the
     list after it's called.
    """
    global _modded_keybind_map

    unrealsdk.DoInjectedCallNext()
    caller.extOnPopulateKeys()

    _modded_keybind_map = {}
    for mod in MenuManager.GetOrderedModList():
        if not mod.IsEnabled:
            continue

        if all(isinstance(k, Keybind) and k.IsHidden for k in mod.Keybinds):
            continue

        tag = f"{_TAG_SEPERATOR}.{mod.Name}"
        idx = caller.AddKeyBindEntry(tag, tag, mod.Name)
        caller.KeyBinds[idx].CurrentKey = "None"

        for input in mod.Keybinds:
            name: str
            key: str
            rebindable: bool
            if isinstance(input, Keybind):
                if input.IsHidden:
                    continue
                name = input.Name
                key = input.Key
                rebindable = input.IsRebindable
            else:
                dh.PrintWarning(Keybind._list_deprecation_warning)
                name = input[0]
                key = input[1]
                rebindable = True

            tag = (_TAG_INPUT if rebindable else _TAG_UNREBINDABLE) + f".{mod.Name}.{name}"
            idx = caller.AddKeyBindEntry(tag, tag, " " * _INDENT + name)

            _modded_keybind_map[idx] = input

            if not rebindable:
                key = "[ ]" if key == "None" else f"[ {key} ]"
            caller.KeyBinds[idx].CurrentKey = key

    return False


def _HandleSelectionChangeRollover(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    The two functions with this hook get called when your menu selection changes. We use them to
     detect when you open each keybinds menu, and filter them down accordingly.
    """
    global _is_modded_keybind_menu

    if params.EventID == _MODDED_EVENT_ID:
        _is_modded_keybind_menu = True
        caller.ControllerMappingClip.GetObject("controller").SetText(_MODDED_CONTROLLER_NAME)
    elif params.EventID == _NORMAL_KEYBINDS_EVENT_ID:
        _is_modded_keybind_menu = False
        caller.ControllerMappingClip.GetObject("controller").SetText(_NORMAL_CONTROLLER_NAME)
    else:
        _is_modded_keybind_menu = False
        return True

    # Recreate the visual keybind list, filtered down to just the relevant binds
    caller.ControllerMappingClip.EmptyKeyData()
    for bind in caller.KeyBinds:
        if _is_modded_keybind_menu:
            if not bind.Tag.startswith(_TAG_MODDED):
                continue
        else:
            if bind.Tag.startswith(_TAG_MODDED):
                continue

        bind.Object = caller.ControllerMappingClip.AddKeyData(
            bind.Tag, bind.Caption, _get_fixed_localized_key_name(caller, bind.CurrentKey)
        )
    caller.ControllerMappingClip.InvalidateKeyData()

    # Conveniently, instantly turning this off + on again will re-show the animation
    caller.ShowControllerMapping(False)
    caller.ShowControllerMapping(True)

    caller.UpdateDescriptionText(params.EventID, params.TheList)
    return False


def _DoBind(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when you start rebinding a key, blocking it on seperators and uneditable
    keybinds.
    """
    tag = caller.KeyBinds[caller.CurrentKeyBindSelection].Tag
    if tag.startswith(_TAG_SEPERATOR) or tag.startswith(_TAG_UNREBINDABLE):
        return False
    return True


def _BindCurrentSelection(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when a key is rebound. We basically entirely rewrite it, making sure to
     update modded binds, as well as adding the ability to unbind modded keys.

    Unbinding default binds won't save, so doing so has been disabled.
    If you want to look into it more, it's probably caused by how it gets saved to your profile,
     follow the trail from `OnPop()`.
    """
    selected_idx = caller.CurrentKeyBindSelection
    selected_bind = caller.KeyBinds[selected_idx]

    translation_context = unrealsdk.GetEngine().GamePlayers[0].GetTranslationContext()

    if selected_bind.Tag.startswith(_TAG_SEPERATOR):
        return False

    key = params.Key
    if selected_bind.CurrentKey == key:
        # Don't allow unbinding defaults
        if selected_idx not in _modded_keybind_map:
            return False
        key = "None"

    if selected_idx in _modded_keybind_map:
        input = _modded_keybind_map[selected_idx]
        if isinstance(input, Keybind):
            input.Key = key
        else:
            dh.PrintWarning(Keybind._list_deprecation_warning)
            input[1] = key

    # Find if we have to swap the bind with anything
    for idx, bind in enumerate(caller.KeyBinds):
        if bind.CurrentKey != params.Key:
            continue
        if bind == selected_bind:
            continue

        # Allow multiple "None" binds
        # Using continue rather than a break so that it falls into the else
        if key == "None":
            continue

        # If you would swap a default bind to None
        if selected_bind.CurrentKey == "None" and idx not in _modded_keybind_map:
            # Show a small explanatory dialog.
            dialog = caller.WPCOwner.GFxUIManager.ShowDialog()

            title = dialog.Localize("dlgKeyBindSwap", "Caption", "WillowMenu")
            msg = (
                f"Unable to bind \"{selected_bind.Caption}\" to \"{key}\".\n"
                f"\n"
                f"Doing so would cause the default bind \"{bind.Caption}\" to become unbound."
            )
            dialog.SetText(title, msg)
            dialog.SetVariableString("tooltips.text", "$<Strings:WillowMenu.TitleMenu.BackBar>")
            dialog.ApplyLayout()

            def HandleInputKey(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
                """
                This function is called on any key event on any `WillowGFxDialogBox`. Only using it
                 to replicate adding `HandleKeySwapDialog` as a delegate, sdk can't quite do so yet.
                """
                if caller != dialog:
                    return True

                if (
                    params.uevent == InputEvent.Released
                    and params.ukey in ("Escape", "XboxTypeS_B", "XboxTypeS_Back")
                ):
                    dialog.Close()
                    unrealsdk.RemoveHook("WillowGame.WillowGFxDialogBox.HandleInputKey", "ModMenu.KeybindManager")
                return True

            unrealsdk.RunHook("WillowGame.WillowGFxDialogBox.HandleInputKey", "ModMenu.KeybindManager", HandleInputKey)

            return False

        if idx in _modded_keybind_map:
            input = _modded_keybind_map[idx]
            if isinstance(input, Keybind):
                input.Key = selected_bind.CurrentKey
            else:
                dh.PrintWarning(Keybind._list_deprecation_warning)
                input[1] = selected_bind.CurrentKey

        unrealsdk.DoInjectedCallNext()
        caller.BindCurrentSelection(key)

        bind.Object.SetString(
            "value",
            _get_fixed_localized_key_name(caller, bind.CurrentKey),
            translation_context
        )
    else:
        caller.bNeedsToSaveKeyBinds = True
        selected_bind.CurrentKey = key

    selected_bind.Object.SetString(
        "value",
        _get_fixed_localized_key_name(caller, selected_bind.CurrentKey),
        translation_context
    )

    caller.ControllerMappingClip.InvalidateKeyData()

    return False


def _OnResetKeyBindsButtonClicked(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called when the user resets all keybinds - unsuprisingly we do the same.

    There is no easy way to store default binds for legacy mods that still provide them as lists,
     so they will not be reset.
    """
    unrealsdk.DoInjectedCallNext()
    caller.OnResetKeyBindsButtonClicked(params.Dlg, params.ControllerId)

    if params.Dlg.DialogResult != "Yes":
        return False

    for input in _modded_keybind_map.values():
        if isinstance(input, Keybind):
            input.Key = input.DefaultKey

    return False


def _KeyboardMouseOptionsOnPop(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called upon leaving the keyboard/mouse settings menu. We save all mod settings
     (including keybinds) when this happens.
    """
    SettingsManager.SaveAllModSettings()
    return True


def _InputKey(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called on basically all player input, while ingame. Using it for our callbacks.
    """
    for mod in ModObjects.Mods:
        if not mod.IsEnabled:
            continue

        for input in mod.Keybinds:
            returned_input: Keybind
            if isinstance(input, Keybind):
                returned_input = input
            else:
                dh.PrintWarning(Keybind._list_deprecation_warning)
                returned_input = Keybind(*input)

            if returned_input.Key != params.Key:
                continue

            # Prefer the callback
            function = (
                returned_input.OnPress or functools.partial(mod.GameInputPressed, returned_input)
            )

            if len(inspect.signature(function).parameters) == 0:
                if params.Event == InputEvent.Pressed:
                    function()
                    return False
            else:
                function(InputEvent(params.Event))
                return False
    return True


unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.Populate", "ModMenu.KeybindManager", _KeyboardMouseOptionsPopulate)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.extOnPopulateKeys", "ModMenu.KeybindManager", _extOnPopulateKeys)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.HandleSelectionChange", "ModMenu.KeybindManager", _HandleSelectionChangeRollover)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.HandleSelectionRollover", "ModMenu.KeybindManager", _HandleSelectionChangeRollover)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.DoBind", "ModMenu.KeybindManager", _DoBind)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.BindCurrentSelection", "ModMenu.KeybindManager", _BindCurrentSelection)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.OnResetKeyBindsButtonClicked", "ModMenu.KeybindManager", _OnResetKeyBindsButtonClicked)
unrealsdk.RunHook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions.OnPop", "ModMenu.KeybindManager", _KeyboardMouseOptionsOnPop)
unrealsdk.RunHook("WillowGame.WillowUIInteraction.InputKey", "ModMenu.KeybindManager", _InputKey)
