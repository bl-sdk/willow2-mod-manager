from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from unrealsdk import logging

from .command import AbstractCommand
from .hook import HookProtocol
from .keybinds import KeybindType
from .options import BaseOption, GroupedOption, KeybindOption, NestedOption
from .settings import default_load_mod_settings, default_save_mod_settings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence


class Game(Flag):
    BL2 = auto()
    TPS = auto()
    AoDK = auto()
    BL3 = auto()
    WL = auto()

    Willow2 = BL2 | TPS | AoDK
    Oak = BL3 | WL

    @staticmethod
    @cache
    def get_current() -> Literal[Game.BL2, Game.TPS, Game.AoDK, Game.BL3, Game.WL]:
        """Gets the current game."""

        # As a bit of safety, we can use the architecture to limit which games are allowed
        is_64bits = sys.maxsize > 2**32

        lower_exe_names: dict[str, Literal[Game.BL2, Game.TPS, Game.AoDK, Game.BL3, Game.WL]]
        default_game: Literal[Game.BL2, Game.TPS, Game.AoDK, Game.BL3, Game.WL]
        if is_64bits:
            lower_exe_names = {
                "borderlands3.exe": Game.BL3,
                "wonderlands.exe": Game.WL,
            }
            default_game = Game.BL3
        else:
            lower_exe_names = {
                "borderlands2.exe": Game.BL2,
                "borderlandspresequel.exe": Game.TPS,
                "tinytina.exe": Game.AoDK,
            }
            default_game = Game.BL2

        exe = Path(sys.executable).name
        exe_lower = exe.lower()

        if exe_lower not in lower_exe_names:
            # We've occasionally seen the executable corrupt in the old willow sdk
            # Instead of throwing, we'll still try return something sane, to keep stuff working
            logging.error(f"Unknown executable name '{exe}'! Assuming {default_game.name}.")
            return default_game

        return lower_exe_names[exe_lower]

    @staticmethod
    @cache
    def get_tree() -> Literal[Game.Willow2, Game.Oak]:
        """
        Gets the "tree" the game we're currently running belongs to.

        Gearbox code names games using tree names. For the games based on same engine, like BL2/TPS,
        they of course reuse the same code name a lot (since they don't touch the base engine). We
        use these to categorise engine versions, where mods are likely to be cross compatible.

        Returns:
            The current game's tree.
        """
        match Game.get_current():
            case Game.BL2 | Game.TPS | Game.AoDK:
                return Game.Willow2
            case Game.BL3 | Game.WL:
                return Game.Oak


class ModType(Enum):
    Standard = auto()
    Library = auto()


class CoopSupport(Enum):
    Unknown = auto()
    Incompatible = auto()
    RequiresAllPlayers = auto()
    ClientSide = auto()


