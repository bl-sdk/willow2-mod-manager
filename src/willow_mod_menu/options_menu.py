# ruff: noqa: D103
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import KW_ONLY, dataclass, field
from typing import Any

import unrealsdk
from unrealsdk import logging
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import (
    ENGINE,
    BaseOption,
    BoolOption,
    ButtonOption,
    DropdownOption,
    GroupedOption,
    KeybindOption,
    Mod,
    NestedOption,
    SliderOption,
    SpinnerOption,
    get_ordered_mod_list,
    hook,
)

from .favourites import is_favourite

BACK_EVENT_ID = -1

OPTION_EVENT_ID_OFFSET = 2000


class DataProvider(ABC):
    @abstractmethod
    def populate(self, data_provider: UObject, the_list: UObject) -> None:
        """
        Populates the list with the appropriate contents.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to populate with.
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
        Returns:
            True if the click was handled.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_spinner_change(self, event_id: int, new_choice_idx: int) -> bool:
        """
        Handles one of options menu spinners being changed.

        Args:
            event_id: The id of the spinner which was clicked.
            new_choice_idx: The index of the newly selected choice.
        Returns:
            True if the change was handled.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_slider_change(self, event_id: int, new_value: int) -> bool:
        """
        Handles one of options menu sliders being changed.

        Args:
            event_id: The id of the spinner which was clicked.
            new_value: The new value the spinner got set to.
        Returns:
            True if the change was handled.
        """
        raise NotImplementedError


@dataclass
class ModListDataProvider(DataProvider):
    drawn_mod_list: list[Mod] = field(default_factory=list, repr=False)

    def populate(self, data_provider: UObject, the_list: UObject) -> None:  # noqa: D102
        del data_provider

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

    def handle_spinner_change(self, event_id: int, new_choice_idx: int) -> bool:  # noqa: ARG002, D102
        return False

    def handle_slider_change(self, event_id: int, new_value: int) -> bool:  # noqa: ARG002, D102
        return False


