# ruff: noqa: D103
import traceback
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block, Type, prevent_hooking_direct_calls
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import EInputEvent, Mod, get_ordered_mod_list, hook
from mods_base.mod_list import base_mod

from .description import get_mod_description
from .favourites import is_favourite, toggle_favourite
from .options_menu import push_mod_list, push_mod_options

if TYPE_CHECKING:
    from enum import auto

    from unrealsdk.unreal._uenum import UnrealEnum  # pyright: ignore[reportMissingModuleSource]

    class ENetMode(UnrealEnum):
        NM_Standalone = auto()
        NM_DedicatedServer = auto()
        NM_ListenServer = auto()
        NM_Client = auto()
        NM_MAX = auto()

else:
    ENetMode = unrealsdk.find_enum("ENetMode")

MODS_EVENT_ID: int = 1417
MODS_MENU_NAME: str = "MODS"

# When the given control key is pressed in the dlc menu, we treat it as the relevant keyboard key
DLC_MENU_CONTROLLER_TO_KB_KEY_MAP = {
    "Gamepad_LeftStick_Up": "Up",
    "Gamepad_LeftStick_Down": "Down",
    "XboxTypeS_Start": "Enter",
    "XboxTypeS_A": "Enter",
    "XboxTypeS_B": "Escape",
    "XboxTypeS_Y": "Q",
    "XboxTypeS_LeftTrigger": "PageUp",
    "XboxTypeS_RightTrigger": "PageDown",
}

FRIENDLY_DISPLAY_VERSION = unrealsdk.config.get("willow2_mod_menu", {}).get(
    "display_version",
    base_mod.version,
)

drawn_mod_list: list[Mod] = []


