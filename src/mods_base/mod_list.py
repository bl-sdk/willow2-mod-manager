import json
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cmp_to_key
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

import pyunrealsdk
import unrealsdk

from . import MODS_DIR, __version__
from .command import AbstractCommand
from .hook import HookType
from .html_to_plain_text import html_to_plain_text
from .keybinds import KeybindType
from .mod import CoopSupport, Game, Library, Mod, ModType
from .options import BaseOption, ButtonOption, GroupedOption, HiddenOption
from .settings import SETTINGS_DIR

# region Mod List

mod_list: list[Mod] = []


def register_mod(mod: Mod) -> None:
    """
    Registers a mod instance.

    Args:
        mod: The mod to register.
    Returns:
        The mod which was registered.
    """
    if mod in mod_list:
        return
    mod_list.append(mod)
    mod.load_settings()


def deregister_mod(mod: Mod) -> None:
    """
    Removes a mod from the mod list.

    Args:
        mod: The mod to remove.
    """
    if mod.is_enabled:
        mod.disable(dont_update_setting=True)

    mod_list.remove(mod)


def get_ordered_mod_list() -> list[Mod]:
    """
    Gets the list of mods, in display order.

    Returns:
        The ordered mod list.
    """

    def cmp(a: Mod, b: Mod) -> int:
        # The base mod should always appear at the start
        if a == base_mod and b != base_mod:
            return -1
        if a != base_mod and b == base_mod:
            return 1

        # Sort libraries after all other mod types
        if a.mod_type is not ModType.Library and b.mod_type is ModType.Library:
            return -1
        if a.mod_type is ModType.Library and b.mod_type is not ModType.Library:
            return 1

        # Finally, sort by name
        # Strip html tags, whitespace, and compare case insensitively
        a_plain = html_to_plain_text(a.name.strip()).lower()
        b_plain = html_to_plain_text(b.name.strip()).lower()
        if a_plain < b_plain:
            return -1
        if a_plain > b_plain:
            return 1
        return 0

    return sorted(mod_list, key=cmp_to_key(cmp))


# endregion

# region Base Mod

MOD_DB_URL: str
MOD_RELEASE_API_URL: str
MOD_RELEASE_DOWNLOAD_URL: str

match Game.get_tree():
    case Game.Willow2:
        MOD_DB_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://bl-sdk.github.io/"
        )
        MOD_RELEASE_API_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://api.github.com/repos/bl-sdk/willow-mod-manager/releases/latest"
        )
        MOD_RELEASE_DOWNLOAD_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://github.com/bl-sdk/willow-mod-manager/releases/"
        )
    case Game.Oak:
        MOD_DB_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://bl-sdk.github.io/oak-mod-db/"
        )
        MOD_RELEASE_API_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://api.github.com/repos/bl-sdk/oak-mod-manager/releases/latest"
        )
        MOD_RELEASE_DOWNLOAD_URL = (  # pyright: ignore[reportConstantRedefinition]
            "https://github.com/bl-sdk/oak-mod-manager/releases/"
        )

_MANAGER_VERSION = os.environ.get("MOD_MANAGER_DISPLAY_VERSION", "Unknown Version")
RE_MANAGER_VERSION = re.compile(r"v?(\d+)\.(\d+)")


