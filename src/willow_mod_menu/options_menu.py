# ruff: noqa: D103
from collections.abc import Sequence
from typing import Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import ENGINE, BaseOption, Mod, hook

from .data_providers import (
    BACK_EVENT_ID,
    KB_TAG_HEADER,
    KB_TAG_UNREBINDABLE,
    KEYBINDS_EVENT_ID,
    OPTION_EVENT_ID_OFFSET,
    RESET_KEYBINDS_EVENT_ID,
    DataProvider,
)

data_provider_stack: list[DataProvider] = []

# Keep track of the latest WillowScrollingList we've been writing options to
# This is just to be a bit nicer to anyone trying to extend the menu, rather than needing to use
# find object calls to get back to it
latest_list: WeakPointer = WeakPointer(None)


def push_options(the_list: UObject, screen_name: str, options: Sequence[BaseOption]) -> None:
    """
    Pushes a screen containing the given set of options.

    Args:
        the_list: The option menu's WillowScrollingList to push to.
        screen_name: The name of this screen, use din the header.
        options: The options which should be included in this screen.
    """
    provider = unrealsdk.construct_object(
        "WillowScrollingListDataProviderKeyboardMouseOptions",
        ENGINE.Outer,
    )
    provider.MenuDisplayName = screen_name

    data_provider_stack.append(OptionsDataProvider(options))
    the_list.PushDataProvider(provider)

    global latest_list
    latest_list = WeakPointer(the_list)


def push_mod_options(the_list: UObject, mod: Mod) -> None:
    """
    Pushes a screen containing all the options for the given mod.

    Args:
        the_list: The option menu's WillowScrollingList to push to.
        mod: The mod to add options for.
    """
    provider = unrealsdk.construct_object(
        "WillowScrollingListDataProviderKeyboardMouseOptions",
        ENGINE.Outer,
    )
    provider.MenuDisplayName = mod.name

    data_provider_stack.append(ModOptionsDataProvider(mod=mod))
    the_list.PushDataProvider(provider)

    global latest_list
    latest_list = WeakPointer(the_list)


def push_mod_list(the_list: UObject) -> None:
    """
    Pushes an options screen containing a mod list.

    Args:
        the_list: The option menu's WillowScrollingList to push to.
    """
    provider = unrealsdk.construct_object(
        "WillowScrollingListDataProviderKeyboardMouseOptions",
        ENGINE.Outer,
    )
    provider.MenuDisplayName = "MODS"

    data_provider_stack.append(ModListDataProvider())
    the_list.PushDataProvider(provider)

    global latest_list
    latest_list = WeakPointer(the_list)


# Avoid circular imports
from .data_providers.mod_list import ModListDataProvider  # noqa: E402
from .data_providers.mod_options import ModOptionsDataProvider  # noqa: E402
from .data_providers.options import OptionsDataProvider  # noqa: E402

_GET_WILLOW_GLOBALS = unrealsdk.find_class("WillowGlobals").ClassDefaultObject.GetWillowGlobals


