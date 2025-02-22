import warnings
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from types import ModuleType

from mods_base.mod_list import base_mod

__all__: tuple[str, ...] = (
    "ENABLED",
    "__author__",
    "__version__",
    "__version_info__",
    "add_compat_module",
    "legacy_compat",
)

__version_info__: tuple[int, int] = (1, 4)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"

ENABLED: bool
compat_handlers: list[Callable[[], AbstractContextManager[None]]] = []


@contextmanager
def legacy_compat() -> Iterator[None]:
    """Context manager which enables legacy SDK compatibility while active."""
    if not ENABLED:
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

    # If we're in a recursive call, don't do anything, only let the outermost one handle it
    if legacy_compat.currently_active:  # type: ignore
        yield
        return

    try:
        legacy_compat.currently_active = True  # type: ignore
        with ExitStack() as stack:
            for handler in compat_handlers:
                stack.enter_context(handler())
            yield
    finally:
        legacy_compat.currently_active = False  # type: ignore


legacy_compat.currently_active = False  # type: ignore


def add_compat_module(name: str, module: ModuleType) -> None:  # pyright: ignore[reportRedeclaration]
    """
    Adds a custom compatibility module, which will be swapped in while legacy compat is active.

    Args:
        name: The name of the module to add. Must start with 'Mods.'.
        module: The module to add.
    """
    # Choose to define the disabled version up here, so the public interface is all in once place,
    # and then replace it lower down
    _ = module

    # Even though we're not actually going to do anything here, replicate the error for consistency
    if not name.startswith("Mods."):
        raise ValueError("Legacy compat modules must start with 'Mods.'")

    warnings.warn(
        "Legacy import compatibility has been removed.",
        DeprecationWarning,
        stacklevel=2,
    )


# Kill switch. May have to update this at some point if we decide to keep this around longer.
if base_mod.version.partition(" ")[0] not in {"3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"}:
    from unrealsdk import logging

    logging.warning("Legacy SDK Compatibility has been disabled")
    ENABLED = False  # pyright: ignore[reportConstantRedefinition]
else:
    import ctypes
    import sys
    import warnings
    from collections.abc import Iterator
    from contextlib import contextmanager
    from functools import wraps

    from unrealsdk.hooks import prevent_hooking_direct_calls
    from unrealsdk.unreal import notify_changes

    from mods_base import MODS_DIR

    from . import ModMenu
    from . import unrealsdk as old_unrealsdk
    from .meta_path_finder import LegacyCompatMetaPathFinder

    base_mod.components.append(base_mod.ComponentInfo("Legacy SDK Compat", __version__))

    ENABLED = True  # pyright: ignore[reportConstantRedefinition]
    compat_handlers.append(prevent_hooking_direct_calls)
    compat_handlers.append(notify_changes)

    """
    There are two parts to legacy SDK compatibility.

    The first is creating aliases and proxy objects for absolutely everything. While extensive, this
    is relatively simple. This is handled by the two `unrealsdk` and `ModMenu` submodules.

    The second more difficult part is dealing with imports. In the legacy SDK, ill advisedly, the
    `Mods` folder was part of the packaging, `mods/xyz` was packaged under `Mods.xyz`. This is no
    longer the case in this version, it's just under a top level `xyz`. We can't trust users to
    extract legacy mods any differently to updated ones, so we need to redirect these imports
    automatically.
    """

    # First, create a fake mods module
    Mods = ModuleType("Mods")

    """
    To allow importing submodules at all, to convert the module into a package, we need to set
    __path__. But to what? This requires a bit of reading between the lines.

    > The find_spec() method of meta path finders is called with two or three arguments. The first
    > is the fully qualified name of the module being imported, for example foo.bar.baz. The second
    > argument is the path entries to use for the module search. For top-level modules, the second
    > argument is None, but for submodules or subpackages, the second argument is the value of the
    > parent package's __path__ attribute.

    When importing a submodule, it copies the value of the parent's __path__. When importing a top
    level module, it uses None. We want importing a submodule of Mods to actually import a top level
    module - so we set it directly to None, to trick the import system into doing this for us.
    """
    Mods.__path__ = None  # type:  ignore

    # This is needed for some mods
    Mods.__file__ = str(MODS_DIR)

    # This is essentially an extra version of sys.modules which we swap during legacy compat
    # When we exit compat, we'll move any new imports under `Mods` into this, since we don't want to
    # keep them around for normal mods
    legacy_modules: dict[str, ModuleType] = {
        "bl2sdk": old_unrealsdk,
        "unrealsdk": old_unrealsdk,
        "Mods": Mods,
        "Mods.ModManager": ModMenu.ModObjects,
        "Mods.ModMenu": ModMenu,
        "Mods.OptionManager": ModMenu.OptionManager,
        # Mod-specific compat
        # This normally points at an older version, we can point it at the current
        "Mods.UserFeedback.ctypes": ctypes,
    }

    @contextmanager
    def import_compat_handler() -> Iterator[None]:
        """Context manager to add the import compatibility."""
        # Backup any current modules with the same name as a legacy one
        overwritten_modules = {
            name: mod for name, mod in sys.modules.items() if name in legacy_modules
        }
        # Overwrite with legacy modules
        sys.modules |= legacy_modules

        # And add our import hook
        sys.meta_path.insert(0, LegacyCompatMetaPathFinder)

        try:
            yield
        finally:
            # Remove the import hook
            sys.meta_path.remove(LegacyCompatMetaPathFinder)

            # Move the legacy modules out of sys.modules back into our legacy dict
            for name in tuple(sys.modules.keys()):
                if name in legacy_modules or name.startswith("Mods."):
                    legacy_modules[name] = sys.modules.pop(name)
            # And add any overwritten modules back in
            sys.modules |= overwritten_modules

    compat_handlers.append(import_compat_handler)

    @wraps(add_compat_module)
    def add_compat_module(name: str, module: ModuleType) -> None:  # noqa: D103
        if not name.startswith("Mods."):
            raise ValueError("Legacy compat modules must start with 'Mods.'")

        if name in legacy_modules:
            raise ValueError(f"Legacy compat module '{name}' already exists!")

        legacy_modules[name] = module
