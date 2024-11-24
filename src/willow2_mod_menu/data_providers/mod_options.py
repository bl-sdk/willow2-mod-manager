from collections.abc import Callable, Iterator, Sequence
from dataclasses import KW_ONLY, dataclass, field

from unrealsdk.unreal import UObject, WrappedStruct

from mods_base import (
    BaseOption,
    BoolOption,
    ButtonOption,
    GroupedOption,
    KeybindOption,
    Mod,
    NestedOption,
)
from willow2_mod_menu.description import get_mod_description

from . import (
    KB_TAG_HEADER,
    KB_TAG_KEYBIND,
    KB_TAG_UNREBINDABLE,
    KEYBINDS_EVENT_ID,
    RESET_KEYBINDS_EVENT_ID,
)
from .options import OptionsDataProvider

try:
    from ui_utils import TrainingBox
except ImportError:
    TrainingBox = None

KEYBINDS_NAME = "$WillowMenu.MenuOptionDisplayNames.KeyBinds"
KEYBINDS_DESC = "$WillowMenu.MenuOptionDisplayNames.KeyBindsDesc"
RESET_KEYBINDS_NAME = "$WillowMenu.MenuOptionDisplayNames.ResetKeyBinds"
RESET_KEYBINDS_DESC = "$WillowMenu.MenuOptionDisplayNames.ResetKeyBindsDesc"

DUMMY_ACTION = "DUMMY"


