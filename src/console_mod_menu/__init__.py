import argparse

from mods_base import command
from mods_base.mod_list import base_mod

from .screens import start_interactive_menu

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
)

__version_info__: tuple[int, int] = (1, 1)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


@command("mods", description="Opens the console mod menu.")
def mods_command(_: argparse.Namespace) -> None:
    start_interactive_menu()


mods_command.add_argument("-v", "--version", action="version", version=__version__)

mods_command.enable()
print("Console Mod Menu loaded. Type 'mods' to get started.")


base_mod.components.append(base_mod.ComponentInfo("Console Mod Menu", __version__))