@dataclass
class Mod:
    """
    A mod instance to display in the mods menu.

    The various display strings may contain HTML tags + entities. All mod menus are expected to
    handle them, parsing or striping as appropriate. Other forms of markup are allowed, but may be
    handled incorrectly by some mod menus.

    Attributes - Metadata:
        name: The mod's name.
        author: The mod's author(s).
        description: A short description of the mod.
        version: A string holding the mod's version. This is purely a display value, the module
                 level attributes should be used for version checking.
        mod_type: What type of mod this is. This influences ordering in the mod list.
        supported_games: The games this mod supports. When loaded in an unsupported game, a warning
                         will be displayed and the mod will be blocked from enabling.
        coop_support: How well the mod supports coop, if known. This is purely a display value.
        settings_file: The file to save settings to. If None (the default), won't save settings.

    Attributes - Functionality:
        keybinds: The mod's keybinds. If not given, searches for them in instance variables.
        options: The mod's options. If not given, searches for them in instance variables.
        hooks: The mod's hooks. If not given, searches for them in instance variables.
        commands: The mod's commands. If not given, searches for them in instance variables.

    Attributes - Enabling:
        enabling_locked: If true, the mod cannot be enabled or disabled, it's locked in it's current
                         state. Set automatically, not available in constructor.
        is_enabled: True if the mod is currently considered enabled. Not available in constructor.
        auto_enable: True if to enable the mod on launch if it was also enabled last time.
        on_enable: A no-arg callback to run on mod enable. Useful when constructing via dataclass.
        on_disable: A no-arg callback to run on mod disable. Useful when constructing via dataclass.
    """

    name: str
    author: str = "Unknown Author"
    description: str = ""
    version: str = "Unknown Version"
    mod_type: ModType = ModType.Standard
    supported_games: Game = field(default=Game.get_tree())
    coop_support: CoopSupport = CoopSupport.Unknown
    settings_file: Path | None = None

    # Set the default to None so we can detect when these aren't provided
    # Don't type them as possibly None though, since we're going to fix it immediately in the
    # constructor, and it'd force you to do None checks whenever you're accessing them
    keybinds: Sequence[KeybindType] = field(default=None)  # type: ignore
    options: Sequence[BaseOption] = field(default=None)  # type: ignore
    hooks: Sequence[HookProtocol] = field(default=None)  # type: ignore
    commands: Sequence[AbstractCommand] = field(default=None)  # type: ignore

    enabling_locked: bool = field(init=False)
    is_enabled: bool = field(default=False, init=False)
    auto_enable: bool = True
    on_enable: Callable[[], None] | None = None
    on_disable: Callable[[], None] | None = None

    def __post_init__(self) -> None:  # noqa: C901 - difficult to split up
        need_to_search_instance_vars = False

        new_keybinds: list[KeybindType] = []
        if find_keybinds := self.keybinds is None:  # type: ignore
            self.keybinds = new_keybinds
            need_to_search_instance_vars = True

        new_options: list[BaseOption] = []
        if find_options := self.options is None:  # type: ignore
            self.options = new_options
            need_to_search_instance_vars = True

        new_hooks: list[HookProtocol] = []
        if find_hooks := self.hooks is None:  # type: ignore
            self.hooks = new_hooks
            need_to_search_instance_vars = True

        new_commands: list[AbstractCommand] = []
        if find_commands := self.commands is None:  # type: ignore
            self.commands = new_commands
            need_to_search_instance_vars = True

        if need_to_search_instance_vars:
            for _, value in inspect.getmembers(self):
                match value:
                    case KeybindType() if find_keybinds:
                        new_keybinds.append(value)
                    case GroupedOption() | NestedOption() if find_options:
                        logging.dev_warning(
                            f"{self.name}: {type(value).__name__} instances must be explicitly"
                            f" specified in the options list!",
                        )
                    case BaseOption() if find_options:
                        new_options.append(value)
                    case HookProtocol() if find_hooks:
                        new_hooks.append(value.bind(self))
                    case AbstractCommand() if find_commands:
                        new_commands.append(value)
                    case _:
                        pass

        for option in self.options:
            option.mod = self

        self.enabling_locked = Game.get_current() not in self.supported_games

    def enable(self) -> None:
        """Called to enable the mod."""
        if self.enabling_locked:
            return
        if self.is_enabled:
            return

        self.is_enabled = True

        for keybind in self.keybinds:
            keybind.enable()
        for hook in self.hooks:
            hook.enable()
        for command in self.commands:
            command.enable()

        if self.on_enable is not None:
            self.on_enable()

        if self.auto_enable:
            self.save_settings()

    def disable(self, dont_update_setting: bool = False) -> None:
        """
        Called to disable the mod.

        Args:
            dont_update_setting: If true, prevents updating the enabled flag in the settings file.
                                 Should be set for automated disables, and clear for manual ones.
        """
        if self.enabling_locked:
            return
        if not self.is_enabled:
            return

        self.is_enabled = False

        for keybind in self.keybinds:
            keybind.disable()
        for hook in self.hooks:
            hook.disable()
        for command in self.commands:
            command.disable()

        if self.on_disable is not None:
            self.on_disable()

        if self.auto_enable and not dont_update_setting:
            self.save_settings()

    def load_settings(self) -> None:
        """
        Loads data for this mod from it's settings file - including auto enabling if needed.

        This is called during `register_mod`, you generally won't need to call it yourself.
        """
        default_load_mod_settings(self)

    def save_settings(self) -> None:
        """Saves the current state of the mod to it's settings file."""
        default_save_mod_settings(self)

    def iter_display_options(self) -> Iterator[BaseOption]:
        """
        Iterates through the options to display in the options menu.

        This may yield options not in the options list, to customize how the menu is displayed.

        Yields:
            Options, in the order they should be displayed.
        """
        if any(not opt.is_hidden for opt in self.options):
            yield GroupedOption("Options", self.options)

        if any(not kb.is_hidden for kb in self.keybinds):
            yield GroupedOption(
                "Keybinds",
                [KeybindOption.from_keybind(bind) for bind in self.keybinds],
            )

    def get_status(self) -> str:
        """Gets the current status of this mod. Should be a single line."""
        if Game.get_current() not in self.supported_games:
            return "<font color='#ffff00'>Incompatible</font>"
        if self.is_enabled:
            return "<font color='#00ff00'>Enabled</font>"
        return "<font color='#ff0000'>Disabled</font>"


@dataclass
class Library(Mod):
    """Helper subclass for libraries, which are always enabled."""

    mod_type: Literal[ModType.Library] = ModType.Library  # pyright: ignore[reportIncompatibleVariableOverride]

    # Don't auto enable, since we're always enabled
    auto_enable: Literal[False] = False  # pyright: ignore[reportIncompatibleVariableOverride]

    def __post_init__(self) -> None:
        super().__post_init__()

        # Enable if not already locked due to an incompatible game
        if not self.enabling_locked:
            self.enable()
        # And then lock
        self.enabling_locked = True

    def get_status(self) -> str:
        """Gets the current status of this mod."""
        if Game.get_current() not in self.supported_games:
            return "<font color='#ffff00'>Incompatible</font>"
        return "<font color='#00ff00'>Loaded</font>"
