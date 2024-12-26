#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import tomllib
from collections.abc import Iterator, Sequence
from functools import cache
from io import BytesIO
from os import path
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pick_release_name import pick_release_name

THIS_FOLDER = Path(__file__).parent

BASE_MOD = THIS_FOLDER / "src" / "mods_base"
CONSOLE_MENU = THIS_FOLDER / "src" / "console_mod_menu"
KEYBINDS = THIS_FOLDER / "src" / "keybinds"
LEGACY_COMPAT = THIS_FOLDER / "src" / "legacy_compat"
NETWORKING = THIS_FOLDER / "src" / "networking"
STANDARD_MENU = THIS_FOLDER / "src" / "willow2_mod_menu"
UI_UTILS = THIS_FOLDER / "src" / "ui_utils"


ALL_MOD_FOLDERS = (
    BASE_MOD,
    CONSOLE_MENU,
    KEYBINDS,
    LEGACY_COMPAT,
    NETWORKING,
    STANDARD_MENU,
    UI_UTILS,
)


INIT_SCRIPT = THIS_FOLDER / "src" / "__main__.py"
SETTINGS_GITIGNORE = THIS_FOLDER / "src" / "settings" / ".gitignore"

LICENSE = THIS_FOLDER / "LICENSE"

MODS_WITH_EXISTING_LICENSE = {
    # These have their own due to being submodules
    BASE_MOD,
    CONSOLE_MENU,
}

BUILD_DIR_BASE = THIS_FOLDER / "out" / "build"
INSTALL_DIR_BASE = THIS_FOLDER / "out" / "install"

STUBS_DIR = THIS_FOLDER / "libs" / "pyunrealsdk" / "stubs"
STUBS_LICENSE = THIS_FOLDER / "libs" / "pyunrealsdk" / "LICENSE"

PYPROJECT_FILE = THIS_FOLDER / "manager_pyproject.toml"


# Primarily to skip over all the dotfiles in mods which are submodules
VALID_MOD_FILE_SUFFIXES = {".py", ".pyi", ".pyd", ".md"}


# Regex to extract presets from a `cmake --list-presets` command
LIST_PRESETS_RE = re.compile('  "(.+)"')


@cache
def cmake_get_presets() -> list[str]:
    """
    Gets the presets which may be used.

    Returns:
        A list of presets.
    """
    proc = subprocess.run(
        ["cmake", "--list-presets"],
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf8",
    )
    return LIST_PRESETS_RE.findall(proc.stdout)


def cmake_install(build_dir: Path) -> None:
    """
    Builds and installs a cmake configuration.

    Args:
        build_dir: The preset's build dir.
    """
    subprocess.check_call(["cmake", "--build", build_dir, "--target", "install"])


@cache
def get_git_commit_hash(identifier: str | None = None) -> str:
    """
    Gets the full commit hash of the current git repo.

    Args:
        identifier: The identifier of the commit to get, or None to get the latest.
    Returns:
        The commit hash.
    """
    args = ["git", "show", "-s", "--format=%H"]
    if identifier is not None:
        args.append(identifier)

    return subprocess.run(
        args,
        cwd=Path(__file__).parent,
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf8",
    ).stdout.strip()


@cache
def check_git_is_dirty() -> bool:
    """
    Checks if the git repo is dirty.

    Returns:
        True if the repo is dirty.
    """
    # This command returns the list of modified files, so any output means dirty
    return any(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).parent,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout,
    )


def get_git_repo_version() -> str:
    """
    Gets a version string representing the current state of the git repo.

    Returns:
        The version string.
    """
    return get_git_commit_hash()[:8] + (", dirty" if check_git_is_dirty() else "")


def iter_mod_files(mod_folder: Path, debug: bool) -> Iterator[Path]:
    """
    Iterates through all files in the given mod folder which are valid to export.

    Args:
        mod_folder: Path to the mod folder to iterate through.
        debug: True if creating a debug zip.
    Yields:
        Valid files to export.
    """
    for file in mod_folder.glob("**/*"):
        if not file.is_file():
            continue
        if file.parent.name == "__pycache__":
            continue

        if file.suffix not in VALID_MOD_FILE_SUFFIXES:
            continue
        if file.suffix == ".pyd" and file.stem.endswith("_d") != debug:
            continue

        yield file


ZIP_MODS_FOLDER = Path("sdk_mods")
ZIP_STUBS_FOLDER = ZIP_MODS_FOLDER / ".stubs"
ZIP_SETTINGS_FOLDER = ZIP_MODS_FOLDER / "settings"
ZIP_EXECUTABLE_FOLDER = Path("Binaries") / "Win32"
ZIP_PLUGINS_FOLDER = ZIP_EXECUTABLE_FOLDER / "Plugins"


def _zip_init_script(zip_file: ZipFile) -> None:
    zip_file.write(INIT_SCRIPT, ZIP_MODS_FOLDER / INIT_SCRIPT.name)


