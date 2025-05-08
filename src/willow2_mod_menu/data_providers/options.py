from collections.abc import Sequence
from dataclasses import dataclass, field

from unrealsdk import logging
from unrealsdk.unreal import UObject

from mods_base import (
    BaseOption,
    BoolOption,
    ButtonOption,
    DropdownOption,
    GroupedOption,
    KeybindOption,
    NestedOption,
    SliderOption,
    SpinnerOption,
)
from willow2_mod_menu.options_menu import push_options

from . import OPTION_EVENT_ID_OFFSET, DataProvider


@dataclass
class OptionsDataProvider(DataProvider):
    options: Sequence[BaseOption]
    drawn_options: list[BaseOption] = field(default_factory=list[BaseOption], repr=False)

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

        Recurses into grouped options, but not nested ones. A grouped option which is not explicitly
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
            or (not isinstance(option, KeybindOption) and not option.is_hidden)
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

            # If we're in any group, we indent the names slightly to distinguish them from the
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
                    if not option.is_integer or any(
                        round(x) != x
                        for x in (option.value, option.min_value, option.max_value, option.step)
                    ):
                        logging.dev_warning(
                            f"'{option.identifier}' is a non-integer slider, which willow2-mod-menu"
                            " does not support due to engine limitations",
                        )
                    if any(
                        (x % option.step) != 0
                        for x in (option.value, option.min_value, option.max_value)
                    ):
                        logging.dev_warning(
                            f"'{option.identifier}' uses a slider step which does not evenly divide"
                            " its values, which have have unexpected behaviour in willow2-mod-menu,"
                            " due to engine limitations",
                        )

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

    def populate_keybind_keys(self, data_provider: UObject) -> None:  # noqa: ARG002, D102
        return

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
                # Unfortunately, all values we get back from the hook are integers - so checking
                # `option.is_integer` is redundant
                option.value = int(new_value)
                return True

            case _:
                logging.dev_warning(
                    f"Encountered unexpected option type {type(option)} in slider change handler",
                )
                return False

    def handle_key_rebind(self, data_provider: UObject, key: str) -> None:  # noqa: ARG002, D102
        return

    def handle_reset_keybinds(self) -> None:  # noqa: D102
        return
