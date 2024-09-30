import inspect
import warnings
from functools import wraps
from types import ModuleType
from typing import Any

from mods_base import Mod

from .decorators import NetworkFunction

MOD_NETWORK_FUNCTIONS_ATTR = "network_functions"


def bind_all_network_functions(obj: object, identifier_extension: str | None = None) -> None:
    """
    Binds all network functions on the given object, replacing the instance vars.

    Equivalent to the following, for all hooks on the object:
        obj.some_func = obj.some_func.bind(obj, identifier_extension)

    Args:
        obj: The object to bind to.
        identifier_extension: If not None, extends the hook identifier with the given string. You
                              You must provide different extensions if you intend to enable multiple
                              hooks on different instances at the same time, otherwise their
                              identifiers will conflict.
    """
    for name, value in inspect.getmembers(obj):
        if isinstance(value, NetworkFunction):
            setattr(obj, name, value.bind(obj, identifier_extension))


def scan_for_network_functions(
    module: ModuleType | None,
    mod: Mod | None,
    identifier_extension: str | None = None,
) -> list[NetworkFunction[Any, Any]]:
    """
    Scans for network functions in a mod and it's module.

    Args:
        module: The module to scan for globals is, or None to not scan.
        mod: The mod to scan for methods in, or None to not scan.
        identifier_extension: The identifier extension to use for any bound methods.
    Returns:
        The found list of network functions.
    """
    network_functions: list[NetworkFunction[Any, Any]] = []

    if module is not None:
        network_functions.extend(
            value for _, value in inspect.getmembers(module) if isinstance(value, NetworkFunction)
        )

    if mod is not None:
        for name, value in inspect.getmembers(mod):
            if isinstance(value, NetworkFunction):
                bound_func = value.bind(mod, identifier_extension)

                setattr(mod, name, bound_func)
                network_functions.append(bound_func)

    if not network_functions:
        warnings.warn(
            "Didn't find any network functions - do you actually need this call?",
            stacklevel=3,
        )

    return network_functions


def add_network_enable_disable_wrappers(mod: Mod) -> None:
    """
    Wraps the given mod's on_enable and on_disable to enable/disable network functions.

    Args:
        mod: The mod to add the enable/disable wrappers to.
    """

    def get_network_funcs() -> list[NetworkFunction[Any, Any]]:
        return getattr(mod, MOD_NETWORK_FUNCTIONS_ATTR, [])

    # Enable
    old_on_enable = mod.on_enable

    def enable() -> None:
        for func in get_network_funcs():
            func.enable()
        if old_on_enable is not None:
            old_on_enable()

    mod.on_enable = enable if old_on_enable is None else wraps(old_on_enable)(enable)

    # Disable
    old_on_disable = mod.on_disable

    def disable() -> None:
        for func in get_network_funcs():
            func.disable()
        if old_on_disable is not None:
            old_on_disable()

    mod.on_disable = disable if old_on_disable is None else wraps(old_on_disable)(disable)


def add_network_functions(
    mod: Mod,
    network_functions: list[NetworkFunction[Any, Any]] | None = None,
    *,
    identifier_extension: str | None = None,
    scan_module: bool = True,
    scan_methods: bool = True,
) -> Mod:
    """
    Factory to find and add network functions to a mod, and auto enable/disable them as needed.

    Intended to be used alongside the mod factory:
        mod = build_mod()
        add_network_functions(mod)

    Scans for both network functions in the same module scope and those defined as methods on the
    mod object. Replaces the instance variables of methods with ones bound to the specific mod'
    object, as in bind_all_network_functions.

    All found network functions are added to a 'mod.network_functions' list. Will throw an exception
    if this field already exists and is set to a value other than an empty list.

    Args:
        mod: The mod to add to.
        network_functions: The functions to add. If given, does not scan for any methods.
        identifier_extension: Used to extend the network identifier of any methods when binding them
                              to the mod. For standard use, where your mod is a singleton, you
                              generally won't need to set this.
        scan_module: If true, scans the module scope for network functions.
        scan_methods: If true, scans for network functions defined as methods on the mod object.
    Returns:
        The same mod object which was passed to this function.
    """
    if (val := getattr(mod, MOD_NETWORK_FUNCTIONS_ATTR, [])) != []:
        raise ValueError(f"Mod already has a value in 'network_functions': {val!r}")

    if network_functions is None:
        module: ModuleType | None = None
        if scan_module:
            module = inspect.getmodule(inspect.stack()[1].frame)
            if module is None:
                raise ValueError(
                    "Unable to find calling module when using add_network_functions factory!",
                )

        network_functions = scan_for_network_functions(
            module,
            mod if scan_methods else None,
            identifier_extension,
        )

    setattr(mod, MOD_NETWORK_FUNCTIONS_ATTR, network_functions)
    add_network_enable_disable_wrappers(mod)

    # If already enabled, (due to auto enable in the build mod call), also enable each function
    if mod.is_enabled:
        for func in network_functions:
            func.enable()

    return mod
