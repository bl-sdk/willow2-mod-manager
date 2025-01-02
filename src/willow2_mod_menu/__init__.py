from mods_base import GroupedOption
from mods_base.mod_list import base_mod

__all__: list[str] = [
    "__author__",
    "__version__",
    "__version_info__",
]

__version_info__: tuple[int, int] = (3, 1)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

# Importing most of these for side effects
from . import outer_menu  # noqa: F401  # pyright: ignore[reportUnusedImport]
from .favourites import favourites_option

base_mod.components.append(base_mod.ComponentInfo("Willow2 Mod Menu", __version__))
base_mod.options.append(GroupedOption("Willow2 Mod Menu", (favourites_option,)))
