import inspect
import re
from collections.abc import Callable, Sequence
from importlib.abc import FileLoader, SourceLoader
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType

# While just messing with `Mod.__path__` is enough for most most mods, there are a few we need to do
# more advanced import hooking on.


class StringSourceLoader(SourceFileLoader):
    source: bytes

    def __init__(self, fullname: str, path: str, source: bytes) -> None:
        super().__init__(fullname, path)
        self.source = source

    def get_data(self, path: str) -> bytes:  # noqa: ARG002, D102
        return self.source


def spec_from_string(fullname: str, source: bytes) -> ModuleSpec | None:
    """
    Creates a module spec from a hardcoded string.

    Args:
        fullname: The fully resolved module name.
        source: The source code.
    """
    return spec_from_file_location(
        fullname,
        "<fake location>",
        loader=StringSourceLoader(fullname, "<fake location>", source),
    )


# Inheriting straight from SourceFileLoade causes some other machinery to expect bytecode?
class ReplacementSourceLoader(FileLoader, SourceLoader):  # type: ignore
    type Pattern = tuple[bytes | re.Pattern[bytes], bytes | Callable[[re.Match[bytes]], bytes]]

    replacements: Sequence[Pattern]

    def __init__(self, fullname: str, path: str, replacements: Sequence[Pattern]) -> None:
        super().__init__(fullname, path)
        self.replacements = replacements

    def get_data(self, path: str) -> bytes:  # noqa: D102
        data = Path(path).read_bytes()
        for pattern, replacement in self.replacements:
            data = re.sub(pattern, replacement, data)
        return data


def spec_with_replacements(
    fullname: str,
    path: Sequence[str] | None = None,
    target: ModuleType | None = None,
    *replacements: ReplacementSourceLoader.Pattern,
) -> ModuleSpec | None:
    """
    Creates a module spec based on the existing module, but applying a set of regex replacements.

    Args:
        fullname: The fully resolved module name, copied from the original call.
        path: The paths to search, copied from the original call.
        target: The target copied from the original call.
        *replacements: Tuples of a regex pattern and it's replacement.
    """
    original_spec = PathFinder.find_spec(fullname, path, target)
    if original_spec is None or not original_spec.has_location or original_spec.origin is None:
        return None

    return spec_from_file_location(
        fullname,
        original_spec.origin,
        loader=ReplacementSourceLoader(fullname, original_spec.origin, replacements),
    )