# This hook is called any time any item is added to the scrolling list menus
# We only turn it on for a limited time while generating the main/pause menus, and use it to inject
# our mods menu instead.
@hook("WillowGame.WillowScrollingList:AddListItem")  # not auto enabled
def add_list_item(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    match args.Caption:
        case "$WillowMenu.WillowScrollingListDataProviderFrontEnd.DLC":
            return Block
        case (
            "$WillowMenu.WillowScrollingListDataProviderFrontEnd.Disconnect"
            | "$WillowMenu.WillowScrollingListDataProviderFrontEnd.Quit"
            | "$WillowMenu.WillowScrollingListDataProviderPause.Exit"
        ):
            # Add the mod entry right before the final option in the menu
            # Need to do it here, rather than while removing DLC, since the DLC menu does not exist
            # in AoDK or in the pause screen
            with prevent_hooking_direct_calls():
                obj.AddListItem(MODS_EVENT_ID, MODS_MENU_NAME, False, False)
            return None
        case _:
            return None


# These hooks are called to generate the relevant menu entries, we use them to enable and disable
# the per-item hook
@hook("WillowGame.WillowScrollingListDataProviderFrontEnd:Populate", immediately_enable=True)
@hook("WillowGame.WillowScrollingListDataProviderPause:Populate")
def frontend_populate_pre(*_: Any) -> None:
    add_list_item.enable()


@hook(
    "WillowGame.WillowScrollingListDataProviderFrontEnd:Populate",
    Type.POST_UNCONDITIONAL,
    immediately_enable=True,
)
@hook("WillowGame.WillowScrollingListDataProviderPause:Populate", Type.POST_UNCONDITIONAL)
def frontend_populate_post(*_: Any) -> None:
    add_list_item.disable()


# We want to add our 'M' -> Mods shortcut to the main/pause menu tooltips.
# At the same time while we're editing it, for some reason, gearbox deliberately remove the network
# mode and character select shortcuts while on PC.
# While there are simpler ways of doing this (e.g. override returning a fake platform), the default
# logic makes it look a bit ugly. Overwrite the entire thing to display it more nicely.
@hook("WillowGame.FrontendGFxMovie:UpdateTooltips", immediately_enable=True)
def frontend_update_tooltips(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block]:
    if (frontend_def := obj.MyFrontendDefinition) is None:
        return Block

    spacing: str = obj.TooltipSpacing

    tooltip: str = spacing + obj.SelectTooltip

    cancel: str = obj.CancelString
    if (
        obj.WPCOwner.WorldInfo.NetMode == ENetMode.NM_Client
        and len(obj.TheList.DataProviderStack) <= 1
    ):
        cancel = obj.DisconnectString
    tooltip += spacing + obj.CancelTooltip.replace("%PLAYER1", cancel)

    tooltip += "\n"

    if obj.CanShowSpectatorControls():
        tooltip += spacing + obj.SpectatorTooltip

    if obj.CanShowCharacterSelect(-1):
        tooltip += spacing + obj.CharacterSelectTooltip

    if obj.WPCOwner.WorldInfo.NetMode != ENetMode.NM_Client:
        tooltip += spacing + obj.NetworkOptionsTooltip

    tooltip += spacing + "[M] Mods"

    obj.SetVariableString(frontend_def.TooltipPath, obj.ResolveDataStoreMarkup(tooltip))
    return Block


def open_mods_menu(movie: UObject) -> None:
    """
    Opens the mods menu.

    Args:
        movie: The movie to open the mods menu under.
    """
    if movie.Class.Name == "FrontendGFxMovie":
        movie.CheckDownloadableContentListCompleted(movie.WPCOwner.GetMyControllerId(), True)
        return

    # A bunch of the stuff required for the dlc menu is only loaded on the main menu, so from the
    # pause screen we can't easily open it.
    # Instead, we use a standard option menu listing each mod.
    # Assuming if you're accessing it in game you just want to tweak some option, this isn't really
    # a big deal, you don't need all the extra info.

    pc = movie.WPCOwner
    frontend_def = movie.MyFrontendDefinition

    options = pc.GFxUIManager.PlayMovie(frontend_def.OptionsMovieDef)
    options.PreviousMenuHeader = movie.GetVariableString(frontend_def.HeaderPath)

    the_list = options.TheList
    the_list.DataProviderStack.clear()
    push_mod_list(the_list)

    movie.OptionsMovie = options


# Called whenever any entry in the menus is clicked. Since we use a custom event, we need a custom
# implementation to actually open it.
@hook("WillowGame.WillowScrollingListDataProviderFrontEnd:HandleClick", immediately_enable=True)
@hook("WillowGame.WillowScrollingListDataProviderPause:HandleClick")
def frontend_handle_click(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    if args.EventID == MODS_EVENT_ID:
        movie = args.TheList.MyOwnerMovie
        if not movie.IsOverlayMenuOpen():
            open_mods_menu(movie)
            return Block, True

    return None


# Called on pressing keys in the menus, we use it to add a key shortcut.
# Since pause menu inherits frontend, one hook is enough
@hook("WillowGame.FrontendGFxMovie:SharedHandleInputKey", immediately_enable=True)
def frontend_input_key(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    if args.ukey == "M" and args.uevent == EInputEvent.IE_Released and not obj.IsOverlayMenuOpen():
        open_mods_menu(obj)
        return Block, True

    return None


# Called whenever the dlc menu is refreshed, we use it to replace all the entries with our own
@hook("WillowGame.MarketplaceGFxMovie:RefreshDLC", immediately_enable=True)
def marketplace_refresh(obj: UObject, _2: WrappedStruct, _3: Any, _4: BoundFunction) -> type[Block]:
    obj.SetContentData([])  # Clear existing content

    obj.ClearFilters()
    obj.SetFilterFromStringAndSortNew("", "", "")

    obj.SetStoreHeader("Mods", False, FRIENDLY_DISPLAY_VERSION, "SDK Mod Manager")

    drawn_mod_list[:] = get_ordered_mod_list()
    for idx, mod in enumerate(drawn_mod_list):
        item, _ = obj.CreateMarketplaceItem(unrealsdk.make_struct("MarketplaceContent"))

        item.SetString(obj.Prop_offeringId, str(idx))
        item.SetString(obj.Prop_contentTitleText, mod.name)
        item.SetString(obj.Prop_costText, "By " + mod.author)
        item.SetString(obj.Prop_descriptionText, get_mod_description(mod, False))
        item.SetString(
            obj.Prop_statusText,
            # Same colour as author again
            f'<font color="#a1e4ef">{mod.version}</font>',
        )
        item.SetString(obj.Prop_messageText, mod.get_status())
        # For some odd reason this (and a bunch of the other bools we ignore), take input as floats
        item.SetFloat(obj.Prop_isNewOffer, float(is_favourite(mod)))

        obj.AddContentData(item)

    obj.PostContentLoaded(True)

    return Block


# Called on switching entries in the DLC menu. We use it just to update the favourite tooltip
@hook("WillowGame.MarketplaceGFxMovie:extOnOfferingChanged", immediately_enable=True)
def marketplace_offering_changed(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block]:
    if (data := args.Data) is None:
        return Block
    obj.PlayUISound("VerticalMovement")

    try:
        mod = drawn_mod_list[int(data.GetString(obj.Prop_offeringId))]
    except (ValueError, KeyError):
        return Block

    favourite_tooltip = (
        "" if mod == base_mod else ("[Q] Unfavourite" if is_favourite(mod) else "[Q] Favourite")
    )
    enable_tooltip = "[Space] Disable" if mod.is_enabled else "[Space] Enable"

    obj.SetTooltips(
        f"[Enter] Details\n{favourite_tooltip}",
        enable_tooltip,
    )
    return Block


# Quick set of helpers for working with our DLC menu keybinds.


def get_selected_mod(movie: UObject) -> Mod | None:
    """
    Gets the mod the user currently has selected.

    Args:
        movie: The current MarketplaceGFxMovie.
    Returns:
        The selected mod object, or None.
    """
    return (
        None
        if (item := movie.GetSelectedObject()) is None
        else drawn_mod_list[int(item.GetString(movie.Prop_offeringId))]
    )


def handle_toggle_favourite(movie: UObject) -> None:
    """
    Handles the user hitting the key to toggle favourite.

    Args:
        movie: The current MarketplaceGFxMovie.
    """
    if (mod := get_selected_mod(movie)) is not None:
        toggle_favourite(mod)
        movie.RefreshDLC()


def handle_toggle_mod(movie: UObject) -> None:
    """
    Handles the user hitting the key to toggle a mod.

    Args:
        movie: The current MarketplaceGFxMovie.
    """
    if (mod := get_selected_mod(movie)) is None or mod.enabling_locked:
        return

    old_enabled = mod.is_enabled
    (mod.disable if old_enabled else mod.enable)()

    # Extra safety layer in case the mod still decided to reject the toggle, no need to refresh if
    # we haven't changed state
    if old_enabled != mod.is_enabled:
        movie.RefreshDLC()


def handle_show_mod_details(movie: UObject) -> None:
    """
    Handles the user hitting the key to show mod details.

    Args:
        movie: The current MarketplaceGFxMovie.
    """
    if (mod := get_selected_mod(movie)) is None:
        return

    pc = movie.WPCOwner
    frontend = pc.GetFrontendMovie()
    frontend.HideMarketplaceMovie()

    options = pc.GFxUIManager.PlayMovie(frontend.MyFrontendDefinition.OptionsMovieDef)
    options.PreviousMenuHeader = MODS_MENU_NAME

    the_list = options.TheList
    the_list.DataProviderStack.clear()
    push_mod_options(the_list, mod)

    frontend.OptionsMovie = options
    frontend_options_hide_reopen_mod_menu.enable()


# Called on any key input in the DLC menu. We basically entirely overwrite it to add our own logic.
@hook("WillowGame.MarketplaceGFxMovie:ShopInputKey", immediately_enable=True)
def marketplace_input_key(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    key: str = args.ukey
    key = DLC_MENU_CONTROLLER_TO_KB_KEY_MAP.get(key, key)

    try:
        event: EInputEvent = args.uevent

        match key, event:
            # Page up/down are actually bugged on Gearbox's end: they look for both a released event
            # and a pressed or repeat, which is a contradition that can never be true.
            # Since there can be quite a few mods and we want to be able to scroll through them
            # quick, we're fixing Gearbox's bug here
            case "PageUp", (EInputEvent.IE_Pressed | EInputEvent.IE_Repeat):
                obj.ScrollDescription(True)
                return Block, True
            case "PageDown", (EInputEvent.IE_Pressed | EInputEvent.IE_Repeat):
                obj.ScrollDescription(False)
                return Block, True

            case "Q", EInputEvent.IE_Released:
                handle_toggle_favourite(obj)
                return Block, True

            case "SpaceBar", EInputEvent.IE_Released:
                handle_toggle_mod(obj)
                return Block, True

            case "Enter", EInputEvent.IE_Released:
                handle_show_mod_details(obj)
                return Block, True

            case _, _:
                pass

    except Exception:  # noqa: BLE001
        traceback.print_exc()

    # These inputs trigger logic in the standard menu, block them all, even if we got an exception.
    # If we let them through it usually ends up opening the steam store page.
    if key in {"Enter", "Q", "E"}:
        return Block, True

    return None


# Called to close the options menu. We temporarily enable it while in a mod options menu triggered
# from the main menu, to reopen the dlc menu afterwards.
@hook("WillowGame.FrontendGFxMovie:HideOptionsMovie", Type.POST)  # not auto enabled
def frontend_options_hide_reopen_mod_menu(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> None:
    frontend_options_hide_reopen_mod_menu.disable()
    open_mods_menu(obj)


# Called whenever the frontend movie (but not the pause one) starts. We use it just to make sure the
# previous hook isn't running, in case the menu got interrupted (e.g. if off host).
@hook("WillowGame.FrontendGFxMovie:Start", immediately_enable=True)
def frontend_start(*_: Any) -> None:
    frontend_options_hide_reopen_mod_menu.disable()
