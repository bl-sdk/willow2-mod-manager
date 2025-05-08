import json
from json import JSONDecodeError
from typing import Any

from unrealsdk import logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedArray, WrappedStruct

import save_options.options
from mods_base import JSON, get_pc, hook
from save_options.options import set_option_to_default, trigger_save
from save_options.registration import (
    ModSaveOptions,
    load_callbacks,
    registered_mods,
    registered_save_options,
    save_callbacks,
)

# Value doesn't matter, just needs to be consistent and higher than any real DLC package ID
_PACKAGE_ID: int = 99


def _extract_save_data(
    lockout_list: WrappedArray[WrappedStruct],
) -> dict[str, dict[str, JSON]]:
    """
    Extracts custom save data from an UnloadableDlcLockoutList.

    This function searches through the list for an entry matching the global `_PACKAGE_ID`.
    If found, it attempts to parse the `LockoutDefName` field as a JSON string into a dictionary.
    Invalid or malformed JSON will result in an empty dictionary and an error being logged.
    All entries matching the `_PACKAGE_ID` are removed in place.

    Args:
        lockout_list: List of LockoutData structs from the character save file.
    Returns:
        A dictionary of extracted save data (empty if not found or invalid).
    """

    matching_lockout_data = next(
        (lockout_data for lockout_data in lockout_list if lockout_data.DlcPackageId == _PACKAGE_ID),
        None,
    )
    if not matching_lockout_data:
        return {}

    extracted_save_data: dict[str, dict[str, JSON]] = {}
    if matching_lockout_data.LockoutDefName:
        try:
            extracted_save_data = json.loads(matching_lockout_data.LockoutDefName)
        except JSONDecodeError:
            # Invalid data, just clear the contents
            logging.error("Error extracting custom save data from save file, invalid JSON found.")
            extracted_save_data = {}
        # Pylance saying this instance check unnecessary, but json.loads can return valid non-dict
        # objects.
        if not isinstance(extracted_save_data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            logging.error(
                f"Could not load dict object from custom save string:"
                f" {matching_lockout_data.LockoutDefName}",
            )
            extracted_save_data = {}

    # Remove all our entries from the list
    # This is done in a bit of a weird, unpythonic way, to be extra safe with regards to the
    # structs. Structs are reference types, so removing one shifts all other references.
    i = 0
    while i < len(lockout_list):
        if lockout_list[i].DlcPackageId == _PACKAGE_ID:
            del lockout_list[i]
            continue
        i += 1

    return extracted_save_data


@hook("WillowGame.WillowSaveGameManager:SaveGame", immediately_enable=True)
def save_game(_1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction) -> None:  # noqa: D103
    # We're going to inject our arbitrary save data here. This is the last time the save game can be
    # edited before writing to disk. Extremely large string sizes can crash the game, so we may want
    # to add a safety check at some point.1M characters has worked fine, so unlikely to be an issue.

    # For callbacks, only process enabled mods and only when we're in game. We'll run these first so
    # mod can use it to set values on the save options.
    enabled_mods = [mod_id for mod_id, mod in registered_mods.items() if mod.is_enabled]

    if get_pc().GetWillowPlayerPawn():
        for mod_id, callback in save_callbacks.items():
            if mod_id in enabled_mods:
                callback()

    # For saving, we'll overwrite existing mod data for enabled mods. Any disabled/uninstalled mods
    # will have their data left alone.
    lockout_list = args.SaveGame.UnloadableDlcLockoutList
    json_save_data = _extract_save_data(lockout_list)
    for mod_id, mod_data in registered_save_options.items():
        if mod_id in enabled_mods:
            mod_save_data = {
                identifier: option_json
                for identifier, save_option in mod_data.items()
                if (option_json := save_option._to_json()) is not ...  # pyright: ignore[reportPrivateUsage]
            }
            try:
                # Only calling this to validate the types, so one mod failing doesn't break
                # everything below.
                _ = json.dumps(mod_save_data)
                json_save_data[mod_id] = mod_save_data
            except TypeError:
                logging.error(f"Could not write save-specific data for {mod_id}.")
                logging.dev_warning(f"Data is not json encodable: {mod_save_data}")

    str_save_data = json.dumps(json_save_data)
    lockout_list.emplace_struct(
        LockoutDefName=str_save_data,
        DlcPackageId=_PACKAGE_ID,
    )

    # Reset our var tracking whether any options have changed since last save.
    save_options.options.any_option_changed = False


@hook("WillowGame.WillowSaveGameManager:EndLoadGame", Type.POST, immediately_enable=True)
def end_load_game(_1: UObject, _2: WrappedStruct, ret: Any, _4: BoundFunction) -> None:  # noqa: D103
    # We hook this to send data back to any registered mod save options. This gets called when
    # loading character in main menu also. No callback here because the timing of when this is
    # called doesn't make much sense to do anything with it. See hook on LoadPlayerSaveGame.

    # Often we'll load a save from a character with no save data. We'll set all save options
    # to default first to cover for any missing data.

    for mod_save_options in registered_save_options.values():
        for save_option in mod_save_options.values():
            set_option_to_default(save_option)

    # This function returns the new save game object, so use a post hook and grab it from `ret`
    save_game = ret
    if not save_game:
        return
    extracted_save_data = _extract_save_data(save_game.UnloadableDlcLockoutList)
    if not extracted_save_data:
        return

    for mod_id, extracted_mod_data in extracted_save_data.items():
        mod_save_options: ModSaveOptions = registered_save_options[mod_id]
        for identifier, extracted_value in extracted_mod_data.items():
            if save_option := mod_save_options.get(identifier):
                save_option._from_json(extracted_value)  # pyright: ignore[reportPrivateUsage]

    # Resetting change tracking var here too. Obviously a load sets a bunch of options, but we don't
    # want to count that as a real change that needs to be saved.
    save_options.options.any_option_changed = False


@hook(
    "WillowGame.WillowPlayerController:LoadPlayerSaveGame",
    Type.POST,
    immediately_enable=True,
)
def load_player_save_game(*_: Any) -> None:  # noqa: D103
    # This function is responsible for applying all save data to the character on loading into a
    # map. We use it to run callbacks, with the intent that any save data a mod wants to apply to
    # the player can be done here. At this point, save options have already been populated with
    # data from the save file through the EndLoadGame hook.
    enabled_mods = [mod_id for mod_id, mod in registered_mods.items() if mod.is_enabled]

    for mod_id, callback in load_callbacks.items():
        if mod_id in enabled_mods:
            callback()


@hook("WillowGame.FrontendGFxMovie:HideOptionsMovie", immediately_enable=True)
def hide_options_movie(*_: Any) -> None:  # noqa: D103
    # When an options movie is closed, we check to see if any save option values have changed since
    # the last time the file was saved. If it has, we save the game. This is necessary since values
    # changed while in the main menu would get overwritten or just get lost if a new character were
    # selected.

    if not save_options.options.any_option_changed:
        return

    trigger_save()