class LegacyCompatMetaPathFinder:
    @staticmethod
    def get_importing_file() -> Path:
        """
        Gets the file which triggered the in progress import.

        Returns:
            The importing file.
        """
        # Skip the frame for this function and find_spec below
        for frame in inspect.stack()[2:]:
            # Then skip everything in the import machinery
            if "importlib" in frame.filename:
                continue
            return Path(frame.filename)
        raise RuntimeError

    @classmethod
    def find_spec(  # noqa: D102
        cls,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        importing_file = cls.get_importing_file()

        match importing_file.parent.name, fullname:
            # EridiumLib adds it's dist folder with a path relative to the executable - fix that
            case "EridiumLib", "semver":
                return spec_from_file_location(
                    "Mods.EridiumLib.fake_dist.semver",
                    importing_file.parent / "dist" / "semver.py",
                )

            # Something about trying to load a requests build from 6 major versions ago completely
            # breaks, we can't easily get it to load.
            # However, it turns out all EridiumLib needs is a get method, which is allowed to just
            # throw.
            case "EridiumLib", "requests":
                return spec_from_string(
                    "Mods.EridiumLib.fake_dist.requests",
                    (
                        b"def get(url: str, timeout: int) -> str:  # noqa: D103\n"
                        b"    raise NotImplementedError"
                    ),
                )

            # Constructor has a bad bit of logic for getting the relative file path to execute.
            # Since we moved the mods folder, it breaks. Replace it with some proper logic.
            case (
                ("Constructor", "Mods.Constructor.hotfix_manager")
                | ("Exodus", "Mods.Exodus.hotfix_manager")
                | ("ExodusTPS", "Mods.ExodusTPS.hotfix_manager")
                | ("Snowbound", "Mods.Snowbound.hotfix_manager")
            ):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    # Import on one line just to avoid changing line numbers
                    (b"import os", b"import os, sys"),
                    (
                        rb'( +)exec_path = str\(file\)\.split\("Binaries\\+", 1\)\[1\]([\r\n]+)'
                        rb'( +)bl2tools.console_command\("exec " \+ exec_path, False\)([\r\n]+)',
                        rb"\1exec_path = os.path.relpath(file,"
                        rb' os.path.join(sys.executable, "..", ".."))\2'
                        rb"\3bl2tools.console_command(f'exec \"{exec_path}\"', False)\4",
                    ),
                )

            # Imported by the init script, accept both `sdk_mods` folder in the release and the
            # `src` folder for if developing in this repo

            # BL2Fix does some redundant random.seed() setting. Py 3.11 removed support for setting
            # the seed from an arbitrary type, so just completely get rid of the calls.
            case (("src" | "sdk_mods"), "Mods.BL2Fix"):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    (rb"random\.seed\(datetime\.datetime\.now\(\)\)", b""),
                )

            # To help out Text Mod Loader, which does all the actual legacy compat for Arcania, get
            # rid of this hook, easier to do here. It ends up permanently enabled otherwise.
            case (("src" | "sdk_mods"), "Mods.Arcania"):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    (rb'@ModMenu\.Hook\("Engine\.GameInfo\.PostCommitMapChange"\)', b""),
                )

            # This is a use case the new SDK kind of broke. Reward Rreroller passed the
            # `MissionStatusPlayerData:ObjectivesProgress` field to `ShouldGrantAlternateReward`.
            # While they're both arrays of ints called `ObjectivesProgress`, since they're different
            # properties they're no longer compatible. Turn it into a list to make a copy.
            case (("src" | "sdk_mods"), "Mods.RewardReroller"):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    (
                        rb"mission\.ShouldGrantAlternateReward\(progress\)",
                        b"mission.ShouldGrantAlternateReward(list(progress))",
                    ),
                )

            # Loot randomizer needs quite a few fixes
            case (
                # Here's the downside of using a single folder name, these cases just look weird.
                ("Mod", "Mods.LootRandomizer.Mod.missions")
                # Newer versions split the files
                | ("Mod", "Mods.LootRandomizer.Mod.bl2.locations")
                | ("Mod", "Mods.LootRandomizer.Mod.tps.locations")
            ):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    # It called these functions with a bad arg type in two places. This is
                    # essentially undefined behaviour, so now gives an exception. Luckily, in this
                    # case the functions actually validated their arg, so this just became a no-op.
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

            case (
                "Mod",
                "Mods.LootRandomizer.Mod.hints"
                | "Mods.LootRandomizer.Mod.bl2"
                | "Mods.LootRandomizer.Mod.tps",
            ):
                return spec_with_replacements(
                    fullname,
                    path,
                    target,
                    # This is a bit of a weird one. Best we can tell, in legacy sdk if you didn't
                    # specify a struct field, it just left it alone, so this kept whatever the old
                    # grades data was.
                    # In new sdk setting an entire struct zero-inits missing fields instead - so add
                    # back in what we actually want it to be set to.
                    (
                        rb"inventory_template.Manufacturers = \(\(manufacturer\),\)",
                        b"inventory_template.Manufacturers = [(manufacturer[0], "
                        b"[((1, None), (1, 100), (0.5, None, None, 1), (1, None, None, 1))])]",
                    ),
                    # This one's a break just due to upgrading python. Hints were trying to be a
                    # string enum before StrEnum was introduced, so stringifying them now returns
                    # the name, not the value. Make it a real StrEnum instead.
                    (rb"class Hint\(str, enum\.Enum\):", b"class Hint(enum.StrEnum):"),
                )

            case _, _:
                return None
