# This file is part of the BL2/TPS/AoDK Willow2 Mod Manager.
# <https://github.com/bl-sdk/willow2-mod-manager>
#
# The Willow2 Mod Manager is free software: you can redistribute it and/or modify it under the terms
# of the GNU Lesser General Public License Version 3 as published by the Free Software Foundation.
#
# The Willow2 Mod Manager is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with the Willow2 Mod
# Manager. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import contextlib
import importlib
import json
import re
import shutil
import sys
import traceback
import warnings
import zipfile
from dataclasses import dataclass, field
from functools import cache, wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

# Note we try to import as few third party modules as possible before the console is ready, in case
# any of them cause errors we'd like to have logged
# Trusting that we can keep all the above standard library modules without issue
import unrealsdk
from unrealsdk import logging

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

# If true, displays the full traceback when a mod fails to import, rather than the shortened one
FULL_TRACEBACKS: bool = False
# If true, makes debugpy wait for a client before continuing - useful for debugging errors which
# happen at import time
WAIT_FOR_CLIENT: bool = False


@dataclass
class ModInfo:
    module: str
    legacy: bool
    location: Path
    duplicates: list[ModInfo] = field(default_factory=list["ModInfo"])


def init_debugpy() -> None:
    """Tries to import and setup debugpy. Does nothing if unable to."""
    try:
        import debugpy  # pyright: ignore[reportMissingImports]  # noqa: T100

        debugpy.listen(  # pyright: ignore[reportUnknownMemberType]  # noqa: T100
            ("localhost", 5678),
            in_process_debug_adapter=True,
        )

        if WAIT_FOR_CLIENT:
            debugpy.wait_for_client()  # pyright: ignore[reportUnknownMemberType]  # noqa: T100
            debugpy.breakpoint()  # pyright: ignore[reportUnknownMemberType]  # noqa: T100

        if not unrealsdk.config.get("pyunrealsdk", {}).get("debugpy", False):
            logging.dev_warning(
                "Was able to start debugpy, but the `pyunrealsdk.debugpy` config variable is not"
                " set to true. This may prevent breakpoints from working properly.",
            )

        # Make WrappedArrays resolve the same as lists
        from _pydevd_bundle.pydevd_resolver import (  # pyright: ignore[reportMissingImports]
            tupleResolver,  # pyright: ignore[reportUnknownVariableType]
        )
        from _pydevd_bundle.pydevd_xml import (  # pyright: ignore[reportMissingImports]
            _TYPE_RESOLVE_HANDLER,  # pyright: ignore[reportUnknownVariableType]
        )
        from unrealsdk.unreal import WrappedArray

        if not _TYPE_RESOLVE_HANDLER._initialized:  # pyright: ignore[reportUnknownMemberType]
            _TYPE_RESOLVE_HANDLER._initialize()  # pyright: ignore[reportUnknownMemberType]
        _TYPE_RESOLVE_HANDLER._default_type_map.append(  # pyright: ignore[reportUnknownMemberType]
            (WrappedArray, tupleResolver),
        )

    except (ImportError, AttributeError):
        pass


def get_all_mod_folders() -> Sequence[Path]:
    """
    Gets all mod folders to try import from, including extra folders defined via config file.

    Returns:
        A sequence of mod folder paths.
    """

    extra_folders = []
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        extra_folders = [
            Path(x) for x in unrealsdk.config.get("mod_manager", {}).get("extra_folders", [])
        ]

    return [Path(__file__).parent, *extra_folders]


@cache
def validate_folder_in_mods_folder(folder: Path) -> bool:
    """
    Checks if a folder inside the mods folder is actually a mod we should try import.

    Args:
        folder: The folder to analyse.
    Returns:
        True if the file is a valid module to try import.
    """
    if folder.name == "__pycache__":
        return False

    # A lot of people accidentally extract into double nested folders - they have a
    # `sdk_mods/MyCoolMod/MyCoolMod/__init__.py` instead of a `sdk_mods/MyCoolMod/__init__.py`
    # Usually this silently fails - we import `MyCoolMod` but there's nothing there
    # Detect this and give a proper error message
    if not (folder / "__init__.py").exists() and (folder / folder.name / "__init__.py").exists():
        logging.error(
            f"'{folder.name}' appears to be double nested, which may prevent it from being it from"
            f" being loaded. Move the inner folder up a level.",
        )
        # Since it's a silent error, may as well continue in case it's actually what you wanted

    # In the case we have a `sdk_mods/My Cool Mod v1.2`, python will try import `My Cool Mod v1`
    # first, and fail when it doesn't exist. Try detect this to throw a better error.
    # When this happens we're likely also double nested - `sdk_mods/My Cool Mod v1.2/MyCoolMod`
    # - but we can't detect that as easily, and the problem's the same anyway
    if "." in folder.name:
        logging.error(
            f"'{folder.name}' is not a valid python module - have you extracted the right folder?",
        )
        return False

    return True


