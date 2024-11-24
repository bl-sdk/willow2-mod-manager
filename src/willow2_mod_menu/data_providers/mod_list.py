from dataclasses import dataclass, field

from unrealsdk.unreal import UObject

from mods_base import Mod, get_ordered_mod_list
from willow2_mod_menu.favourites import is_favourite
from willow2_mod_menu.options_menu import push_mod_options

from . import DataProvider


@dataclass
class ModListDataProvider(DataProvider):
    drawn_mod_list: list[Mod] = field(default_factory=list, repr=False)

    def populate(self, data_provider: UObject, the_list: UObject) -> None:  # noqa: D102
        del data_provider

        mods = get_ordered_mod_list()
        favourite_mods = [m for m in mods if is_favourite(m)]
        non_favourite_mods = [m for m in mods if not is_favourite(m)]
        self.drawn_mod_list = favourite_mods + non_favourite_mods

        for idx, mod in enumerate(self.drawn_mod_list):
            the_list.AddListItem(idx, mod.name, False)

    def populate_keybind_keys(self, data_provider: UObject) -> None:  # noqa: ARG002, D102
        return

    def handle_click(self, event_id: int, the_list: UObject) -> bool:  # noqa: D102
        push_mod_options(the_list, self.drawn_mod_list[event_id])
        return True

    def handle_spinner_change(self, event_id: int, new_choice_idx: int) -> bool:  # noqa: ARG002, D102
        return False

    def handle_slider_change(self, event_id: int, new_value: int) -> bool:  # noqa: ARG002, D102
        return False

    def handle_key_rebind(self, data_provider: UObject, key: str) -> None:  # noqa: ARG002, D102
        return

    def handle_reset_keybinds(self) -> None:  # noqa: D102
        return
