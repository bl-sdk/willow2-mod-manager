# ruff: noqa: D103
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import ENGINE, Mod, get_ordered_mod_list, hook

from .favourites import is_favourite

BACK_EVENT_ID = -1


class DataProvider(ABC):
    @abstractmethod
    def populate(self, the_list: UObject) -> None:
        """
        Populates the list with the appropriate contents.

        Args:
            the_list: The WillowScrollingList to populate.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_click(self, event_id: int, the_list: UObject) -> bool:
        """
        Handles a click on one of the options menu entries.

        Args:
            event_id: The id of the menu entry which was clicked.
            the_list: The WillowScrollingList which was clicked.
        """
        raise NotImplementedError


@dataclass
class ModListDataProvider(DataProvider):
    drawn_mod_list: list[Mod] = field(default_factory=list, repr=False)

    def populate(self, the_list: UObject) -> None:  # noqa: D102
        mods = get_ordered_mod_list()
        favourite_mods = [m for m in mods if is_favourite(m)]
        non_favourite_mods = [m for m in mods if not is_favourite(m)]
        self.drawn_mod_list = favourite_mods + non_favourite_mods

        add_list_item = the_list.AddListItem
        for idx, mod in enumerate(self.drawn_mod_list):
            add_list_item(idx, mod.name, False)

    def handle_click(self, event_id: int, the_list: UObject) -> bool:  # noqa: D102
        push_mod_options(the_list, self.drawn_mod_list[event_id])
        return True


@dataclass
class ModDataProvider(DataProvider):
    mod: Mod

    def populate(self, the_list: UObject) -> None:  # noqa: D102
        the_list.AddListItem(0, self.mod.name + " options...", False)

    def handle_click(self, event_id: int, the_list: UObject) -> bool:  # noqa: D102
        _ = the_list
        _ = event_id
        return False


data_provider_stack: list[DataProvider] = []


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

    data_provider_stack.append(ModDataProvider(mod))
    the_list.PushDataProvider(provider)


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


# Called when filling in the kb/m options menu. This version shows our entries instead.
@hook("WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:Populate", auto_enable=True)
def dataprovider_kbm_populate(
    _1: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    # This is opening the standard keyboard/mouse options
    if not data_provider_stack:
        return None

    the_list: UObject = args.TheList
    data_provider_stack[-1].populate(the_list)

    # Since our modded menus start with an empty data provider stack, but logically exist under
    # other menus, add the back caption - the standard machinery won't
    if len(data_provider_stack) == 1:
        the_list.AddListItem(BACK_EVENT_ID, the_list.BackCaption, False, False)

    return Block


# Called when clicking something in the kb/m options menu - we use it for the same.
@hook(
    "WillowGame.WillowScrollingListDataProviderKeyboardMouseOptions:HandleClick",
    auto_enable=True,
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
    if event_id == BACK_EVENT_ID:
        return None

    handled = data_provider_stack[-1].handle_click(event_id, the_list)
    return Block, handled


# Called when closing any scrolling list menu. We use it to keep our stack in sync. This relies on
# the fact that once you enter an modded menu, all child menus in the stack are also always modded.
@hook("WillowGame.WillowScrollingList:HandlePopList", auto_enable=True)
def scrolling_list_handle_pop(
    obj: UObject,
    _2: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> None:
    if not data_provider_stack:
        return

    data_provider_stack.pop()
    if not data_provider_stack:
        obj.MyOwnerMovie.WPCOwner.GetFrontendMovie().HideOptionsMovie()