# Called when filling in the kb/m options menu. This version shows our entries instead.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:Populate",
    immediately_enable=True,
)
def dataprovider_kbm_populate(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    # This is opening the standard keyboard/mouse options
    if not data_provider_stack:
        return None

    the_list: UObject = args.TheList

    # Replicate a bit of the normal populate function
    obj.MyOptionsMovie = (owner_movie := the_list.MyOwnerMovie)

    obj.WPCOwner = (pc := owner_movie.WPCOwner)
    if pc is not None:
        pc.SetupInputDevices()
    obj.CurrentKeyBindSelection = -1

    obj.DeviceCollection = _GET_WILLOW_GLOBALS().GetGlobalsDefinition().InputDeviceCollection
    obj.InitKeyBinding(the_list)

    # Do our custom population
    data_provider_stack[-1].populate(obj, the_list)

    # Since our modded menus start with an empty data provider stack, but logically exist under
    # other menus, add the back caption - the standard machinery won't
    if len(data_provider_stack) == 1:
        the_list.AddListItem(BACK_EVENT_ID, the_list.BackCaption, False, False)

    # Without this, the description of the first entry doesn't show up until you reselect it
    obj.UpdateDescriptionText(OPTION_EVENT_ID_OFFSET, the_list)

    return Block


# Called when filling in the kb/m options menu with it's keybinds. We need to use this to set the
# keys for each entry, can't do it using the above hook for some reason.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:extOnPopulateKeys",
    immediately_enable=True,
)
def dataprovider_kbm_populate_keys(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    if not data_provider_stack:
        return None

    data_provider_stack[-1].populate_keybind_keys(obj)
    return Block


# Called when clicking something in the kb/m options menu - we use it for the same.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:HandleClick",
    immediately_enable=True,
)
def dataprovider_kbm_handle_click(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    if not data_provider_stack:
        return None

    event_id: int = args.EventID
    the_list: UObject = args.TheList

    if event_id in {BACK_EVENT_ID, RESET_KEYBINDS_EVENT_ID}:
        return None
    if event_id == KEYBINDS_EVENT_ID:
        return Block, True

    handled = data_provider_stack[-1].handle_click(event_id, the_list)
    return Block, handled


# Called when changing a spinner in *any* options menu - there isn't a kb/m specific override of
# this. We use it to track our events for the same.
@hook(
    "WillowGame.WillowScrollingListDataProviderOptionsBase:HandleSpinnerChange",
    immediately_enable=True,
)
def dataprovider_base_handle_spinner_change(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    if not data_provider_stack:
        return None

    event_id: int = args.EventID
    new_choice_idx: int = args.NewChoiceIndex
    data_provider_stack[-1].handle_spinner_change(event_id, new_choice_idx)

    # Don't want to let the base provider handling through, even if we didn't handle this event
    # above, since normally it can't trigger under the kb/m menu, and if we let it pass it might try
    # write to settings.
    # Unconditionally return that we handled it.
    return Block, True


# Called when changing a slider in *any* options menu, same as above
@hook(
    "WillowGame.WillowScrollingListDataProviderOptionsBase:HandleSliderChange",
    immediately_enable=True,
)
def dataprovider_base_handle_slider_change(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    if not data_provider_stack:
        return None

    event_id: int = args.EventID
    new_value: int = args.NewSliderValue
    data_provider_stack[-1].handle_slider_change(event_id, new_value)

    # Same as above, unconditionally return handled
    return Block, True


# Called when closing any scrolling list menu. We use it to keep our stack in sync. This relies on
# the fact that once you enter an modded menu, all child menus in the stack are also always modded.
@hook("WillowGame.WillowScrollingList:HandlePopList", immediately_enable=True)
def scrolling_list_handle_pop(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> None:
    if not data_provider_stack:
        return

    provider = data_provider_stack.pop()

    # On leaving a mod options screen, also make sure to save it
    if isinstance(provider, ModOptionsDataProvider):
        provider.mod.save_settings()

    if not data_provider_stack:
        obj.MyOwnerMovie.WPCOwner.GetFrontendMovie().HideOptionsMovie()


# Called when starting a rebind. We use it to block rebinding some entries in our custom menus.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:DoBind",
    immediately_enable=True,
)
def dataprovider_kbm_do_bind(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    if not data_provider_stack:
        return None

    tag: str = obj.KeyBinds[obj.CurrentKeyBindSelection].Tag
    return Block if tag.startswith((KB_TAG_HEADER, KB_TAG_UNREBINDABLE)) else None


# Called to check if a key is allowed to be bound to. By default this just blocks controller keys.
# We override it to always allow everything while in our modded menus.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:AllowBindKey",
    immediately_enable=True,
)
def dataprovider_kbm_allow_bind_key(*_: Any) -> tuple[type[Block], bool] | None:
    if not data_provider_stack:
        return None
    return Block, True


# Called after finishing a rebind. We update our own keys to the new value.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:BindCurrentSelection",
    immediately_enable=True,
)
def dataprovider_kbm_bind_current_selection(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    if not data_provider_stack:
        return None

    data_provider_stack[-1].handle_key_rebind(obj, args.key)
    return Block


# Called on resetting the key binds, we use it to reset our own.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:OnResetKeyBindsButtonClicked",
    immediately_enable=True,
)
def dataprovider_kbm_on_reset_keys(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    if not data_provider_stack:
        return None

    if args.Dlg.DialogResult == "Yes":
        data_provider_stack[-1].handle_reset_keybinds()

        # Redraw everything to update the shown keys
        obj.extOnPopulateKeys()

    return Block
