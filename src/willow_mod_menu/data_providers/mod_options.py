from collections.abc import Callable, Iterator, Sequence
from dataclasses import KW_ONLY, dataclass, field

from mods_base import BaseOption, BoolOption, ButtonOption, Mod
from willow_mod_menu.description import get_mod_description

from .options import OptionsDataProvider

try:
    from ui_utils import TrainingBox
except ImportError:
    TrainingBox = None


@dataclass
class ModOptionsDataProvider(OptionsDataProvider):
    options: Sequence[BaseOption] = field(default_factory=tuple, init=False)
    _: KW_ONLY
    mod: Mod

    def __post_init__(self) -> None:
        def get_options_list() -> Iterator[BaseOption]:
            # If we have access to a training box, we'll let you click the description to get the
            # full thing, since just the option description is quite small
            on_press: Callable[[ButtonOption], None] | None = None
            if TrainingBox is not None:
                full_description = TrainingBox(self.mod.name, get_mod_description(self.mod, True))
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

        self.options = tuple(get_options_list())