@dataclass
class BaseMod(Library):
    name: str = "Python SDK"
    author: str = "bl-sdk"
    version: str = _MANAGER_VERSION
    coop_support: CoopSupport = CoopSupport.ClientSide
    settings_file: Path | None = SETTINGS_DIR / "python-sdk.json"

    # As an internal interface, the other submodules which the sdk ships with by default should add
    # themselves to these fields on the `base_mod` object, rather than registering as their own mod.
    # This helps avoid cluttering the default mod list.

    keybinds: list[KeybindType] = field(default_factory=list)  # type: ignore
    options: list[BaseOption] = field(default_factory=list)  # type: ignore
    hooks: list[HookType] = field(default_factory=list)  # type: ignore
    commands: list[AbstractCommand] = field(default_factory=list)  # type: ignore

    @dataclass
    class ComponentInfo:
        name: str
        version: str

    # They should also all add themselves here, so we can record their versions
    components: list[ComponentInfo] = field(default_factory=list)

    # Base mod options
    get_latest_release_button: ButtonOption = field(init=False)
    latest_version_option: HiddenOption[str | None] = field(init=False)
    next_version_check_time_option: HiddenOption[str] = field(init=False)

    @property
    def description(self) -> str:
        """Custom description getter, which builds it from the list of components."""

        # We want to show components in alphabetical order
        # Rather than use sorted, and throw away the result, might as well just do a proper sort
        # Once already sorted, re-sorting should be relatively quick
        self.components.sort(key=lambda c: c.name.lower())

        description = "Components:"
        description += "<ul>"
        for comp in self.components:
            description += f"<li>{comp.name}: {comp.version}</li>"
        description += "</ul>"

        return description

    @description.setter
    def description(  # pyright: ignore[reportIncompatibleVariableOverride]
        self,
        _: str,
    ) -> None:
        """No-op description setter."""

    def __post_init__(self) -> None:
        super().__post_init__()

        self.get_latest_release_button = ButtonOption(
            "Get Latest Release",
            on_press=lambda _: os.startfile(MOD_RELEASE_DOWNLOAD_URL),  # type: ignore  # noqa: S606
            is_hidden=True,
        )
        self.latest_version_option = HiddenOption("Latest", None)
        self.next_version_check_time_option = HiddenOption("Next Check Time", "")

        self.options = [  # pyright: ignore[reportIncompatibleVariableOverride]
            self.get_latest_release_button,
            ButtonOption(
                "Open Mod Database",
                on_press=lambda _: os.startfile(MOD_DB_URL),  # type: ignore  # noqa: S606
            ),
            ButtonOption(
                "Open Installed Mods Folder",
                on_press=lambda _: os.startfile(MODS_DIR),  # type: ignore  # noqa: S606
            ),
            GroupedOption(
                "Version Checking",
                (
                    self.latest_version_option,
                    self.next_version_check_time_option,
                ),
                is_hidden=True,
            ),
        ]

        self.components = [
            BaseMod.ComponentInfo("Base", __version__),
            # Both of these start their version strings with their module name, strip it out
            BaseMod.ComponentInfo("unrealsdk", unrealsdk.__version__.partition(" ")[2]),
            BaseMod.ComponentInfo("pyunrealsdk", pyunrealsdk.__version__.partition(" ")[2]),
        ]

    def get_this_release_tuple(self) -> tuple[int, ...] | None:
        """
        Gets the version tuple for this release.

        Returns:
            The version tuple, or None if unknown.
        """
        if self.version == "Unknown Version":
            return None
        version_match = RE_MANAGER_VERSION.match(_MANAGER_VERSION)
        if version_match is None:
            return None
        return tuple(int(x) for x in version_match.groups())

    def get_latest_release_version(self) -> tuple[str, tuple[int, ...]] | tuple[None, None]:
        """
        Gets the version of the latest release.

        Should be called in a thread, as this makes a blocking HTTP request.

        Returns:
            A tuple of the latest version name and version tuple, or None and None if unknown.
        """
        try:
            resp = urlopen(  # noqa: S310 - hardcoded https
                Request(  # noqa: S310
                    MOD_RELEASE_API_URL,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                ),
            ).read()

            tag: str = json.loads(resp)["tag_name"]
            tag_match = RE_MANAGER_VERSION.match(tag)
            if tag_match is None:
                raise ValueError

            return tag, tuple(int(x) for x in tag_match.groups())

        except Exception:  # noqa: BLE001
            unrealsdk.logging.warning("SDK update check failed")
            unrealsdk.logging.dev_warning(traceback.format_exc())
            return None, None

    def perform_version_check(self) -> None:
        """
        Checks if there's a newer version, and updates the options appropriately.

        Should be called in a thread, as this makes a blocking HTTP request.
        """
        this_version = self.get_this_release_tuple()
        if this_version is None:
            unrealsdk.logging.warning("Skipping SDK update check since current version is unknown")
            return

        try:
            next_check_time = datetime.fromisoformat(self.next_version_check_time_option.value)
            if next_check_time > datetime.now(UTC):
                # Not time yet
                return
        except ValueError:
            # If we failed to parse the option, assume we need a new check
            pass

        latest_version_name, latest_version_tuple = self.get_latest_release_version()
        if latest_version_name is None or latest_version_tuple is None:
            return

        if latest_version_tuple > this_version:
            self.latest_version_option.value = latest_version_name
        else:
            self.latest_version_option.value = None

        next_check_time = datetime.now(UTC) + timedelta(days=1)
        self.next_version_check_time_option.value = next_check_time.isoformat()

        self.save_settings()

    def notify_latest_release(self) -> None:
        """
        Checks for a newer release, and notifies if one's found.

        Should be called in a thread, as this makes a blocking HTTP request.
        """
        self.perform_version_check()

        if self.latest_version_option.value is not None:
            self.get_latest_release_button.is_hidden = False
            unrealsdk.logging.warning(
                f"A newer SDK release is available: {self.latest_version_option.value}",
            )

    def get_status(self) -> str:
        """Custom status which shows when updates are available."""
        if self.latest_version_option.value is not None:
            return "<font color='#ffff00'>Update Available</font>"

        return super().get_status()


base_mod = BaseMod()


def register_base_mod() -> None:
    """Registers the base mod. Should be called by the mod loader after importing all components."""
    register_mod(base_mod)
    Thread(target=base_mod.notify_latest_release).start()


# endregion
