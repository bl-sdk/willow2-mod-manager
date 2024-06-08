# ruff: noqa: N802, N803, D102, D103, N999

from mods_base import ENGINE
from unrealsdk import find_class, find_object
from unrealsdk.unreal import UClass, UFunction, UObject

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
