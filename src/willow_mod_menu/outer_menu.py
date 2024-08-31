# ruff: noqa: D103
import traceback
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk.hooks import Block, Type, inject_next_call
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import CoopSupport, EInputEvent, Game, Mod, get_ordered_mod_list, hook
from mods_base.mod_list import base_mod

from .favourites import is_favourite, toggle_favourite

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
    "XboxTypeS_A": "Enter",
    "XboxTypeS_B": "Escape",
    "XboxTypeS_Y": "Q",
    "XboxTypeS_LeftTrigger": "PageUp",
    "XboxTypeS_RightTrigger": "PageDown",
}

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
            inject_next_call()
            obj.AddListItem(MODS_EVENT_ID, MODS_MENU_NAME, False, False)
            return Block
        case "$WillowMenu.WillowScrollingListDataProviderPause.Exit":
            inject_next_call()
            obj.AddListItem(MODS_EVENT_ID, MODS_MENU_NAME, False, False)
            return None
        case _:
            return None


# These hooks are called to generate the relevant menu entries, we use them to enable and disable
# the per-item hook
@hook("WillowGame.WillowScrollingListDataProviderFrontEnd:Populate", auto_enable=True)
@hook("WillowGame.WillowScrollingListDataProviderPause:Populate")
def frontend_populate_pre(*_: Any) -> None:
    add_list_item.enable()


@hook(
    "WillowGame.WillowScrollingListDataProviderFrontEnd:Populate",
    Type.POST_UNCONDITIONAL,
    auto_enable=True,
)
@hook("WillowGame.WillowScrollingListDataProviderPause:Populate", Type.POST_UNCONDITIONAL)
def frontend_populate_post(*_: Any) -> None:
    add_list_item.disable()


# We want to add our 'M' -> Mods shortcut to the main/pause menu tooltips.
# At the same time while we're editing it, for some reason, gearbox deliberately remove the network
# mode and character select shortcuts while on PC.
# While there are simpler ways of doing this (e.g. override returning a fake platform), the default
# logic makes it look a bit ugly. Overwrite the entire thing to display it more nicely.
@hook("WillowGame.FrontendGFxMovie:UpdateTooltips", auto_enable=True)
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
    if obj.WPCOwner.WorldInfo.NetMode == ENetMode.NM_Client and len(obj.TheList) <= 1:
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

    # TODO: implement
    print("OPEN PAUSE MODS")


# Called whenever any entry in the menus is clicked. Since we use a custom event, we need a custom
# implementation to actually open it.
@hook("WillowGame.WillowScrollingListDataProviderFrontEnd:HandleClick", auto_enable=True)
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
@hook("WillowGame.FrontendGFxMovie:SharedHandleInputKey", Type.PRE, auto_enable=True)
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


def create_description_text(mod: Mod) -> str:
    """
    Creates the text to use for a mod's description option.

    Args:
        mod: The mod to create the title for.
    Returns:
        The description text.
    """
    blocks: list[str] = []

    match mod.coop_support:
        case CoopSupport.Unknown:
            # Choose this size and colour to make it look the same as the author text above it
            # Can only add one line there, so hiding this at the top of the description
            blocks.append("<font size='14' color='#a1e4ef'>Coop Support: Unknown</font>")
        case CoopSupport.Incompatible:
            blocks.append(
                "<font size='14' color='#a1e4ef'>Coop Support:</font>"
                " <font size='14'color='#ffff00'>Incompatible</font>",
            )
        case CoopSupport.RequiresAllPlayers:
            blocks.append(
                "<font size='14' color='#a1e4ef'>Coop Support: Requires All Players</font>",
            )
        case CoopSupport.ClientSide:
            blocks.append("<font size='14' color='#a1e4ef'>Coop Support: Client Side</font>")

    if Game.get_current() not in mod.supported_games:
        supported = [g.name for g in Game if g in mod.supported_games and g.name is not None]
        blocks.append(
            "<font color='#ffff00'>Incompatible Game!</font>\n"
            "This mod supports: " + ", ".join(supported),
        )

    if mod.description:
        blocks.append(mod.description)

    return "\n\n".join(blocks)


# Called whenever the dlc menu is refreshed, we use it to replace all the entries with our own
@hook("WillowGame.MarketplaceGFxMovie:RefreshDLC", Type.PRE, auto_enable=True)
def marketplace_refresh(obj: UObject, _2: WrappedStruct, _3: Any, _4: BoundFunction) -> type[Block]:
    obj.SetContentData([])  # Clear existing content

    obj.ClearFilters()
    obj.SetFilterFromStringAndSortNew("", "", "")

    obj.SetStoreHeader("Mods", False, base_mod.version, "SDK Mod Manager")

    drawn_mod_list[:] = get_ordered_mod_list()
    for idx, mod in enumerate(drawn_mod_list):
        item, _ = obj.CreateMarketplaceItem(unrealsdk.make_struct("MarketplaceContent"))

        item.SetString(obj.Prop_offeringId, str(idx))
        item.SetString(obj.Prop_contentTitleText, mod.name)
        item.SetString(obj.Prop_costText, "By " + mod.author)
        item.SetString(obj.Prop_descriptionText, create_description_text(mod))
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
@hook("WillowGame.MarketplaceGFxMovie:extOnOfferingChanged", Type.PRE, auto_enable=True)
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

    obj.SetTooltips(
        "[Enter] Select",
        "" if mod == base_mod else ("[Q] Unfavourite" if is_favourite(mod) else "[Q] Favourite"),
    )
    return Block


# Called on any key input in the DLC menu. We basically entirely overwrite it to add our own logic.
@hook("WillowGame.MarketplaceGFxMovie:ShopInputKey", Type.PRE, auto_enable=True)
def marketplace_input_key(
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> tuple[type[Block], bool] | None:
    try:
        key: str = DLC_MENU_CONTROLLER_TO_KB_KEY_MAP.get(args.ukey, args.ukey)
        event: EInputEvent = args.uevent

        match key, event:
            # Keep the standard handling
            case (("Escape" | "Up" | "Down" | "W" | "S"), _):
                return None

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
                item = obj.GetSelectedObject()
                if item is not None:
                    mod = drawn_mod_list[int(item.GetString(obj.Prop_offeringId))]
                    toggle_favourite(mod)
                    obj.RefreshDLC()
                return Block, True
            case "Enter", EInputEvent.IE_Released:
                # TODO: open inner menu
                return Block, True

            case _, _:
                return Block, True

    # If we let this function process normally, most inputs end up opening the steam store page
    # Make sure we always block it
    except Exception:  # noqa: BLE001
        traceback.print_exc()

    return Block, True
