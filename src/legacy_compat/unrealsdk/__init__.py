# ruff: noqa: N802, N803, D102, D103, N999

from unrealsdk import find_object
from unrealsdk.unreal import UClass, UFunction, UObject

__all__: tuple[str, ...] = (
    "FindObject",
    "Log",
    "UClass",
    "UFunction",
    "UObject",
)

Log = print


def FindObject(Class: str | UClass, ObjectFullName: str, /) -> UObject:
    return find_object(Class, ObjectFullName)
