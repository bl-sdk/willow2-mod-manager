from mods_base import HiddenOption, Mod
from mods_base.mod_list import base_mod

favourites_option = HiddenOption[list[str]]("Favourites", [])


def toggle_favourite(mod: Mod) -> None:
    """
    Toggles if a mod is considered a favourite.

    Args:
        mod: The mod to toggle.
    """
    if mod == base_mod:
        return

    if mod.name in favourites_option.value:
        favourites_option.value.remove(mod.name)
    else:
        favourites_option.value.append(mod.name)

    base_mod.save_settings()


def is_favourite(mod: Mod) -> bool:
    """
    Checks if a mod is favourited.

    Args:
        mod: The mod to check.
    Returns:
        True if the mod is favourited.
    """
    if mod == base_mod:
        return True

    return mod.name in favourites_option.value
