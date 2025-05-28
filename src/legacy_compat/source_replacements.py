from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import unrealsdk

ALL_SOURCE_REPLACEMENTS: list[SourceReplacement] = []


@dataclass
class SourceReplacement:
    # i.e. things which are valid in calls to re.sub
    type Pattern = tuple[bytes | re.Pattern[bytes], bytes | Callable[[re.Match[bytes]], bytes]]

    module_patterns: tuple[tuple[str, str], ...]
    replacements: tuple[Pattern, ...]

    auto_register: ClassVar[bool] = True

    def __init__(self, module_patterns: tuple[tuple[str, str], ...], *args: Pattern) -> None:
        self.module_patterns = module_patterns
        self.replacements = args

        if SourceReplacement.auto_register:
            ALL_SOURCE_REPLACEMENTS.append(self)

    def matches(self, importing_module_folder: str, module_name: str) -> bool:
        """
        Checks if this matches the given module.

        Args:
            importing_module_folder: The folder name which imported this module.
            module_name: The full name of this module.
        Returns:
            True if it matches.
        """
        return (importing_module_folder, module_name) in self.module_patterns

    def apply(self, path: str) -> bytes:
        """
        Loads a file's bytes with with replacements applied.

        Args:
            path: Path to the file to read.
        Returns:
            The raw file bytes with all replacements applied.
        """
        data = Path(path).read_bytes()
        for pattern, replacement in self.replacements:
            data = re.sub(pattern, replacement, data)
        return data


# Constructor has a bad bit of logic for getting the relative file path to execute.
# Since we moved the mods folder, it breaks. Replace it with some proper logic.
SourceReplacement(
    (
        ("Constructor", "Mods.Constructor.hotfix_manager"),
        ("Exodus", "Mods.Exodus.hotfix_manager"),
        ("ExodusTPS", "Mods.ExodusTPS.hotfix_manager"),
        ("Snowbound", "Mods.Snowbound.hotfix_manager"),
    ),
    (b"import os", b"import os, sys"),
    (
        rb'( +)exec_path = str\(file\)\.split\("Binaries\\+", 1\)\[1\]([\r\n]+)'
        rb'( +)bl2tools.console_command\("exec " \+ exec_path, False\)([\r\n]+)',
        rb"\1exec_path = os.path.relpath(file,"
        rb' os.path.join(sys.executable, "..", ".."))\2'
        rb"\3bl2tools.console_command(f'exec \"{exec_path}\"', False)\4",
    ),
)

# BL2Fix does some redundant random.seed() setting. Py 3.11 removed support for setting the seed
# from an arbitrary type, so just completely get rid of the calls.
SourceReplacement(
    (("src", "Mods.BL2Fix"), ("sdk_mods", "Mods.BL2Fix")),
    (rb"random\.seed\(datetime\.datetime\.now\(\)\)", b""),
)


# To help out Text Mod Loader, which does all the actual legacy compat for Arcania, get rid of this
# hook, easier to do here. It ends up permanently enabled otherwise.
SourceReplacement(
    (("src", "Mods.Arcania"), ("sdk_mods", "Mods.Arcania")),
    (rb'@ModMenu\.Hook\("Engine\.GameInfo\.PostCommitMapChange"\)', b""),
)

# This is a use case the new SDK kind of broke. Reward Reroller passed the
# `MissionStatusPlayerData:ObjectivesProgress` field to `ShouldGrantAlternateReward`.
# While they're both arrays of ints called `ObjectivesProgress`, since they're different properties
# they're no longer compatible. Turn it into a list to make a copy.
SourceReplacement(
    (("src", "Mods.RewardReroller"), ("sdk_mods", "Mods.RewardReroller")),
    (
        rb"mission\.ShouldGrantAlternateReward\(progress\)",
        b"mission.ShouldGrantAlternateReward(list(progress))",
    ),
)

# Loot randomizer needs quite a few fixes
SourceReplacement(
    (
        # Here's the downside of using a single folder name, these cases just look weird.
        ("Mod", "Mods.LootRandomizer.Mod.missions"),
        # Newer versions split the files
        ("Mod", "Mods.LootRandomizer.Mod.bl2.locations"),
        ("Mod", "Mods.LootRandomizer.Mod.tps.locations"),
    ),
    # It called these functions with a bad arg type in two places. This is essentially undefined
    # behaviour, so now gives an exception. Luckily, in this case the functions actually validated
    # their arg, so this just became a no-op.
    # Remove the two bad calls.
    (rb"get_missiontracker\(\)\.(Unr|R)egisterMissionDirector\(giver\)", b"pass"),
    # I was just told this one never did anything, idk what the bug is
    (rb"sequence\.CustomEnableCondition\.bComplete = True", b""),
    # This one's the same as reward reroller, need to manually convert to a list
    (
        rb"caller\.FastTravelClip\.SendLocationData\(([\r\n]+ +)"
        rb"travels,([\r\n]+ +)"
        rb"caller\.LocationStationStrings,",
        rb"caller.FastTravelClip.SendLocationData(\1travels,\2list(caller.LocationStationStrings),",
    ),
)

SourceReplacement(
    (
        ("Mod", "Mods.LootRandomizer.Mod.hints"),
        ("Mod", "Mods.LootRandomizer.Mod.bl2"),
        ("Mod", "Mods.LootRandomizer.Mod.tps"),
    ),
    # This is a bit of a weird one. Best we can tell, in legacy sdk if you didn't specify a struct
    # field, it just left it alone, so this kept whatever the old grades data was.
    # In new sdk setting an entire struct zero-inits missing fields instead - so add back in what we
    # actually want it to be set to.
    (
        rb"inventory_template.Manufacturers = \(\(manufacturer\),\)",
        b"inventory_template.Manufacturers = [(manufacturer[0], "
        b"[((1, None), (1, 100), (0.5, None, None, 1), (1, None, None, 1))])]",
    ),
    # This one's a break just due to upgrading python. Hints were trying to be a string enum before
    # StrEnum was introduced, so stringifying them now returns the name, not the value. Make it a
    # real StrEnum instead.
    (rb"class Hint\(str, enum\.Enum\):", b"class Hint(enum.StrEnum):"),
)


# It turns out, the error here is protecting us from a full game crash on older versions of
# unrealsdk, so only apply this fix if we're running a new enough one
if unrealsdk.__version_info__ >= (2, 0, 0):
    # Reign of Giants is naughty, and deliberately writes an object to a property with a different
    # type - so any attempt of doing that in new sdk rightfully throws a type error. We need to
    # launder it in now.
    SourceReplacement(
        (("src", "Mods.ReignOfGiants"), ("sdk_mods", "Mods.ReignOfGiants")),
        (
            rb"(\S+\.DebugPawnMarkerInst) = (.+?)([\r\n])",
            rb"_o = \2; _c = _o.Class;"
            rb'_o.Class = new_unrealsdk.find_class("MaterialInstanceConstant");'
            rb"\1 = _o;"
            rb"_o.Class = _c\3",
        ),
    )


SourceReplacement.auto_register = False