@dataclass
class OptionsDataProvider(DataProvider):
    options: Sequence[BaseOption]
    drawn_options: list[BaseOption] = field(default_factory=list, repr=False)

    @staticmethod
    def create_option_description(option: BaseOption) -> str:
        """
        Creates the description text to use for the given option.

        Args:
            option: The option to create a description for.
        Returns:
            The option description (which may be an empty string).
        """
        # If we don't have a special description title, just ignore it - we have limited space
        if option.display_name == option.description_title:
            return option.description

        blocks: list[str] = []
        if option.description_title:
            blocks.append(option.description_title)
        if option.description:
            blocks.append(option.description)
        return "\n".join(blocks)

    @staticmethod
    def any_option_visible(options: Sequence[BaseOption]) -> bool:
        """
        Recursively checks if any option in a sequence is visible.

        Recurses into grouped options, but not nested ones. A grouped option which is not explictly
        hidden, but contains no visible children, does not count as visible.

        Keybind options are always treated as hidden.

        Args:
            options: The list of options to check.
        """
        return any(
            (
                isinstance(option, GroupedOption)
                and not option.is_hidden
                and OptionsDataProvider.any_option_visible(option.children)
            )
            or (not option.is_hidden and not isinstance(option, KeybindOption))
            for option in options
        )

    def add_grouped_option(
        self,
        data_provider: UObject,
        the_list: UObject,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption],
        option: GroupedOption,
        options_idx: int,
    ) -> None:
        """
        Adds a grouped option to the current scrolling list.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to populate with.
            the_list: The WillowScrollingList to add to.
            options: The full options list this group is part of.
            group_stack: The stack of currently open grouped options.
            option: The specific grouped option to add.
            options_idx: The index of the specific grouped option being added.
        """
        if not self.any_option_visible(option.children):
            return

        group_stack.append(option)

        # If the first entry of the group is another group, don't draw a title, let the
        # nested call do it, so the first title is the most nested
        # If we're empty, or a different type, draw our own header
        if len(option.children) == 0 or not isinstance(option.children[0], GroupedOption):
            the_list.AddListItem(
                event_id := (len(self.drawn_options) + OPTION_EVENT_ID_OFFSET),
                " - ".join(g.display_name for g in group_stack),
                False,
            )
            data_provider.AddDescription(event_id, self.create_option_description(option))

            self.drawn_options.append(option)

        self.add_option_list(data_provider, the_list, option.children, group_stack)

        group_stack.pop()

        # If we didn't just close the outermost group, the group above us still has extra visible
        # options, and the next one of those options is not another group, re-draw the outer
        # group's header
        if (
            group_stack
            and options_idx != len(options) - 1
            and self.any_option_visible(options[options_idx + 1 :])
            and not isinstance(options[options_idx + 1], GroupedOption)
        ):
            the_list.AddListItem(
                event_id := (len(self.drawn_options) + OPTION_EVENT_ID_OFFSET),
                " - ".join(g.display_name for g in group_stack),
                False,
            )
            data_provider.AddDescription(event_id, self.create_option_description(option))

            self.drawn_options.append(option)

    def add_option_list(  # noqa: C901 - we can't really simplify it, each case is just a single
        self,  #                         statement, the match just eats a lot
        data_provider: UObject,
        the_list: UObject,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption],
    ) -> None:
        """
        Adds a list of options to the current scrolling list.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to populate with.
            the_list: The WillowScrollingList to add to.
            options: The list of options to add.
            group_stack: The stack of currently open grouped options. Should start out empty.
        """
        for options_idx, option in enumerate(options):
            if option.is_hidden:
                continue

            # Grouped options are a little more complex, it handles this manually
            if not isinstance(option, GroupedOption):
                self.drawn_options.append(option)

            event_id = len(self.drawn_options) - 1 + OPTION_EVENT_ID_OFFSET

            # If we're in any group, we indent the names slightly to distingish them from the
            # headers
            option_name = ("  " if group_stack else "") + option.display_name

            match option:
                case ButtonOption() | NestedOption():
                    the_list.AddListItem(event_id, option_name, False)

                case BoolOption():
                    the_list.AddSpinnerListItem(
                        event_id,
                        option_name,
                        False,
                        int(option.value),
                        [option.false_text or "Off", option.true_text or "On"],
                    )

                case DropdownOption() | SpinnerOption():
                    the_list.AddSpinnerListItem(
                        event_id,
                        option_name,
                        False,
                        option.choices.index(option.value),
                        option.choices,
                    )

                case SliderOption():
                    the_list.AddSliderListItem(
                        event_id,
                        option_name,
                        False,
                        option.value,
                        option.min_value,
                        option.max_value,
                        option.step,
                    )

                case GroupedOption() if option in group_stack:
                    logging.dev_warning(f"Found recursive options group, not drawing: {option}")
                case GroupedOption():
                    self.add_grouped_option(
                        data_provider,
                        the_list,
                        options,
                        group_stack,
                        option,
                        options_idx,
                    )

                case KeybindOption():
                    pass
                case _:
                    logging.dev_warning(f"Encountered unknown option type {type(option)}")

            if not isinstance(option, GroupedOption):
                data_provider.AddDescription(event_id, self.create_option_description(option))

    def populate(self, data_provider: UObject, the_list: UObject) -> None:  # noqa: D102
        self.add_option_list(data_provider, the_list, self.options, [])

    def handle_click(self, event_id: int, the_list: UObject) -> bool:  # noqa: D102
        match option := self.drawn_options[event_id - OPTION_EVENT_ID_OFFSET]:
            case ButtonOption():
                if option.on_press is not None:
                    option.on_press(option)
                return True
            case GroupedOption():
                return True
            case NestedOption():
                push_options(the_list, option.display_name, option.children)
                return True
            case _:
                logging.dev_warning(
                    f"Encountered unexpected option type {type(option)} in click handler",
                )
                return False

    def handle_spinner_change(self, event_id: int, new_choice_idx: int) -> bool:  # noqa: D102
        match option := self.drawn_options[event_id - OPTION_EVENT_ID_OFFSET]:
            case BoolOption():
                option.value = bool(new_choice_idx)
                return True

            case DropdownOption() | SpinnerOption():
                option.value = option.choices[new_choice_idx]
                return True

            case _:
                logging.dev_warning(
                    f"Encountered unexpected option type {type(option)} in spinner change handler",
                )
                return False

    def handle_slider_change(self, event_id: int, new_value: int) -> bool:  # noqa: D102
        match option := self.drawn_options[event_id - OPTION_EVENT_ID_OFFSET]:
            case SliderOption():
                # Unfortuantely, all values we get back from the hook are integers - so checking
                # `option.is_integer` is redundant
                option.value = int(new_value)
                return True

            case _:
                logging.dev_warning(
                    f"Encountered unexpected option type {type(option)} in slider change handler",
                )
                return False


@dataclass
class ModOptionsDataProvider(OptionsDataProvider):
    options: Sequence[BaseOption] = field(default_factory=tuple, init=False)
    _: KW_ONLY
    mod: Mod

    def __post_init__(self) -> None:
        def get_options_list() -> Iterator[BaseOption]:
            yield ButtonOption("Description", description=self.mod.description)

            if not self.mod.enabling_locked:
                yield BoolOption(
                    "Enabled",
                    self.mod.is_enabled,
                    on_change=lambda _, now_enabled: (
                        self.mod.enable() if now_enabled else self.mod.disable()
                    ),
                )

            yield from self.mod.iter_display_options()

        self.options = tuple(get_options_list())


data_provider_stack: list[DataProvider] = []


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
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    # This is opening the standard keyboard/mouse options
    if not data_provider_stack:
        return None

    the_list: UObject = args.TheList
    data_provider_stack[-1].populate(obj, the_list)

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


# Called when changing a spinner in *any* options menu - there isn't a kb/m specific override of
# this. We use it to track our events for the same.
@hook(
    "WillowGame.WillowScrollingListDataProviderOptionsBase:HandleSpinnerChange",
    auto_enable=True,
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
    auto_enable=True,
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
    data_provider_stack[-1].handle_spinner_change(event_id, new_value)

    # Same as above, unconditionally return handled
    return Block, True


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

    provider = data_provider_stack.pop()

    # On leaving a mod options screen, also make sure to save it
    if isinstance(provider, ModOptionsDataProvider):
        provider.mod.save_settings()

    if not data_provider_stack:
        obj.MyOwnerMovie.WPCOwner.GetFrontendMovie().HideOptionsMovie()
