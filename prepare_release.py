#!/usr/bin/env python3
# ruff: noqa: T201
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from functools import cache
from io import BytesIO
from os import path
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

from pick_release_name import pick_release_name

if TYPE_CHECKING:
    from collections.abc import Iterator

THIS_FOLDER = Path(__file__).parent

# The various locations we extract to within the zip file
ZIP_MODS_FOLDER = Path("sdk_mods")
ZIP_STUBS_FOLDER = ZIP_MODS_FOLDER / ".stubs"
ZIP_SETTINGS_FOLDER = ZIP_MODS_FOLDER / "settings"
ZIP_EXECUTABLE_FOLDER = Path("Binaries") / "Win32"
ZIP_PLUGINS_FOLDER = ZIP_EXECUTABLE_FOLDER / "Plugins"

# The base CMake directories - these need the preset added after
BUILD_DIR_BASE = THIS_FOLDER / "out" / "build"
INSTALL_DIR_BASE = THIS_FOLDER / "out" / "install"

# Within the install folder, the folder we use for files that actually go into the exe's folder
INSTALL_EXECUTABLE_FOLDER_NAME = ".exe_folder"

# All non-gitignored folders which include any file matching one of these file suffixes becomes its
# own nested zip/.sdkmod.
# The list of suffixes is also useful to make sure we don't match dotfiles from submodules.
MODS_FOLDER = THIS_FOLDER / "src"
VALID_MOD_FILE_SUFFIXES = {".py", ".pyi", ".pyd", ".md"}

# And there are a few extra files which we want which aren't matched by the above
INIT_SCRIPT = MODS_FOLDER / "__main__.py"
SETTINGS_GITIGNORE = MODS_FOLDER / "settings" / ".gitignore"
STUBS_DIR = THIS_FOLDER / "stubs"

# The default license we use for any folders which don't already have one (due to being a submodule)
LICENSE = THIS_FOLDER / "LICENSE"

# Only used to extract the version number
MANAGER_PYPROJECT = THIS_FOLDER / "manager_pyproject.toml"

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


def cmake_configure(preset: str, extra_args: list[str]) -> None:
    """
    Configures the given CMake preset.

    Args:
        preset: The preset to configure.
        extra_args: Extra CMake args to append to the configure command.
    """
    subprocess.check_call(["cmake", ".", "--preset", preset, *extra_args])


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


@cache
def get_git_repo_version() -> str:
    """
    Gets a version string representing the current state of the git repo.

    Returns:
        The version string.
    """
    return get_git_commit_hash()[:8] + (", dirty" if check_git_is_dirty() else "")


def iter_non_gitignored_mod_folders() -> Iterator[Path]:
    """
    Iterates through all folders which are *not* gitignored within the mods folder.

    Includes untracked folders.

    Yields:
        Paths for each matched folder.
    """
    for folder in MODS_FOLDER.iterdir():
        if not folder.is_dir():
            continue

        # Check if this folder has any valid contents
        stdout = (
            subprocess.run(
                ["git", "ls-files", folder],
                check=True,
                stdout=subprocess.PIPE,
                encoding="utf8",
            ).stdout
            + subprocess.run(
                ["git", "ls-files", "-o", "--exclude-standard", folder],
                check=True,
                stdout=subprocess.PIPE,
                encoding="utf8",
            ).stdout
        )
        if not stdout:
            continue

        yield folder


def zip_dlls(zip_file: ZipFile, install_dir: Path) -> None:
    """
    Adds all the dlls/related files to the zip.

    Args:
        zip_file: The zip file to add the dlls to.
        install_dir: The CMake install dir with the built files.
    """
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

    # Also add a '._pth' file. This is equivalent to the default settings, so for more people this
    # is redundant. However, if someone has a global 'PYTHONPATH'/'PYTHONHOME' env var, having this
    # file means we ignore them.
    py_stem = next(install_dir.glob("python*.zip")).stem
    zip_file.writestr(
        str(ZIP_PLUGINS_FOLDER / (py_stem + "._pth")),
        (
            f"{py_stem}.zip\n"  # dummy comment to force multiline
            "DLLs\n"
        ),
    )


