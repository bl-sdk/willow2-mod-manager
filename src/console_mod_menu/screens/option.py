from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field

from console_mod_menu.draw import draw
from console_mod_menu.option_formatting import draw_option_header
from mods_base import (
    JSON,
    BaseOption,
    BoolOption,
    ButtonOption,
    DropdownOption,
    Mod,
    SliderOption,
    SpinnerOption,
    ValueOption,
)

from . import AbstractScreen, draw_standard_commands, handle_standard_command_input


@dataclass
class OptionScreen[T: BaseOption, J: JSON](AbstractScreen):
    name: str = field(init=False)
    mod: Mod
    option: T

    def __post_init__(self) -> None:
        self.name = self.option.display_name

    def draw(self) -> None:  # noqa: D102
        draw_option_header(self.option)
        self.draw_option()

    @abstractmethod
    def draw_option(self) -> None:
        """Draws anything needed for the specific option."""
        raise NotImplementedError

    def update_value(self, new_value: J) -> None:
        """
        Updates an option's value, running the callback if needed.

        Args:
            new_value: The option's new value.
        """
        assert isinstance(self.option, ValueOption)
        option: ValueOption[J] = self.option  # type: ignore
        option.value = new_value
        self.mod.save_settings()


@dataclass
class ButtonOptionScreen(OptionScreen[ButtonOption, None]):
    def draw_option(self) -> None:  # noqa: D102
        if self.option.on_press is not None:
            draw("[1] Press")

        draw_standard_commands()

    def handle_input(self, line: str) -> bool:  # noqa: D102
        if handle_standard_command_input(line):
            return True

        if line == "1" and self.option.on_press is not None:
            self.option.on_press(self.option)
            return True

        return False


@dataclass
class BoolOptionScreen(OptionScreen[BoolOption, bool]):
    def draw_option(self) -> None:  # noqa: D102
        draw(f"[1] {self.option.false_text or 'Off'}")
        draw(f"[2] {self.option.true_text or 'On'}")

        draw_standard_commands()

    def handle_input(self, line: str) -> bool:  # noqa: D102
        if handle_standard_command_input(line):
            return True

        if line == "1":
            self.update_value(False)
            return True
        if line == "2":
            self.update_value(True)
            return True

        return False


@dataclass
class ChoiceOptionScreen(OptionScreen[DropdownOption | SpinnerOption, str]):
    def draw_option(self) -> None:  # noqa: D102
        for idx, val in enumerate(self.option.choices):
            draw(f"[{idx}] {val}")

        draw_standard_commands()

    def handle_input(self, line: str) -> bool:  # noqa: D102
        if handle_standard_command_input(line):
            return True

        value: str
        try:
            value = self.option.choices[int(line)]
        except (ValueError, IndexError):
            return False

        self.update_value(value)
        return True


@dataclass
class SliderOptionScreen(OptionScreen[SliderOption, float]):
    def draw_option(self) -> None:  # noqa: D102
        draw(f"Enter the new value [{self.option.min_value}-{self.option.max_value}]")

        draw_standard_commands()

    def handle_input(self, line: str) -> bool:  # noqa: D102
        if handle_standard_command_input(line):
            return True

        value: float
        try:
            value = float(line)
        except ValueError:
            return False
        if self.option.is_integer:
            value = round(value)

        self.update_value(value)
        return True
