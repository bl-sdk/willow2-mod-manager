import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from importlib import import_module
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from importlib.util import spec_from_file_location
from types import ModuleType

from mods_base import Game
from mods_base.mod_list import base_mod

from . import unrealsdk

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
    "legacy_compat",
    "import_legacy",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


base_mod.components.append(base_mod.ComponentInfo("Legacy SDK Compat", __version__))

"""
There are two parts to legacy SDK compatability.

The first is creating aliases and proxy objects for absolutely everything. While extensive, this is
the simple part. This is handled by the two `unrealsdk` and `ModMenu` submodules.

The second more difficult part is dealing with imports. In the legacy SDK, ill advisedly, the `Mods`
folder was part of the packaging, `mods/xyz` was packaged under `Mods.xyz`. This is no longer the
case in this version, it's just under a top level `xyz`. We can't trust users to extract legacy mods
any differently to updated ones, so we need to redirect these imports automatically.

The first step is to create a fake `Mods` module - the import hooks won't even run if the parent
module doesn't exist.

In doing this, we're already relying on some vagely defined behaviour.

All *packages* need a `__path__` attribute, which holds the locations to search for submodules.
Without one, attempting to import a submodule gives an explict `'Mods' is not a package` error.

The import system docs say that when importing a submodule, the system uses the parent's path, and
when importing a top level module it uses None. While not explictly stated, if we set the path to
None, it causes "submodule" imports to look in the top level instead.
"""
Mods = ModuleType("Mods")
Mods.__path__ = None  # type: ignore

"""
Now that we're allowed to try import from under `Mods`, define an import hook to redirect them.
"""


class LegacyImportPathFinder(PathFinder):
    @classmethod
    def find_spec(
        cls,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        # We only handle modules under `Mods`, everything else can fall back to the next finder
        if not fullname.startswith("Mods."):
            return None

        search_name = fullname.removeprefix("Mods.")
        search_path = path
        search_target = target

        # Special case for `ModMenu`: search for our replacement in this folder
        # This is basically just so that we don't need to manually specify all it's submodules
        # as replacements, it's just automatic.
        # `unrealsdk` already exists in `sys.modules`, so we have to replace it there
        if search_name == "ModMenu" or search_name.startswith("ModMenu."):
            search_name = f"{__name__}.{search_name}"
            search_path = tuple(__path__)

        # Try find the module under the path we expect it actually is
        spec = super().find_spec(search_name, search_path, search_target)

        # If we failed to find it, exit and fallback to the next finder
        if spec is None or not spec.has_location or spec.origin is None:
            return None

        # Create a new module spec using the original name, but overwrite the locations to be where
        # we just found them
        return spec_from_file_location(
            fullname,
            spec.origin,
            loader=SourceFileLoader(fullname, spec.origin),
            submodule_search_locations=spec.submodule_search_locations,
        )


# This is essentially an extra version of sys.modules which we swap in while legacy compat is active
# When we exit compat, we'll move any new imports under `Mods` into this, since we don't want to
# keep them around for normal mods
legacy_modules: dict[str, ModuleType] = {
    "unrealsdk": unrealsdk,
    "Mods": Mods,
}


@contextmanager
def legacy_compat() -> Iterator[None]:
    """Context manager which enables legacy SDK import compatibility while active."""
    # Add our path finder
    sys.meta_path.append(LegacyImportPathFinder)

    # Backup any current modules with the same name as a legacy one
    overwritten_modules = {name: mod for name, mod in sys.modules.items() if name in legacy_modules}
    # Overwrite with legacy modules
    sys.modules |= legacy_modules

    # Extra hack: Add the `Game.GetCurrent` alias to the actual class here
    # We can't easily create a seperate enum class with the alias, since `Game` isn't inheritable,
    # and since seperate identical enum classes still don't compare equal.
    # We don't want to leave this alias on permanently, so just deal with it here
    Game.GetCurrent = Game.get_current  # type: ignore

    try:
        yield
    finally:
        del Game.GetCurrent  # type: ignore

        # Move the legacy modules out of sys.modules back into our legacy dict
        for name in tuple(sys.modules.keys()):
            if name in {"Mods", "unrealsdk"} or name.startswith("Mods."):
                legacy_modules[name] = sys.modules.pop(name)
        # And add any overwritten modules back in
        sys.modules |= overwritten_modules

        # Remove the path finder
        sys.meta_path.remove(LegacyImportPathFinder)


def import_legacy(name: str, package: str | None = None) -> ModuleType:
    """Wrapper around `importlib.import_module` which uses legacy SDK import compatibility."""
    with legacy_compat():
        return import_module(name, package)
