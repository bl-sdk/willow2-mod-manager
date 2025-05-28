import inspect
from collections.abc import Sequence
from importlib.abc import FileLoader, SourceLoader
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType

from .source_replacements import ALL_SOURCE_REPLACEMENTS, SourceReplacement

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


# Inheriting straight from SourceFileLoader causes some other machinery to expect bytecode?
class ReplacementSourceLoader(FileLoader, SourceLoader):  # type: ignore
    replacements: SourceReplacement

    def __init__(self, fullname: str, path: str, replacements: SourceReplacement) -> None:
        super().__init__(fullname, path)
        self.replacements = replacements

    def get_data(self, path: str) -> bytes:  # noqa: D102
        return self.replacements.apply(path)


def spec_with_replacements(
    fullname: str,
    path: Sequence[str] | None,
    target: ModuleType | None,
    replacements: SourceReplacement,
) -> ModuleSpec | None:
    """
    Creates a module spec based on the existing module, but with a set of source replacements.

    Args:
        fullname: The fully resolved module name, copied from the original call.
        path: The paths to search, copied from the original call.
        target: The target copied from the original call.
        replacements: The source replacements to apply.
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
        importing_module_name = importing_file.parent.name

        match importing_module_name, fullname:
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

            case _, _:
                # Check for generic source replacements
                for entry in ALL_SOURCE_REPLACEMENTS:
                    if entry.matches(importing_module_name, fullname):
                        return spec_with_replacements(fullname, path, target, entry)

                return None
