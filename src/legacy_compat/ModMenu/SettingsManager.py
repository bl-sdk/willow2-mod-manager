from __future__ import annotations

import unrealsdk
import inspect
import json
import traceback
from os import path
from typing import Any, Dict, Sequence, Set, Tuple

from . import DeprecationHelper as dh
from . import KeybindManager, ModObjects, Options

__all__: Tuple[str, ...] = (
    "GetSettingsFilePath",
    "SaveModSettings",
    "SaveAllModSettings",
    "LoadModSettings",
)


_OPTIONS_CATEGORY_NAME = "Options"
_KEYBINDS_CATEGORY_NAME = "Keybinds"
_ENABLED_CATEGORY_NAME = "AutoEnable"
_SETTINGS_FILE_NAME = "settings.json"

_mods_to_enable_on_main_menu: Set[ModObjects.SDKMod] = set()


def GetSettingsFilePath(mod: ModObjects.SDKMod) -> str:
    """
    Gets the path of a mod's settings file.

    Args:
        mod: The instance of the mod whose settings file path should be retrived.
    Returns:
        The path to the file, which is in the same folder as the file defining the mod class.
    """
    return path.join(path.dirname(inspect.getfile(mod.__class__)), _SETTINGS_FILE_NAME)


def SaveModSettings(mod: ModObjects.SDKMod) -> None:
    """
    Saves the options, keybinds, and enabled state of a mod, where applicable.

    Args:
        mod: The instance of the mod whose settings should be saved.
    """
    mod_settings: Dict[str, Any] = {}

    def create_options_dict(options: Sequence[Options.Base]) -> Dict[str, Any]:
        settings = {}
        for option in options:
            if isinstance(option, Options.Value):
                settings[option.Caption] = option.CurrentValue
            elif isinstance(option, Options.Nested):
                settings[option.Caption] = create_options_dict(option.Children)
        return settings

    options_dict = create_options_dict(mod.Options)

    if len(options_dict) > 0:
        mod_settings[_OPTIONS_CATEGORY_NAME] = options_dict

    keybinds_dict = {}
    for input in mod.Keybinds:
        if isinstance(input, KeybindManager.Keybind):
            if not input.IsRebindable:
                continue
            keybinds_dict[input.Name] = input.Key
        else:
            dh.PrintWarning(KeybindManager.Keybind._list_deprecation_warning)
            keybinds_dict[input[0]] = input[1]

    if len(keybinds_dict) > 0:
        mod_settings[_KEYBINDS_CATEGORY_NAME] = keybinds_dict

    if mod.SaveEnabledState != ModObjects.EnabledSaveType.NotSaved:
        mod_settings[_ENABLED_CATEGORY_NAME] = mod.IsEnabled

    if len(mod_settings.keys()) > 0:
        with open(GetSettingsFilePath(mod), "w") as file:
            json.dump(mod_settings, file, indent=4)


def SaveAllModSettings() -> None:
    """ Saves the options, keybinds, and enabled state of all loaded mods, where applicable. """
    for mod in ModObjects.Mods:
        try:
            SaveModSettings(mod)
        except Exception:
            unrealsdk.Log(f"Unable to save settings for '{mod.Name}'")
            tb = traceback.format_exc().split('\n')
            unrealsdk.Log(f"    {tb[-4].strip()}")
            unrealsdk.Log(f"    {tb[-3].strip()}")
            unrealsdk.Log(f"    {tb[-2].strip()}")


def LoadModSettings(mod: ModObjects.SDKMod) -> None:
    """
    Loads the options, keybinds, and enabled state of a mod back from disk.

    Args:
        mod: The instance of the mod to load settings onto.
    """
    settings: Dict[str, Any]
    try:
        with open(GetSettingsFilePath(mod)) as file:
            settings = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    def load_options_dict(options: Sequence[Options.Base], settings: Dict[str, Any]) -> None:
        for option in options:
            if option.Caption not in settings:
                continue

            value = settings[option.Caption]

            if isinstance(option, Options.Boolean):
                if isinstance(value, str):
                    if value in option.Choices:
                        option.CurrentValue = bool(option.Choices.index(value))
                    elif value.lower() == "true":
                        option.CurrentValue = True
                    elif value.lower() == "false":
                        option.CurrentValue = False
                else:
                    option.CurrentValue = bool(value)
            elif isinstance(option, Options.Spinner):
                if value in option.Choices:
                    option.CurrentValue = str(value)
                else:
                    option.CurrentValue = option.StartingValue
            elif isinstance(option, Options.Slider):
                option.CurrentValue = max(option.MinValue, min(option.MaxValue, int(value)))
            elif isinstance(option, Options.Hidden):
                option.CurrentValue = value

            elif isinstance(option, Options.Nested):
                load_options_dict(option.Children, value)

    load_options_dict(mod.Options, settings.get(_OPTIONS_CATEGORY_NAME, {}))

    saved_keybinds = settings.get(_KEYBINDS_CATEGORY_NAME, {})
    for input in mod.Keybinds:
        if isinstance(input, KeybindManager.Keybind):
            if input.Name in saved_keybinds:
                input.Key = saved_keybinds[input.Name]
        else:
            dh.PrintWarning(KeybindManager.Keybind._list_deprecation_warning)
            if input[0] in saved_keybinds:
                input[1] = saved_keybinds[input[0]]

    if settings.get(_ENABLED_CATEGORY_NAME, False):
        if mod.SaveEnabledState == ModObjects.EnabledSaveType.LoadWithSettings:
            if not mod.IsEnabled:
                mod.SettingsInputPressed("Enable")
        elif mod.SaveEnabledState == ModObjects.EnabledSaveType.LoadOnMainMenu:
            _mods_to_enable_on_main_menu.add(mod)


def _FrontendGFxMovieStart(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
    """
    This function is called upon reaching the main menu, after hotfix objects already exist and all
     the main packages are loaded. We use it to enable all `LoadOnMainMenu` mods.
    """
    for mod in _mods_to_enable_on_main_menu:
        if not mod.IsEnabled:
            mod.SettingsInputPressed("Enable")

    _mods_to_enable_on_main_menu.clear()

    return True


unrealsdk.RunHook("WillowGame.FrontendGFxMovie.Start", "ModMenu.SettingsManager", _FrontendGFxMovieStart)
