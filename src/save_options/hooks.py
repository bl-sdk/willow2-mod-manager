import json
from json import JSONDecodeError
from typing import Any

from unrealsdk import logging, make_struct
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

import save_options.options
from mods_base import JSON, get_pc, hook
from save_options.options import trigger_save
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
    lockout_list: list[WrappedStruct],
) -> tuple[dict[str, dict[str, JSON]], list[WrappedStruct]]:
    # Grab the json string from UnloadableDlcLockoutList based on the package id, then load to
    # Python object. Returns empty dict if no data found. Returns the remaining lockout_list
    # as the second element of a tuple so as not to overwrite unrelated data."""

    matching_lockout_data = next(
        (lockout_data for lockout_data in lockout_list if lockout_data.DlcPackageId == _PACKAGE_ID),
        None,
    )
    if not matching_lockout_data:
        return {}, lockout_list

    # Preserve other package Ids on the off chance someone else uses this.
    lockout_list_other = [
        lockout_data for lockout_data in lockout_list if lockout_data.DlcPackageId != _PACKAGE_ID
    ]

    extracted_save_data: dict[str, dict[str, JSON]] = {}
    if matching_lockout_data.LockoutDefName:
        try:
            extracted_save_data = json.loads(matching_lockout_data.LockoutDefName)
        except JSONDecodeError:
            # Invalid data, just clear the contents
            extracted_save_data = {}
        # Pylance saying this instance check unnecessary, but json.loads can return valid non-dict
        # objects.
        if not isinstance(extracted_save_data, dict):  # type: ignore
            logging.error(
                f"Could not load dict object from custom save string:"
                f"{matching_lockout_data.LockoutDefName}"  # noqa: COM812
            )
            extracted_save_data = {}
    return extracted_save_data, lockout_list_other


@hook("WillowGame.WillowSaveGameManager:SaveGame", immediately_enable=True)
def save_game(_1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction) -> None:  # noqa: D103
    # We're going to inject our arbitrary save data here. This is the last time the save game can be
    # edited before writing to disk. Extremely large string sizes can crash the game, so we may want
    # to add a safety check at some point.1M characters has worked fine, so unlikely to be an issue.

    # For callbacks, only process enabled mods and only when we're in game. We'll run these first so
    # mod can use it to set values on the save options.
    enabled_mods = [mod_id for mod_id, mod in registered_mods.items() if mod.is_enabled]

    if get_pc().GetWillowPlayerPawn():
        callbacks_to_process = {
            mod_id: callback
            for mod_id, callback in save_callbacks.items()
            if mod_id in enabled_mods
        }

        for callback in callbacks_to_process.values():
            callback()

    # For saving, we'll overwrite existing mod data for enabled mods. Any disabled/uninstalled mods
    # will have their data left alone.
    json_save_data, lockout_list = _extract_save_data(args.SaveGame.UnloadableDlcLockoutList)
    for mod_id, mod_data in registered_save_options.items():
        if mod_id in enabled_mods:
            mod_save_data = {
                identifier: option_json
                for identifier, save_option in mod_data.items()
                if (option_json := save_option._to_json()) is not ...  # type: ignore
            }
            try:
                json.dumps(mod_save_data)
                json_save_data[mod_id] = mod_save_data
            except TypeError:
                logging.error(
                    f"Could not save data for {mod_id}. Data is not json encodable:{mod_save_data}"  # noqa: COM812
                )

    str_save_data = json.dumps(json_save_data)
    custom_lockout = make_struct(
        "UnloadableDlcLockoutData",
        LockoutDefName=str_save_data,
        DlcPackageId=_PACKAGE_ID,
    )
    lockout_list.append(custom_lockout)
    args.SaveGame.UnloadableDlcLockoutList = lockout_list

    # Reset our var tracking whether any options have changed since last save.
    save_options.options.any_option_changed = False


@hook("WillowGame.WillowSaveGameManager:EndLoadGame", Type.POST, immediately_enable=True)
def end_load_game(_1: UObject, _2: WrappedStruct, ret: Any, _4: BoundFunction) -> None:  # noqa: D103
    # We hook this to send data back to any registered mod save options. This gets called when
    # loading character in main menu also. No callback here because the timing of when this is
    # called doesn't make much sense to do anything with it. See hook on LoadPlayerSaveGame.
    if ret:
        extracted_save_data, _ = _extract_save_data(ret.UnloadableDlcLockoutList)
    else:
        return

    if not extracted_save_data:
        return

    for mod_id, extracted_mod_data in extracted_save_data.items():
        mod_save_options: ModSaveOptions = registered_save_options[mod_id]
        for identifier, extracted_value in extracted_mod_data.items():
            if save_option := mod_save_options.get(identifier):
                save_option._from_json(extracted_value)  # type: ignore

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
    callbacks_to_process = {
        mod_id: callback for mod_id, callback in load_callbacks.items() if mod_id in enabled_mods
    }

    for callback in callbacks_to_process.values():
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