RE_LEGACY_MOD_IMPORT = re.compile(r"from (\.\.ModMenu|Mods(\.\S+)?) import|BL2MOD\):")


@cache
def is_mod_folder_legacy_mod(folder: Path) -> bool:
    """
    Checks if a mod folder is a legacy mod.

    Args:
        folder: The folder to analyse.
    Returns:
        True if the folder contains a legacy mod.
    """
    # An exhaustive search over all legacy mods found we can reliably detect them by looking for one
    # of the following patterns in the first 1024 bytes of it's `__init__.py`.
    #   {from ..ModMenu import} xyz
    #   {from Mods.abc import} xyz
    #   class MyCoolMod(unrealsdk.{BL2MOD):}
    init = folder / "__init__.py"
    if not init.exists():
        return False
    with (folder / "__init__.py").open() as file:
        header = file.read(1024)
        return RE_LEGACY_MOD_IMPORT.search(header) is not None


# Catch when someone downloaded a mod a few times and ended up with a "MyMod (3).sdkmod"
RE_NUMBERED_DUPLICATE = re.compile(r"^(.+?) \(\d+\)\.sdkmod$", flags=re.I)


@cache
def validate_file_in_mods_folder(file: Path) -> bool:
    """
    Checks if a folder inside the mods folder is actually a mod we should try import.

    Sets up sys.path as required.

    Args:
        file: The file to analyse.
    Returns:
        True if the file is a valid .sdkmod to try import.
    """
    text_mod_error = (
        f"'{file.name}' appears to be a text mod, not an SDK mod. Move it to your binaries folder."
    )

    match file.suffix.lower():
        # Since text mods can be any text file, this won't be exhaustive, but match and warn
        # about what we can
        case ".blcm":
            logging.error(text_mod_error)
            return False

        case ".txt":
            # Try double check if this actually looks like a mod file
            # There's a bit more of a chance of people accidentally extracting a `readme.txt` or
            # similar, which we don't want to throw an error on
            with file.open() as f:
                line = f.readline()
                if line.strip().startswith(("<BLCMM", "set ")):
                    logging.error(text_mod_error)
            return False

        case ".sdkmod":
            # Handled below
            pass

        case _:
            return False

    valid_zip = False
    name_suggestion: str | None = None
    with contextlib.suppress(zipfile.BadZipFile, StopIteration, OSError):
        zip_iter = zipfile.Path(file).iterdir()
        zip_entry = next(zip_iter)
        valid_zip = zip_entry.name == file.stem and next(zip_iter, None) is None

        if (
            not valid_zip
            and (match := RE_NUMBERED_DUPLICATE.match(file.name))
            and (base_name := match.group(1)) == zip_entry.name
        ):
            name_suggestion = base_name + ".sdkmod"

    if not valid_zip:
        error_msg = f"'{file.name}' does not appear to be valid, and has been ignored."
        if name_suggestion is not None:
            error_msg += f" Is it supposed to be called '{name_suggestion}'?"
        logging.error(error_msg)
        logging.dev_warning(
            "'.sdkmod' files must be a zip, and may only contain a single root folder, which must"
            " be named the same as the zip (excluding suffix).",
        )
        return False

    str_path = str(file)
    if str_path not in sys.path:
        sys.path.append(str_path)

    return True


def find_mods_to_import(all_mod_folders: Sequence[Path]) -> Collection[ModInfo]:
    """
    Given the sequence of mod folders, find all individual mod modules within them to try import.

    Any '.sdkmod's found are added to `sys.path` as part of this step.

    Args:
        all_mod_folders: A sequence of all mod folders to import from, in the order they are listed
                         in `sys.path`.
    Returns:
        A collection of the module names to import.
    """
    mods_to_import: dict[str, ModInfo] = {}

    for folder in all_mod_folders:
        if not folder.exists():
            continue

        for entry in folder.iterdir():
            if entry.name.startswith("."):
                continue

            mod_info: ModInfo
            if entry.is_dir() and validate_folder_in_mods_folder(entry):
                mod_info = ModInfo(entry.name, is_mod_folder_legacy_mod(entry), entry)

            elif entry.is_file() and validate_file_in_mods_folder(entry):
                # Files are never legacy mods
                mod_info = ModInfo(entry.stem, False, entry)
            else:
                continue

            if mod_info.module in mods_to_import:
                mods_to_import[mod_info.module].duplicates.append(mod_info)
            else:
                mods_to_import[mod_info.module] = mod_info

    return mods_to_import.values()


