# This file is part of the BL3/WL Oak Mod Manager.
# <https://github.com/bl-sdk/oak-mod-manager>
#
# The Oak Mod Manager is free software: you can redistribute it and/or modify it under the terms of
# the GNU Lesser General Public License Version 3 as published by the Free Software Foundation.
#
# The Oak Mod Manager is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with the Oak Mod Manager.
# If not, see <https://www.gnu.org/licenses/>.

import contextlib
import importlib
import json
import os
import sys
import traceback
import zipfile
from collections.abc import Collection
from pathlib import Path

import unrealsdk
from unrealsdk import logging

# If true, displays the full traceback when a mod fails to import, rather than the shortened one
FULL_TRACEBACKS: bool = False
# If true, makes debugpy wait for a client before continuing - useful for debugging errors which
# happen at import time
WAIT_FOR_CLIENT: bool = False

# A json list of paths to also to import mods from - you can add your repo to keep it separated
EXTRA_FOLDERS_ENV_VAR: str = "OAK_MOD_MANAGER_EXTRA_FOLDERS"


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

        if "PYUNREALSDK_DEBUGPY" not in os.environ:
            logging.dev_warning(
                "Was able to start debugpy, but the `PYUNREALSDK_DEBUGPY` environment variable is"
                " not set. This may prevent breakpoints from working properly.",
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


def get_all_mod_folders() -> Collection[Path]:
    """
    Gets all mod folders to try import from, including extra folders defined via env var.

    Returns:
        A collection of mod folder paths.
    """

    extra_folders = []
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        extra_folders = [Path(x) for x in json.loads(os.environ.get(EXTRA_FOLDERS_ENV_VAR, ""))]

    return [Path(__file__).parent, *extra_folders]


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


def validate_file_in_mods_folder(file: Path) -> bool:
    """
    Checks if a folder inside the mods folder is actually a mod we should try import.

    Sets up sys.path as required.

    Args:
        file: The file to analyse.
    Returns:
        True if the file is a valid .sdkmod to try import.
    """
    match file.suffix.lower():
        # Since hotfix mods can be any text file, this won't be exhaustive, but match and warn
        # about what we can
        # OHL often uses .url files to download the latest version of a mod, so also match that
        case ".bl3hotfix" | ".wlhotfix" | ".url":
            logging.error(
                f"'{file.name}' appears to be a hotfix mod, not an SDK mod. Move it to your hotfix"
                f" mods folder.",
            )
            return False

        case ".sdkmod":
            # Handled below
            pass

        case _:
            return False

    valid_zip: bool
    try:
        zip_iter = zipfile.Path(file).iterdir()
        zip_entry = next(zip_iter)
        valid_zip = zip_entry.name == file.stem and next(zip_iter, None) is None
    except (zipfile.BadZipFile, StopIteration, OSError):
        valid_zip = False

    if not valid_zip:
        logging.error(
            f"'{file.name}' does not appear to be valid, and has been ignored.",
        )
        logging.dev_warning(
            "'.sdkmod' files must be a zip, and may only contain a single root folder, which must"
            " be named the same as the zip (excluding suffix).",
        )
        return False

    sys.path.append(str(file))

    return True


def find_mods_to_import(mod_folders: Collection[Path]) -> Collection[str]:
    """
    Given a collection of mod folders, find the individual mod modules within it to try import.

    Sets up sys.path for `.sdkmod` mods.

    Returns:
        A collection of the module names to import.
    """
    mods_to_import: list[str] = []

    for folder in mod_folders:
        if not folder.exists():
            continue

        for entry in folder.iterdir():
            if entry.name.startswith("."):
                continue

            if entry.is_dir() and validate_folder_in_mods_folder(entry):
                mods_to_import.append(entry.name)

            elif entry.is_file() and validate_file_in_mods_folder(entry):
                mods_to_import.append(entry.stem)

    return mods_to_import


def import_mod_manager() -> None:
    """
    Imports any mod manager modules which have specific initialization order requirements.

    Most modules are fine to get imported as a mod/by another mod, but we need to do a few manually.
    """
    # Keybinds must be early to ensure it can overwrite the enable/disable functions before anything
    # else tries to use them.
    import keybinds  # noqa: F401  # pyright: ignore[reportUnusedImport]


def import_mods(mods_to_import: Collection[str]) -> None:
    """
    Tries to import a list of mods.

    Args:
        mods_to_import: The list of mods to import.
    """
    for name in mods_to_import:
        try:
            importlib.import_module(name)
        except Exception as ex:  # noqa: BLE001
            logging.error(f"Failed to import mod '{name}'")

            tb = traceback.extract_tb(ex.__traceback__)
            if not FULL_TRACEBACKS:
                tb = tb[-1:]

            logging.error("".join(traceback.format_exception_only(ex)))
            logging.error("".join(traceback.format_list(tb)))


def proton_null_exception_check() -> None:
    """
    Tries to detect and warn if we're running under a version of Proton which has the exception bug.

    For context, usually pybind detects exceptions using a catch all, which eventually calls through
    to `std::current_exception` to get the exact exception, and then runs a bunch of translators on
    it to convert it to a Python exception. When running under a bad Proton version, this call
    fails, and returns an empty exception pointer, so pybind is unable to translate it.

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
        return
    except SystemError:
        # Have the bug
        logging.error(
            "===============================================================================",
        )
        traceback.print_exc()
        logging.error(
            "\n"
            "Some particular Proton versions cause this, try switch to another one.\n"
            "Alternatively, the nightly release has builds from other compilers, which may also"
            " prevent it.\n"
            "\n"
            "Will attempt to import mods, but they'll likely break with a similar error.\n"
            "===============================================================================",
        )


# Don't really want to put a `__name__` check here, since it's currently just `builtins`, and that
# seems a bit unstable, like something that pybind might eventually change

mod_folders = get_all_mod_folders()
for folder in mod_folders:
    sys.path.append(str(folder.resolve()))

init_debugpy()

while not logging.is_console_ready():
    pass

# Now that the console's ready, show errors for any non-existent mod folders
for folder in mod_folders:
    if not folder.exists() or not folder.is_dir():
        logging.dev_warning(f"Extra mod folder does not exist: {folder}")

# And check for the proton null exception bug, if present we also want to print
proton_null_exception_check()

mods_to_import = find_mods_to_import(mod_folders)

import_mod_manager()
import_mods(mods_to_import)

del mod_folders, mods_to_import
