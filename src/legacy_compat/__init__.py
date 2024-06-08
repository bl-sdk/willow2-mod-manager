import sys
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType

from mods_base import Game
from mods_base.mod_list import base_mod
from unrealsdk import logging

from . import ModMenu
from . import unrealsdk as old_unrealsdk

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
    "legacy_compat",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

# May have to update this at some point if we decide to keep this around longer.
KILL_SWITCH = base_mod.version not in {"3.0", "3.1", "3.2", "3.3", "3.4"}

if KILL_SWITCH:
    logging.warning("Legacy SDK Compatibility has been disabled")
else:
    base_mod.components.append(base_mod.ComponentInfo("Legacy SDK Compat", __version__))

"""
There are two parts to legacy SDK compatibility.

The first is creating aliases and proxy objects for absolutely everything. While extensive, this is
relatively simple. This is handled by the two `unrealsdk` and `ModMenu` submodules.

The second more difficult part is dealing with imports. In the legacy SDK, ill advisedly, the `Mods`
folder was part of the packaging, `mods/xyz` was packaged under `Mods.xyz`. This is no longer the
case in this version, it's just under a top level `xyz`. We can't trust users to extract legacy mods
any differently to updated ones, so we need to redirect these imports automatically.
"""

# First, create a fake mods module
Mods = ModuleType("Mods")

"""
To allow importing submodules at all, to convert the module into a package, we need to set __path__.
But to what? This requires a bit of reading between the lines.

> The find_spec() method of meta path finders is called with two or three arguments. The first is
> the fully qualified name of the module being imported, for example foo.bar.baz. The second
> argument is the path entries to use for the module search. For top-level modules, the second
> argument is None, but for submodules or subpackages, the second argument is the value of the
> parent package's __path__ attribute.

When importing a submodule, it copies the value of the parent's __path__. When importing a top level
module, it uses None. We want importing a submodule of Mods to actually import a top level module -
so we set it directly to None, to trick the import system into doing this for us.
"""
Mods.__path__ = None  # type:  ignore

# This is essentially an extra version of sys.modules which we swap in while legacy compat is active
# When we exit compat, we'll move any new imports under `Mods` into this, since we don't want to
# keep them around for normal mods
legacy_modules: dict[str, ModuleType] = {
    "unrealsdk": old_unrealsdk,
    "Mods": Mods,
    "Mods.ModMenu": ModMenu,
}


@contextmanager
def legacy_compat() -> Iterator[None]:
    """Context manager which enables legacy SDK import compatibility while active."""
    if KILL_SWITCH:
        warnings.warn(
            "Legacy import compatibility has been removed.",
            DeprecationWarning,
            stacklevel=3,
        )
        yield
        return

    warnings.warn(
        "Using deprecated legacy import compatibility.",
        DeprecationWarning,
        stacklevel=3,
    )

    # Backup any current modules with the same name as a legacy one
    overwritten_modules = {name: mod for name, mod in sys.modules.items() if name in legacy_modules}
    # Overwrite with legacy modules
    sys.modules |= legacy_modules

    # Extra hack: Add the `Game.GetCurrent` alias to the actual class here
    # We can't easily create a separate enum class with the alias, since `Game` isn't inheritable,
    # and since separate identical enum classes still don't compare equal.
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