def import_mods(mods_to_import: Collection[ModInfo]) -> None:
    """
    Tries to import a list of mods.

    Args:
        mods_to_import: The list of mods to import.
    """
    # False sorts before True, import all legacy mods last, so that any new mods can setup their own
    # legacy compat first
    for mod in sorted(mods_to_import, key=lambda x: x.legacy):
        try:
            if mod.legacy and legacy_compat is not None:
                with legacy_compat():
                    importlib.import_module(f"Mods.{mod.module}")
            else:
                importlib.import_module(mod.module)

        except Exception as ex:  # noqa: BLE001
            logging.error(f"Failed to import mod '{mod.module}'")

            tb = traceback.extract_tb(ex.__traceback__)
            if not FULL_TRACEBACKS:
                tb = tb[-1:]

            logging.error("".join(traceback.format_exception_only(ex)))
            logging.error("".join(traceback.format_list(tb)))


def hookup_warnings() -> None:
    """Hooks up the Python warnings system to the dev warning log type."""

    original_show_warning = warnings.showwarning
    dev_warn_logger = logging.Logger(logging.Level.DEV_WARNING)

    @wraps(warnings.showwarning)
    def showwarning(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: TextIO | None = None,
        line: str | None = None,
    ) -> None:
        if file is None:
            # Typeshed has this as a TextIO, but the implementation only actually uses `.write`
            file = dev_warn_logger  # type: ignore
        original_show_warning(message, category, filename, lineno, file, line)

    warnings.showwarning = showwarning
    warnings.resetwarnings()  # Reset filters, show all warnings


def check_proton_bugs() -> None:
    """Tries to detect and warn about various known proton issues."""

    """
    The exception bug
    -----------------
    Usually pybind detects exceptions using a catch all, which eventually calls through to
    `std::current_exception` to get the exact exception, and then runs a bunch of translators on it
    to convert it to a Python exception. When running under a bad Proton version, this call fails,
    and returns an empty exception pointer, so pybind is unable to translate it.

    This means Python throws a:
    ```
    SystemError: <built-in method __getattr__ of PyCapsule object at 0x00000000069AC780> returned NULL without setting an exception
    ```
    This is primarily a problem for `StopIteration`.
    """  # noqa: E501
    cls = unrealsdk.find_class("Object")
    try:
        # Cause an attribute error
        _ = cls._check_for_proton_null_exception_bug
    except AttributeError:
        # Working properly
        pass
    except SystemError:
        # Have the bug
        logging.error(
            "===============================================================================",
        )
        traceback.print_exc()
        logging.error(
            "\n"
            "Some particular Proton versions cause this, try switch to another one.\n"
            "Alternatively, the nightly release has builds from other compilers, which may\n"
            "also prevent it.\n"
            "\n"
            "Will attempt to import mods, but they'll likely break with a similar error.\n"
            "===============================================================================",
        )


LEGACY_MOD_MIGRATION_BLACKLIST: set[str] = {
    # Old Mod Manager
    "General",
    "ModMenu",
    # Rely on external modules
    "blimgui",
    "CommandExtensions",
    "TextModLoader",
    "TwitchLogin",
    # Misc
    "__pycache__",
    "AsyncUtil",
    "SideMissionRandomizer",
    "RoguelandsGamemode",
    "RoguelandsMiniGamemode",
    "ProjectileRandomizer",
}


LEGACY_TO_NEW_SETTING_REMAPPING: dict[str, str] = {
    "Options": "options",
    "Keybinds": "keybinds",
    "AutoEnable": "enabled",
}

LEGACY_MOD_FOLDER: Path = Path("Mods")
NEW_MOD_FOLDER: Path = Path(__file__).parent
NEW_SETTINGS_FOLDER: Path = NEW_MOD_FOLDER / "settings"


