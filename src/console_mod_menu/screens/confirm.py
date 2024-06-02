from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from console_mod_menu.draw import draw

from . import AbstractScreen, pop_screen


@dataclass
class ConfirmScreen(AbstractScreen):
    msg: str
    # Return values are ignored
    on_confirm: Callable[[], Any]
    on_cancel: Callable[[], Any] = field(default=lambda: None)

    def draw(self) -> None:  # noqa: D102
        draw(self.msg)
        draw("[Y] Yes")
        draw("[N] No")

    def handle_input(self, line: str) -> bool:  # noqa: D102
        pop_screen()

        if line[0] in ("Y", "y"):
            self.on_confirm()
        else:
            self.on_cancel()

        return True