def _zip_config_file(zip_file: ZipFile) -> None:
    # Path.relative_to doesn't work when where's no common base, need to use os.path
    # While the file goes in the plugins folder, this path is relative to *the executable*
    init_script_path = path.relpath(ZIP_MODS_FOLDER / INIT_SCRIPT.name, ZIP_EXECUTABLE_FOLDER)
    pyexec_root = path.relpath(ZIP_MODS_FOLDER, ZIP_EXECUTABLE_FOLDER)

    version_number = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["version"]
    git_version = get_git_repo_version()
    display_version = f"{version_number} ({git_version})"

    release_name = pick_release_name(get_git_commit_hash())

    # Tomllib doesn't support dumping yet, so we have to create it as a string
    # Using `json.dumps` to escape strings, since it should be mostly compatible
    config = (
        f"[unrealsdk]\n"
        f"locking_function_calls = true\n"
        f"\n"
        f"[pyunrealsdk]\n"
        f"init_script = {json.dumps(init_script_path)}\n"
        f"pyexec_root = {json.dumps(pyexec_root)}\n"
        f"\n"
        f"[mod_manager]\n"
        f"display_version = {json.dumps(display_version)}\n"
        f"legacy_mod_migration = true\n"
        f"\n"
        f"[willow2_mod_menu]\n"
        f"display_version = {json.dumps(release_name)}\n"
    )

    zip_file.writestr(str(ZIP_PLUGINS_FOLDER / "unrealsdk.toml"), config)


def _zip_mod_folders(zip_file: ZipFile, mod_folders: Sequence[Path], debug: bool) -> None:
    for mod in mod_folders:
        # If the mod contains any .pyds
        if next(mod.glob("**/*.pyd"), None) is not None:
            # We have to add it as a raw folder
            for file in iter_mod_files(mod, debug):
                zip_file.write(
                    file,
                    ZIP_MODS_FOLDER / mod.name / file.relative_to(mod),
                )

            # Add the license
            license_file = mod / "LICENSE" if mod in MODS_WITH_EXISTING_LICENSE else LICENSE
            zip_file.write(license_file, ZIP_MODS_FOLDER / mod.name / LICENSE.name)
        else:
            # Otherwise, we can add it as a .sdkmod
            buffer = BytesIO()
            with ZipFile(buffer, "w", ZIP_DEFLATED, compresslevel=9) as sdkmod_zip:
                for file in iter_mod_files(mod, debug):
                    sdkmod_zip.write(
                        file,
                        mod.name / file.relative_to(mod),
                    )

                # Add the license
                license_file = mod / "LICENSE" if mod in MODS_WITH_EXISTING_LICENSE else LICENSE
                sdkmod_zip.write(license_file, Path(mod.name) / LICENSE.name)

            buffer.seek(0)
            zip_file.writestr(
                str(ZIP_MODS_FOLDER / (mod.name + ".sdkmod")),
                buffer.read(),
            )


def _zip_stubs(zip_file: ZipFile) -> None:
    for file in STUBS_DIR.glob("**/*"):
        if not file.is_file():
            continue
        if file.suffix != ".pyi":
            continue

        zip_file.write(
            file,
            ZIP_STUBS_FOLDER / file.relative_to(STUBS_DIR),
        )

    zip_file.write(STUBS_LICENSE, ZIP_STUBS_FOLDER / STUBS_LICENSE.name)


def _zip_settings(zip_file: ZipFile) -> None:
    zip_file.write(
        SETTINGS_GITIGNORE,
        ZIP_SETTINGS_FOLDER / SETTINGS_GITIGNORE.name,
    )


INSTALL_EXECUTABLE_FOLDER_NAME = ".exe_folder"


def _zip_dlls(zip_file: ZipFile, install_dir: Path) -> None:
    exe_folder = install_dir / INSTALL_EXECUTABLE_FOLDER_NAME

    for file in install_dir.glob("**/*"):
        if not file.is_file():
            continue

        dest: Path
        if file.is_relative_to(exe_folder):
            dest = ZIP_EXECUTABLE_FOLDER / file.relative_to(exe_folder)
        else:
            dest = ZIP_PLUGINS_FOLDER / file.relative_to(install_dir)

        zip_file.write(file, dest)


def zip_release(
    output: Path,
    mod_folders: Sequence[Path],
    debug: bool,
    install_dir: Path,
) -> None:
    """
    Creates a release zip.

    Args:
        output: The location of the zip to create.
        init_script: The pyunrealsdk init script to use.
        mod_folders: A list of mod folders to include in the zip.
        debug: True if this is a debug release.
        stubs_dir: The stubs dir to include.
        settings_dir: The settings dir to include. All json files are ignored.
        install_dir: The CMake install dir to copy the dlls from.
        license_file: The location of the license file to copy to each of the created mod files.
    """

    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=9) as zip_file:
        _zip_init_script(zip_file)
        _zip_config_file(zip_file)
        _zip_mod_folders(zip_file, mod_folders, debug)
        _zip_stubs(zip_file)
        _zip_settings(zip_file)
        _zip_dlls(zip_file, install_dir)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Prepares a release zip.")
    parser.add_argument(
        "preset",
        choices=cmake_get_presets(),
        help="The CMake preset to use.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="If specified, skips performing a CMake install. The directory must still exist.",
    )

    args = parser.parse_args()

    if check_git_is_dirty():
        print("WARNING: git repo is dirty")

    install_dir = INSTALL_DIR_BASE / str(args.preset)

    if not args.skip_install:
        shutil.rmtree(install_dir, ignore_errors=True)
        cmake_install(BUILD_DIR_BASE / args.preset)

    assert install_dir.exists() and install_dir.is_dir(), "install dir doesn't exist"

    name = f"willow-sdk-{args.preset}.zip"
    print(f"Zipping {name} ...")

    zip_release(Path(name), ALL_MOD_FOLDERS, "debug" in args.preset, install_dir)