def migrate_mod_settings_file(
    old_settings_file: Path,
    new_settings_file: Path,
    mod_name: str,
) -> bool:
    """
    Migrates a single legacy mod's settings file to the new settings folder.

    Args:
        old_settings_file: The path of the old settings file.
        new_settings_file: The path to migrate the settings file to.
        mod_name: The name of the mod this file is from, to be used in log messages.
    Returns:
        True if successfully migrated, false if an error occurred.
    """
    if not old_settings_file.exists():
        # Mod doesn't have settings, can continue
        return True

    with old_settings_file.open("r") as old, new_settings_file.open("w") as new:
        data: dict[str, Any]
        try:
            data = json.load(old)
            if not isinstance(data, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            logging.warning(
                f"The settings file for legacy mod '{mod_name}' appears to be invalid. Not"
                f" migrating it to prevent losing data.",
            )
            return False

        for old_name, new_name in LEGACY_TO_NEW_SETTING_REMAPPING.items():
            if old_name in data:
                data[new_name] = data.pop(old_name)
        json.dump(data, new, indent=4)

    old_settings_file.unlink()

    return True


def migrate_legacy_mods_folder() -> bool:
    """
    Migrates any mods and their settings files from the legacy mod folder into the new one.

    Returns:
        True if any migrations were performed.
    """

    if legacy_compat is None or not (
        unrealsdk.config.get("mod_manager", {}).get("legacy_mod_migration", False)
    ):
        return False

    if not LEGACY_MOD_FOLDER.exists():
        return False

    migrated_any = False
    for entry in LEGACY_MOD_FOLDER.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".sdkmod":
            new_mod_file = NEW_MOD_FOLDER / entry.name
            if new_mod_file.exists():
                logging.warning(
                    f"Not migrating '{entry.name}' since a file with the same name already exists.",
                )
                continue

            shutil.copy(entry, new_mod_file)
            continue

        if (
            not entry.is_dir()
            or entry.name in LEGACY_MOD_MIGRATION_BLACKLIST
            or entry.name.startswith(".")
            or not (entry / "__init__.py").exists()
        ):
            continue

        new_mod_folder = NEW_MOD_FOLDER / entry.name

        old_settings_file = entry / "settings.json"
        new_settings_file = NEW_SETTINGS_FOLDER / (entry.name + ".json")

        # To be safe, don't migrate if we'd overwrite things, if a folder or settings file exists
        if new_mod_folder.exists() or (old_settings_file.exists() and new_settings_file.exists()):
            reason = "folder" if new_mod_folder.exists() else "settings file"
            logging.warning(
                f"Not migrating legacy mod '{entry.name}' since a {reason} with the same name"
                f" already exists.",
            )
            continue

        if not migrate_mod_settings_file(old_settings_file, new_settings_file, entry.name):
            continue

        shutil.move(entry, new_mod_folder)
        migrated_any = True

    return migrated_any


# Don't really want to put a `__name__` check here, since it's currently just `builtins`, and that
# seems a bit unstable, like something that pybind might eventually change

# Do as little as possible before console's ready

# Add all mod folders to `sys.path` first
mod_folders = get_all_mod_folders()
for folder in mod_folders:
    sys.path.append(str(folder.resolve()))

init_debugpy()

while not logging.is_console_ready():
    pass


# Now that the console's ready, hook up the warnings system, and show some other warnings users may
# be interested in
hookup_warnings()

check_proton_bugs()
for folder in mod_folders:
    if not folder.exists() or not folder.is_dir():
        logging.dev_warning(f"Extra mod folder does not exist: {folder}")

# Find all mods once to add any `.sdkmod`s to `sys.path`
mods_to_import = find_mods_to_import(mod_folders)

# Now see if we're allowed to use legacy compat - this may be in a `.sdkmod`
try:
    from legacy_compat import legacy_compat
except ImportError:
    logging.warning("Legacy SDK Compatibility has been disabled")
    legacy_compat = None

# Try migrate legacy mods
if migrate_legacy_mods_folder():
    # If we migrated any, find all mods again, to include the new ones
    mods_to_import = find_mods_to_import(mod_folders)

# Warn about duplicate mods
for mod in mods_to_import:
    if not mod.duplicates:
        continue
    logging.warning(f"Found multiple versions of mod '{mod.module}'. In order of priority:")
    # All folders always have higher priority than any files
    folders = (info.location for info in (mod, *mod.duplicates) if info.location.is_dir())
    files = (info.location for info in (mod, *mod.duplicates) if info.location.is_file())
    for location in (*folders, *files):
        logging.warning(str(location.resolve()))

# Import any mod manager modules which have specific initialization order requirements.
# Most modules are fine to get imported as a mod/by another mod, but we need to do a few manually.
# Prefer to import these after console is ready so we can show errors
import keybinds  # noqa: F401, E402  # pyright: ignore[reportUnusedImport]
from mods_base.mod_list import register_base_mod  # noqa: E402

import_mods(mods_to_import)

# After importing everything, register the base mod
register_base_mod()
