# ruff: noqa: N802, N803, D102, D103, N999

import warnings
from contextlib import suppress
from functools import wraps
from typing import Any

from mods_base import ENGINE
from unrealsdk import find_class, find_object
from unrealsdk.unreal import UClass, UFunction, UObject, UStructProperty, WrappedStruct

__all__: tuple[str, ...] = (
    "FindObject",
    "Log",
    "UClass",
    "UFunction",
    "UObject",
)

Log = print


def FindObject(Class: str | UClass, ObjectFullName: str, /) -> UObject | None:
    try:
        return find_object(Class, ObjectFullName)
    except ValueError:
        return None


def FindClass(ClassName: str, Lookup: bool = False) -> UClass | None:  # noqa: ARG001
    try:
        return find_class(ClassName, False)
    except ValueError:
        return None


def GetEngine() -> UObject:
    return ENGINE


# The legacy SDK had you set structs via a tuple of their values in sequence, we need to convert
# them to a wrapped struct instance
_default_object_setattr = UObject.__setattr__
_default_struct_setattr = WrappedStruct.__setattr__


@wraps(UObject.__setattr__)
def _object_setattr(self: UObject, name: str, value: Any) -> None:
    if isinstance(value, tuple):
        with suppress(ValueError):
            prop = self.Class._find_prop(name)
            if isinstance(prop, UStructProperty):
                warnings.warn(
                    "Setting struct properties using tuples is deprecated. Use"
                    " unrealsdk.make_tuple(), or WrappedStruct directly.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                value = WrappedStruct(prop.Struct, *value)
    _default_object_setattr(self, name, value)


@wraps(WrappedStruct.__setattr__)
def _struct_setattr(self: WrappedStruct, name: str, value: Any) -> None:
    if isinstance(value, tuple):
        with suppress(ValueError):
            prop = self._type._find_prop(name)
            if isinstance(prop, UStructProperty):
                warnings.warn(
                    "Setting struct properties using tuples is deprecated. Use"
                    " unrealsdk.make_tuple(), or WrappedStruct directly.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                value = WrappedStruct(prop.Struct, *value)
    _default_struct_setattr(self, name, value)


# Unfortuantely we need to keep these active the entire time, since the calls happen at runtime
UObject.__setattr__ = _object_setattr
WrappedStruct.__setattr__ = _struct_setattr
