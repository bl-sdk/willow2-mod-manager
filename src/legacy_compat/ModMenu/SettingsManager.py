# ruff: noqa: N802, N803, D102, D103, N999

from __future__ import annotations

import json
import traceback
from typing import TYPE_CHECKING

from legacy_compat import unrealsdk as old_unrealsdk

from .ModObjects import EnabledSaveType, Mods, SDKMod

if TYPE_CHECKING:
    from mods_base.settings import BasicModSettings

__all__: tuple[str, ...] = (
    "GetSettingsFilePath",
    "LoadModSettings",
    "SaveAllModSettings",
    "SaveModSettings",
)


def GetSettingsFilePath(mod: SDKMod) -> str:
    return str(mod.new_mod_obj.settings_file)


def SaveModSettings(mod: SDKMod) -> None:
    mod.new_mod_obj.save_settings()


def SaveAllModSettings() -> None:
    for mod in Mods:
        try:
            SaveModSettings(mod)
        except Exception:  # noqa: BLE001
            old_unrealsdk.Log(f"Unable to save settings for '{mod.Name}'")
            tb = traceback.format_exc().split("\n")
            old_unrealsdk.Log(f"    {tb[-4].strip()}")
            old_unrealsdk.Log(f"    {tb[-3].strip()}")
            old_unrealsdk.Log(f"    {tb[-2].strip()}")


_mods_to_enable_on_main_menu: set[SDKMod] = set()


def LoadModSettings(mod: SDKMod) -> None:
    # May be the case if we're called during __init__
    if not hasattr(mod, "new_mod_obj") or mod.new_mod_obj.settings_file is None:  # pyright: ignore[reportUnnecessaryComparison, ]
        return

    mod.new_mod_obj.load_settings()

    if mod.SaveEnabledState == EnabledSaveType.LoadOnMainMenu:
        # Little silly to load this an extra time but ehh
        settings: BasicModSettings
        try:
            with mod.new_mod_obj.settings_file.open() as file:
                settings = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        if settings.get("enabled", False):
            _mods_to_enable_on_main_menu.add(mod)


def _FrontendGFxMovieStart(
    caller: old_unrealsdk.UObject,  # noqa: ARG001
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,  # noqa: ARG001
) -> bool:
    for mod in _mods_to_enable_on_main_menu:
        if not mod.IsEnabled:
            mod.Enable()

    _mods_to_enable_on_main_menu.clear()

    return True


old_unrealsdk.RunHook(
    "WillowGame.FrontendGFxMovie.Start",
    "ModMenu.SettingsManager",
    _FrontendGFxMovieStart,
)
