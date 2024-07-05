#!/usr/bin/env python3
import re
import shutil
import subprocess
import textwrap
import tomllib
from collections.abc import Iterator, Sequence
from functools import cache
from io import BytesIO
from os import path
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

THIS_FOLDER = Path(__file__).parent

BASE_MOD = THIS_FOLDER / "src" / "mods_base"
BL3_MENU = THIS_FOLDER / "src" / "bl3_mod_menu"
KEYBINDS = THIS_FOLDER / "src" / "keybinds"
WL_MENU = THIS_FOLDER / "src" / "console_mod_menu"
UI_UTILS = THIS_FOLDER / "src" / "ui_utils"

INIT_SCRIPT = THIS_FOLDER / "src" / "__main__.py"
SETTINGS_GITIGNORE = THIS_FOLDER / "src" / "settings" / ".gitignore"

LICENSE = THIS_FOLDER / "LICENSE"

BUILD_DIR_BASE = THIS_FOLDER / "out" / "build"
INSTALL_DIR_BASE = THIS_FOLDER / "out" / "install"

STUBS_DIR = THIS_FOLDER / "libs" / "pyunrealsdk" / "stubs"
STUBS_LICENSE = THIS_FOLDER / "libs" / "pyunrealsdk" / "LICENSE"

PYPROJECT_FILE = THIS_FOLDER / "manager_pyproject.toml"


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
def get_git_repo_version() -> str:
    """
    Gets a version string representing the current state of the git repo.

    Returns:
        The version string.
    """
    commit_hash = subprocess.run(
        ["git", "show", "-s", "--format=%H"],
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf8",
    ).stdout.strip()

    # This command returns the list of modified files, so any output means dirty
    is_dirty = any(
        subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout,
    )

    return commit_hash[:8] + (", dirty" if is_dirty else "")


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

        if file.suffix == ".cpp":
            continue
        if file.suffix == ".pyd" and file.stem.endswith("_d") != debug:
            continue

        yield file


ZIP_MODS_FOLDER = Path("sdk_mods")
ZIP_STUBS_FOLDER = ZIP_MODS_FOLDER / ".stubs"
ZIP_SETTINGS_FOLDER = ZIP_MODS_FOLDER / "settings"
ZIP_EXECUTABLE_FOLDER = Path("OakGame") / "Binaries" / "Win64"
ZIP_PLUGINS_FOLDER = ZIP_EXECUTABLE_FOLDER / "Plugins"


def _zip_init_script(zip_file: ZipFile) -> None:
    output_init_script = ZIP_MODS_FOLDER / INIT_SCRIPT.name
    zip_file.write(INIT_SCRIPT, output_init_script)
    init_script_env = (
        # Path.relative_to doesn't work when where's no common base, need to use os.path
        # While the file goes in the plugins folder, this path is relative to *the executable*
        f"PYUNREALSDK_INIT_SCRIPT={path.relpath(output_init_script, ZIP_EXECUTABLE_FOLDER)}"
    )

    # We also define the display version via an env var, do that here too
    version_number = tomllib.loads(PYPROJECT_FILE.read_text())["project"]["version"]
    git_version = get_git_repo_version()
    display_version_env = f"MOD_MANAGER_DISPLAY_VERSION={version_number} ({git_version})"

    zip_file.writestr(
        str(ZIP_PLUGINS_FOLDER / "unrealsdk.env"),
        f"{init_script_env}\n{display_version_env}\n",
    )


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
            zip_file.write(LICENSE, ZIP_MODS_FOLDER / mod.name / LICENSE.name)
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
                sdkmod_zip.write(LICENSE, Path(mod.name) / LICENSE.name)

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

    py_stem = next(install_dir.glob("python*.zip")).stem
    zip_file.writestr(
        str(ZIP_PLUGINS_FOLDER / (py_stem + "._pth")),
        textwrap.dedent(
            f"""
            {path.relpath(ZIP_MODS_FOLDER, ZIP_PLUGINS_FOLDER)}
            {py_stem}.zip
            DLLs
            """,
        )[1:-1],
    )


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
        _zip_mod_folders(zip_file, mod_folders, debug)
        _zip_stubs(zip_file)
        _zip_settings(zip_file)
        _zip_dlls(zip_file, install_dir)


if __name__ == "__main__":
    from argparse import ArgumentParser, BooleanOptionalAction

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
    parser.add_argument(
        "--bl3",
        action=BooleanOptionalAction,
        default=True,
        help="Create a BL3 release zip. Defaults to on.",
    )
    parser.add_argument(
        "--wl",
        action=BooleanOptionalAction,
        default=True,
        help="Create a WL release zip. Defaults to on.",
    )
    parser.add_argument(
        "--unified",
        action=BooleanOptionalAction,
        default=False,
        help="Create a unified release zip. Defaults to off.",
    )
    args = parser.parse_args()

    install_dir = INSTALL_DIR_BASE / str(args.preset)

    if not args.skip_install:
        shutil.rmtree(install_dir, ignore_errors=True)
        cmake_install(BUILD_DIR_BASE / args.preset)

    assert install_dir.exists() and install_dir.is_dir(), "install dir doesn't exist"

    # Zip up all the requested files
    COMMON_FOLDERS = (BASE_MOD, KEYBINDS, UI_UTILS)

    for prefix, arg, mods in (
        ("bl3", args.bl3, (*COMMON_FOLDERS, BL3_MENU)),
        ("wl", args.wl, (*COMMON_FOLDERS, WL_MENU)),
        ("unified", args.unified, (*COMMON_FOLDERS, BL3_MENU, WL_MENU)),
    ):
        if not arg:
            continue

        name = f"{prefix}-sdk-{args.preset}.zip"
        print(f"Zipping {name} ...")

        zip_release(Path(name), mods, "debug" in args.preset, install_dir)