@dataclass
class ModOptionsDataProvider(OptionsDataProvider):
    options: Sequence[BaseOption] = field(default_factory=tuple, init=False)
    _: KW_ONLY
    mod: Mod

    drawn_keybinds: dict[int, KeybindOption] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.options = tuple(self.gen_options_list())

    def gen_options_list(self) -> Iterator[BaseOption]:
        """
        Generates the outermost set of options to display.

        Yields:
            The options to display.
        """
        # If we have access to a training box, we'll let you click the description to get the
        # full thing, since just the option description is quite small
        on_press: Callable[[ButtonOption], None] | None = None
        if TrainingBox is not None:
            full_description = TrainingBox(
                title=self.mod.name,
                message=get_mod_description(self.mod, True),
            )
            on_press = lambda _: full_description.show()  # noqa: E731

        yield ButtonOption(
            "Description",
            description=self.mod.description,
            on_press=on_press,
        )

        if not self.mod.enabling_locked:
            yield BoolOption(
                "Enabled",
                self.mod.is_enabled,
                on_change=lambda _, now_enabled: (
                    self.mod.enable() if now_enabled else self.mod.disable()
                ),
            )

        yield from self.mod.iter_display_options()

    @staticmethod
    def any_keybind_visible(options: Sequence[BaseOption]) -> bool:
        """
        Recursively checks if any keybind option in a sequence is visible.

        Recurses into grouped and nested options. A grouped or nested option which is not explicitly
        hidden, but contains no visible children, does not count as visible.

        Args:
            options: The list of options to check.
        """
        return any(
            (
                isinstance(option, GroupedOption | NestedOption)
                and not option.is_hidden
                and ModOptionsDataProvider.any_keybind_visible(option.children)
            )
            or (isinstance(option, KeybindOption) and not option.is_hidden)
            for option in options
        )

    def add_keybinds_list(
        self,
        data_provider: UObject,
        options: Sequence[BaseOption],
        group_stack: list[GroupedOption | NestedOption],
    ) -> None:
        """
        Adds a list of keybinds to the current menu.

        Args:
            data_provider: The WillowScrollingListDataProviderOptionsBase to add to.
            options: The list of options containing the keybinds to add.
            group_stack: The stack of currently open grouped options. Should start out empty.
        """
        nest_idx = len(group_stack)

        for options_idx, option in enumerate(options):
            if option.is_hidden:
                continue

            tag_this_idx = f"{nest_idx}:{options_idx}"

            match option:
                case KeybindOption():
                    tag_prefix = KB_TAG_KEYBIND if option.is_rebindable else KB_TAG_UNREBINDABLE
                    tag = f"{tag_prefix}:{tag_this_idx}"
                    caption = ("  " if group_stack else "") + option.display_name

                    keybind_idx = data_provider.AddKeyBindEntry(tag, DUMMY_ACTION, caption)
                    self.drawn_keybinds[keybind_idx] = option

                # This is the same sort of logic as grouped options in add_options_list
                case GroupedOption() | NestedOption() if self.any_keybind_visible(option.children):
                    group_stack.append(option)

                    if len(option.children) == 0 or not (
                        isinstance(option.children[0], GroupedOption | NestedOption)
                    ):
                        tag = f"{KB_TAG_HEADER}:{tag_this_idx}:pre_group"
                        caption = " - ".join(g.display_name for g in group_stack)
                        data_provider.AddKeyBindEntry(tag, DUMMY_ACTION, caption)

                    self.add_keybinds_list(
                        data_provider,
                        option.children,
                        group_stack,
                    )

                    group_stack.pop()

                    if (
                        group_stack
                        and options_idx != len(options) - 1
                        and self.any_keybind_visible(options[options_idx + 1 :])
                        and not isinstance(options[options_idx + 1], GroupedOption | NestedOption)
                    ):
                        tag = f"{KB_TAG_HEADER}:{tag_this_idx}:post_group"
                        caption = " - ".join(g.display_name for g in group_stack)
                        data_provider.AddKeyBindEntry(tag, DUMMY_ACTION, caption)

                case _:
                    pass

    def populate(self, data_provider: UObject, the_list: UObject) -> None:  # noqa: D102
        super().populate(data_provider, the_list)

        if not self.any_keybind_visible(self.options):
            return

        the_list.AddListItem(KEYBINDS_EVENT_ID, KEYBINDS_NAME, False)
        data_provider.AddDescription(KEYBINDS_EVENT_ID, KEYBINDS_DESC)

        the_list.AddListItem(RESET_KEYBINDS_EVENT_ID, RESET_KEYBINDS_NAME, False)
        data_provider.AddDescription(RESET_KEYBINDS_EVENT_ID, RESET_KEYBINDS_DESC)

        self.add_keybinds_list(data_provider, self.options, [])

    @staticmethod
    def localize_keybind_key(option: KeybindOption, data_provider: UObject) -> str:
        """
        Gets the localized display string to use for the given keybind's key.

        Args:
            option: The keybind to get the string for.
            data_provider: The data provider to use for localization.
        Returns:
            The localized display string.
        """
        localized_key: str
        if option.value is None:
            localized_key = ""
        else:
            localized_key = data_provider.GetLocalizedKeyName(option.value)
            # If we failed to localize, just use the raw key name
            if localized_key.startswith("?INT?"):
                localized_key = option.value

        if not option.is_rebindable:
            localized_key = f"[ {localized_key} ]"

        return localized_key

    def populate_keybind_keys(self, data_provider: UObject) -> None:  # noqa: D102
        controller_mapping_clip = data_provider.ControllerMappingClip
        controller_mapping_clip.EmptyKeyData()

        for idx, key in enumerate(data_provider.KeyBinds):
            if idx not in self.drawn_keybinds:
                # Must be a group header, display without a key
                key.Object = controller_mapping_clip.AddKeyData(key.Tag, key.Caption, "")
                continue

            localized_key = self.localize_keybind_key(self.drawn_keybinds[idx], data_provider)
            key.Object = controller_mapping_clip.AddKeyData(key.Tag, key.Caption, localized_key)

    def handle_key_rebind(self, data_provider: UObject, key: str) -> None:  # noqa: D102
        idx: int = data_provider.CurrentKeyBindSelection

        key_entry: WrappedStruct
        option: KeybindOption
        try:
            key_entry = data_provider.KeyBinds[idx]
            option = self.drawn_keybinds[idx]
        except (IndexError, KeyError):
            return

        option.value = None if key == option.value else key

        key_entry.Object.SetString("value", self.localize_keybind_key(option, data_provider))
        data_provider.ControllerMappingClip.InvalidateKeyData()

    def handle_reset_keybinds(self) -> None:  # noqa: D102
        for keybind in self.drawn_keybinds.values():
            if not keybind.is_rebindable:
                continue
            keybind.value = keybind.default_value
