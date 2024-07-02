# ruff: noqa: N802, N803, D102, D103, N999

from __future__ import annotations

import json
import traceback
from typing import TYPE_CHECKING, Any

from mods_base import hook
from unrealsdk import logging
from unrealsdk.hooks import Type

from .ModObjects import EnabledSaveType, Mods, SDKMod

if TYPE_CHECKING:
    from mods_base.settings import BasicModSettings

__all__: tuple[str, ...] = (
    "GetSettingsFilePath",
    "SaveModSettings",
    "SaveAllModSettings",
    "LoadModSettings",
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
            logging.error(f"Unable to save settings for '{mod.Name}'")
            tb = traceback.format_exc().split("\n")
            logging.dev_warning(f"    {tb[-4].strip()}")
            logging.dev_warning(f"    {tb[-3].strip()}")
            logging.dev_warning(f"    {tb[-2].strip()}")


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


@hook("WillowGame.FrontendGFxMovie:Start", Type.PRE, auto_enable=True)
def _FrontendGFxMovieStart(*_: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    for mod in _mods_to_enable_on_main_menu:
        if not mod.IsEnabled:
            mod.Enable()

    _mods_to_enable_on_main_menu.clear()