def zip_config_file(zip_file: ZipFile) -> None:
    """
    Adds the config file to the zip.

    Args:
        zip_file: The zip file to add the config file to.
    """
    # Path.relative_to doesn't work when where's no common base, need to use os.path
    # These paths are relative to the plugins folder
    init_script_path = path.relpath(ZIP_MODS_FOLDER / INIT_SCRIPT.name, ZIP_PLUGINS_FOLDER)
    pyexec_root = path.relpath(ZIP_MODS_FOLDER, ZIP_PLUGINS_FOLDER)

    version_number = tomllib.loads(MANAGER_PYPROJECT.read_text())["project"]["version"]
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


def zip_dot_sdkmod(zip_file: ZipFile, mod: Path, mod_files: list[Path]) -> None:
    """
    Adds a .sdkmod to the zip.

    Args:
        zip_file: The zip file to add the mod to.
        mod: The mod folder.
        mod_files: The list of valid files to zip up.
    """
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED, compresslevel=9) as sdkmod_zip:
        for file in mod_files:
            sdkmod_zip.write(
                file,
                mod.name / file.relative_to(mod),
            )

        # Add the license
        license_file = (
            existing_license if (existing_license := mod / "LICENSE").exists() else LICENSE
        )
        sdkmod_zip.write(license_file, Path(mod.name) / LICENSE.name)

    buffer.seek(0)
    zip_file.writestr(
        str(ZIP_MODS_FOLDER / (mod.name + ".sdkmod")),
        buffer.read(),
    )


def zip_mod_folder(zip_file: ZipFile, mod: Path, mod_files: list[Path]) -> None:
    """
    Adds a mod folder to the zip.

    Args:
        zip_file: The zip file to add the mod to.
        mod: The mod folder.
        mod_files: The list of valid files to zip up.
    """
    # We have to add it as a raw folder
    for file in mod_files:
        zip_file.write(
            file,
            ZIP_MODS_FOLDER / mod.name / file.relative_to(mod),
        )

    # Add the license
    license_file = existing_license if (existing_license := mod / "LICENSE").exists() else LICENSE
    zip_file.write(license_file, ZIP_MODS_FOLDER / mod.name / LICENSE.name)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Prepares a release zip.")
    parser.add_argument(
        "preset",
        choices=cmake_get_presets(),
        help="The CMake preset to use.",
    )
    parser.add_argument(
        "--configure",
        action="store_true",
        help="Configure CMake before building.",
    )
    parser.add_argument(
        "-C",
        "--configure-extra-args",
        action="append",
        default=[],
        metavar="...",
        help="Extra args to append to the CMake configure call.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="If specified, skips performing a CMake install. The directory must already exist.",
    )

    args = parser.parse_args()

    if check_git_is_dirty():
        print("WARNING: git repo is dirty")

    install_dir = INSTALL_DIR_BASE / str(args.preset)

    if args.configure:
        cmake_configure(args.preset, args.configure_extra_args)
    else:
        assert (BUILD_DIR_BASE / args.preset).exists(), "configure dir doesn't exist"

    if not args.skip_install:
        shutil.rmtree(install_dir, ignore_errors=True)
        cmake_install(BUILD_DIR_BASE / args.preset)

    assert install_dir.exists() and install_dir.is_dir(), "install dir doesn't exist"

    zip_name = f"willow2-sdk-{args.preset}.zip"
    print(f"Zipping {zip_name} ...")

    with ZipFile(zip_name, "w", ZIP_DEFLATED, compresslevel=9) as zip_file:
        zip_dlls(zip_file, install_dir)
        zip_config_file(zip_file)

        for folder in iter_non_gitignored_mod_folders():
            mod_files = list(iter_mod_files(folder, "debug" in args.preset))
            if not any(mod_files):
                continue

            if any(file.suffix == ".pyd" for file in mod_files):
                zip_mod_folder(zip_file, folder, mod_files)
            else:
                zip_dot_sdkmod(zip_file, folder, mod_files)

        zip_file.write(INIT_SCRIPT, ZIP_MODS_FOLDER / INIT_SCRIPT.name)
        zip_file.write(SETTINGS_GITIGNORE, ZIP_SETTINGS_FOLDER / SETTINGS_GITIGNORE.name)

        for file in STUBS_DIR.glob("**/*.pyi"):
            zip_file.write(
                file,
                ZIP_STUBS_FOLDER / file.relative_to(STUBS_DIR),
            )

        zip_file.write(LICENSE, ZIP_STUBS_FOLDER / LICENSE.name)
