# ruff: noqa: N802, N803, D102, D103, N999

import inspect
import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache, wraps
from typing import Any

from unrealsdk import (
    __version_info__,
    construct_object,
    find_all,
    find_class,
    find_object,
    load_package,
)
from unrealsdk.hooks import (
    Block,
    Type,
    add_hook,
    inject_next_call,  # pyright: ignore[reportDeprecated]
    log_all_calls,
    remove_hook,
)
from unrealsdk.unreal import (
    BoundFunction,
    UArrayProperty,
    UBoolProperty,
    UByteProperty,
    UClass,
    UClassProperty,
    UComponentProperty,
    UDelegateProperty,
    UFloatProperty,
    UFunction,
    UInterfaceProperty,
    UIntProperty,
    UNameProperty,
    UObject,
    UObjectProperty,
    UProperty,
    UStrProperty,
    UStruct,
    UStructProperty,
    WrappedArray,
    WrappedStruct,
)

from legacy_compat import compat_handlers, legacy_compat
from mods_base import ENGINE

# This is mutable so mod menu can add to it
__all__: list[str] = [
    "CallPostEdit",
    "ConstructObject",
    "DoInjectedCallNext",
    "FArray",
    "FScriptInterface",
    "FStruct",
    "FindAll",
    "FindClass",
    "FindObject",
    "GetEngine",
    "GetVersion",
    "KeepAlive",
    "LoadPackage",
    "Log",
    "LogAllCalls",
    "RegisterHook",
    "RemoveHook",
    "RunHook",
    "UClass",
    "UFunction",
    "UObject",
    "UPackage",
    "UStruct",
]

FStruct = WrappedStruct
FArray = WrappedArray
UPackage = UObject


# There is no longer an equivalent of this type, but we need to keep something around, both for
# isinstance checks and for something to return
@dataclass
class FScriptInterface:
    ObjectPointer: UObject | None


Log = print


def GetVersion() -> tuple[int, int, int]:
    caller = inspect.stack()[1]

    # Rougelands does a weird version check by adding strings and converting that to an int
    # [(0, 7, 11) -> "0711" -> 711] > [(1, 0, 0) -> "100" -> 100]
    # Give it it's own fake version to make the check succeed
    if caller.filename.endswith("RoguelandsGamemode\\__init__.py") and caller.function == "Enable":
        return (0, 9999, 9999)

    return __version_info__


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


def FindAll(InStr: str, IncludeSubclasses: bool = False) -> list[UObject]:
    return list(find_all(InStr, exact=not IncludeSubclasses))


def GetEngine() -> UObject:
    return ENGINE


def ConstructObject(
    Class: UClass | str,
    Outer: UObject | None = ENGINE,
    Name: str = "None",
    SetFlags: int = 1,
    InternalSetFlags: int = 0,  # noqa: ARG001
    Template: UObject | None = None,
    Error: None = None,  # noqa: ARG001
    InstanceGraph: None = None,  # noqa: ARG001
    bAssumeTemplateIsArchetype: int = 0,  # noqa: ARG001
) -> UObject | None:
    try:
        return construct_object(Class, Outer, Name, SetFlags, Template)
    except RuntimeError:
        return None


type _SDKHook = Callable[[UObject, UFunction, FStruct], bool | None]


@cache
def _translate_hook_func_name(func_name: str) -> str:
    """
    Translates a legacy style hook name to a modern one.

    The legacy SDK used dots for every separator, while the modern one uses the proper object name,
    which typically replaces the last one with a colon.

    Args:
        func_name: The legacy hook name.
    Returns:
        The modern hook name.
    """
    split_idx = len(func_name)
    while True:
        # Find the rightmost dot
        split_idx = func_name.rfind(".", 0, split_idx)

        # If we couldn't find it, just use the original name
        if split_idx < 0:
            return func_name

        try:
            # See if we can find the object when replacing this dot with a colon
            obj = find_object("Function", func_name[:split_idx] + ":" + func_name[split_idx + 1 :])
            return obj._path_name()
        except ValueError:
            pass
        # Couldn't find it, the colon may have to be a step further left


_HOOK_BLACKLIST: set[tuple[str, str]] = {
    # These two are used to manually implement buttons in the option list. The options handling code
    # hardcodes some fixups for these instead, so suppress their hooks
    ("WillowGame.WillowScrollingList.OnClikEvent", "Commander"),
    ("WillowGame.WillowScrollingList.OnClikEvent", "LootRandomizer"),
    # This hook is used to fix the offline mode say crash - which is something included in unrealsdk
    # itself now. Since the semantics of multiple blocking hooks on the same function changed (which
    # is not something we replicate), having both means trying to chat will print the message twice.
    ("WillowGame.TextChatGFxMovie.AddChatMessage", "Offline Helpers"),
}


def RegisterHook(func_name: str, hook_id: str, hook_function: _SDKHook, /) -> None:
    if (func_name, hook_id) in _HOOK_BLACKLIST:
        return

    @wraps(hook_function)
    def translated_hook(
        obj: UObject,
        args: WrappedStruct,
        _ret: Any,
        func: BoundFunction,
    ) -> type[Block] | None:
        with legacy_compat():
            return Block if not hook_function(obj, func.func, args) else None

    add_hook(
        _translate_hook_func_name(func_name),
        Type.PRE,
        f"{__name__}:{hook_id}",
        translated_hook,
    )


def RemoveHook(func_name: str, hook_id: str, /) -> None:
    remove_hook(_translate_hook_func_name(func_name), Type.PRE, f"{__name__}:{hook_id}")


def RunHook(func_name: str, hook_id: str, hook_function: _SDKHook, /) -> None:
    RemoveHook(func_name, hook_id)
    RegisterHook(func_name, hook_id, hook_function)


def DoInjectedCallNext() -> None:
    # We're changing behaviour here
    # A lot of people assumed calling this would mean the next time you called an unreal function,
    # it would skip hooks - the sdk itself kind of seemed to have assumed as much
    # However, in truth, any call from Python to unreal skipped hooks, so calling it actually
    # skipped the *second* unreal function call.
    # Since this was basically never useful, try change the behaviour to what people assumed
    inject_next_call()  # pyright: ignore[reportDeprecated]


def LogAllCalls(should_log: bool, /) -> None:
    log_all_calls(should_log)


def CallPostEdit(_: bool, /) -> None:
    # Never really useful and no way to replicate
    pass


def LoadPackage(filename: str, flags: int = 0, force: bool = False) -> None:  # noqa: ARG001
    load_package(filename, flags)


def KeepAlive(obj: UObject, /) -> None:
    # Use legacy compat to be sure we have `ObjectFlags.A`
    with legacy_compat():
        # Don't think this loop is strictly necessary - the parent objects should stay loaded since
        # they're referenced via Outer - but it's replicating the old code
        iter_obj: UObject | None = obj
        while iter_obj is not None:
            iter_obj.ObjectFlags.A |= 0x4000  # type: ignore
            iter_obj = iter_obj.Outer


# ==================================================================================================
# Compatibility methods wrappers

"""
There are a number of things we're fixing with these.

Property Access:
- The legacy sdk had you set structs via a tuple of their values in sequence, we need to convert
  them to a wrapped struct instance.
- The legacy sdk returned None instead of throwing an attribute error when a field didn't exist.
- The legacy sdk had interface properties return an FScriptInterface struct, but since you only ever
  accessed the object, the new sdk just returns it directly. We need to return the struct instead.
- In the legacy sdk, name properties did not include the number when converted to a string, which we
  need to strip out.

UObject:
- The `ObjectFlags` field on objects used to be split into the upper and lower 32 bits (B and A
  respectively), new sdk returns a single 64 bit int. Return a proxy object instead.
- The `Name` field is also a name property, so needs have the suffix stripped as above.
- In the legacy sdk the __repr__ of objects was just kind of wrong, but we need to replicate it.

BoundFunction:
- The legacy sdk treated all out params as be optional, even if they weren't actually.
- The new sdk always returns Ellipsis for a void function, meaning a void function with out params
  returns an extra value compared to the legacy one.
"""

_default_object_getattr = UObject.__getattr__
_default_object_getattribute = UObject.__getattribute__
_default_object_setattr = UObject.__setattr__
_default_object_repr = UObject.__repr__

_default_struct_getattr = WrappedStruct.__getattr__
_default_struct_setattr = WrappedStruct.__setattr__

# Array looks a little weird since it's generic, just remember WrappedArray[Any] == WrappedArray
_default_array_getitem = WrappedArray[Any].__getitem__
_default_array_setitem = WrappedArray[Any].__setitem__

_default_func_call = BoundFunction.__call__


def _convert_struct_tuple_if_required(
    prop: UProperty,
    value: Any,
    _ignore_array_dim: bool = False,
) -> Any:
    """
    Convert any tuple-based structs in the given value into Wrapped Structs.

    Args:
        prop: The property being set.
        value: The value it's getting set to.
    Returns:
        The possibly converted value.
    """

    # If it's a fixed array of structs, need to convert each inner value
    if not _ignore_array_dim and prop.ArrayDim > 1 and isinstance(prop, UStructProperty):
        return tuple(
            _convert_struct_tuple_if_required(prop, inner_val, _ignore_array_dim=True)
            for inner_val in value  # type: ignore
        )

    # If it's a struct being set as a tuple directly
    if isinstance(prop, UStructProperty) and isinstance(value, tuple):
        return WrappedStruct(
            prop.Struct,
            *(
                _convert_struct_tuple_if_required(inner_prop, inner_val)
                for inner_prop, inner_val in zip(prop.Struct._properties(), value, strict=False)  # type: ignore
            ),
        )

    # If it's an array of structs, need to convert each value
    if isinstance(prop, UArrayProperty) and isinstance(prop.Inner, UStructProperty):
        seq_value: Sequence[Any] = value

        return tuple(
            _convert_struct_tuple_if_required(prop.Inner, inner_val)
            if isinstance(inner_val, tuple)
            else inner_val
            for inner_val in seq_value
        )

    return value


_RE_NAME_SUFFIX = re.compile(r"^(.+)_\d+$")


def _strip_name_property_suffix(name: str) -> str:
    """
    Tries to strip the numeric suffix from a name property.

    Args:
        name: The input name.
    Returns:
        The stripped name.
    """
    return match.group(1) if (match := _RE_NAME_SUFFIX.match(name)) else name


@wraps(UObject.__getattr__)
def _uobject_getattr(self: UObject, name: str) -> Any:
    try:
        prop = self.Class._find(name)
    except ValueError:
        return None

    value = self._get_field(prop)

    match prop:
        case UInterfaceProperty():
            return FScriptInterface(value)
        case UNameProperty():
            return _strip_name_property_suffix(value)
        case _:
            return value


@dataclass
class _ObjectFlagsProxy:
    _obj: UObject

    @property
    def A(self) -> int:
        flags = _default_object_getattribute(self._obj, "ObjectFlags")
        return flags & 0xFFFFFFFF

    @A.setter
    def A(self, val: int) -> None:
        flags = _default_object_getattribute(self._obj, "ObjectFlags")
        self._obj.ObjectFlags = (val & 0xFFFFFFFF) | (flags & ~0xFFFFFFFF)

    @property
    def B(self) -> int:
        flags = _default_object_getattribute(self._obj, "ObjectFlags")
        return flags >> 32

    @B.setter
    def B(self, val: int) -> None:
        flags = _default_object_getattribute(self._obj, "ObjectFlags")
        self._obj.ObjectFlags = (flags & 0xFFFFFFFF) | (val << 32)

    # This also ensures the setattr works properly, since it'll just cast to int
    def __int__(self) -> int:
        return _default_object_getattribute(self._obj, "ObjectFlags")


# Because we want to overwrite exiting fields, we have to use getattribute over getattr
@wraps(UObject.__getattribute__)
def _uobject_getattribute(self: UObject, name: str) -> Any:
    match name:
        case "ObjectFlags":
            return _ObjectFlagsProxy(self)
        case "Name":
            return _strip_name_property_suffix(_default_object_getattribute(self, "Name"))
        case _:
            return _default_object_getattribute(self, name)


@wraps(UObject.__setattr__)
def _uobject_setattr(self: UObject, name: str, value: Any) -> None:
    try:
        prop = self.Class._find_prop(name)
    except ValueError:
        _default_object_setattr(self, name, value)
        return

    _default_object_setattr(self, name, _convert_struct_tuple_if_required(prop, value))


@wraps(UObject.__repr__)
def _uobject_repr(self: UObject) -> str:
    if self is None or self.Class is None:  # type: ignore
        return "(null)"

    current = self
    output = f"{self.Name}"
    while current := current.Outer:
        output = f"{current.Name}.{output}"

    return f"{self.Class.Name} {output}"


@wraps(WrappedStruct.__getattr__)
def _struct_getattr(self: WrappedStruct, name: str) -> Any:
    try:
        prop = self._type._find(name)
    except ValueError:
        return None

    value = self._get_field(prop)

    match prop:
        case UInterfaceProperty():
            return FScriptInterface(value)
        case UNameProperty():
            return _strip_name_property_suffix(value)
        case _:
            return value


@wraps(WrappedStruct.__setattr__)
def _struct_setattr(self: WrappedStruct, name: str, value: Any) -> None:
    try:
        prop = self._type._find_prop(name)
    except ValueError:
        _default_struct_setattr(self, name, value)
        return

    _default_struct_setattr(self, name, _convert_struct_tuple_if_required(prop, value))


@wraps(WrappedArray[Any].__getitem__)
def _array_getitem[T](self: WrappedArray[T], idx: int | slice) -> T | list[T]:
    value = _default_array_getitem(self, idx)

    match self._type:
        case UInterfaceProperty():
            if isinstance(idx, slice):
                val_seq: Sequence[T] = value  # type: ignore
                return [FScriptInterface(x) for x in val_seq]  # type: ignore

            return FScriptInterface(value)  # type: ignore
        case UNameProperty():
            if isinstance(idx, slice):
                val_seq: Sequence[T] = value  # type: ignore
                return [_strip_name_property_suffix(x) for x in val_seq]  # type: ignore

            return _strip_name_property_suffix(value)  # type: ignore

            return _strip_name_property_suffix(value)
        case _:
            return value


@wraps(WrappedArray[Any].__setitem__)
def _array_setitem[T](self: WrappedArray[T], idx: int | slice, value: T | Sequence[T]) -> None:
    if isinstance(idx, slice):
        val_seq: Sequence[T] = value  # type: ignore
        _default_array_setitem(
            self,
            idx,
            tuple(
                _convert_struct_tuple_if_required(self._type, inner_val) for inner_val in val_seq
            ),
        )
    else:
        _default_array_setitem(
            self,
            idx,
            _convert_struct_tuple_if_required(self._type, value),
        )


def _get_default_value_for_prop(prop: UProperty) -> Any:
    """
    Gets the default value to use for a required property if it wasn't given.

    Args:
        prop: The property to get the default value of.
    Returns:
        The default value.
    """
    match prop:
        case UArrayProperty():
            return ()
        case UBoolProperty():
            return False
        case UByteProperty() | UFloatProperty() | UIntProperty():
            return 0
        case (
            UClassProperty()
            | UComponentProperty()
            | UDelegateProperty()
            | UInterfaceProperty()
            | UObjectProperty()
        ):
            return None
        case UNameProperty() | UStrProperty():
            return ""
        case UStructProperty():
            return WrappedStruct(prop.Struct)
        case _:
            raise RuntimeError(
                f"Wasn't given value for required arg {prop}, and couldn't find default"
                f" value to keep legacy compatibility.",
            )


@wraps(BoundFunction.__call__)
def _boundfunc_call(self: BoundFunction, *args: Any, **kwargs: Any) -> Any:
    # If we have no out params and no struct properties, can fall back to the default
    if not any(
        (prop.PropertyFlags & 0x100) != 0  # UProperty::PROP_FLAG_OUT
        or isinstance(prop, UStructProperty)
        for prop in self.func._properties()
    ):
        return _default_func_call(self, *args, **kwargs)

    # Otherwise parsing args is quite annoying, basically have to replicate the C++ code exactly

    mutable_args = list(args)
    # Since we're comparing FNames, kwargs are supposed to be case insensitive, but in Python
    # they're just normal strings
    lower_kwargs = {k.lower(): k for k in kwargs}

    seen_return = False
    for idx, prop in enumerate(self.func._properties()):
        if (prop.PropertyFlags & 0x80) == 0:  # UProperty::PROP_FLAG_PARAM
            continue
        if (prop.PropertyFlags & 0x400) != 0 and not seen_return:  # UProperty::PROP_FLAG_RETURN
            seen_return = True
            continue

        if idx < len(mutable_args):
            mutable_args[idx] = _convert_struct_tuple_if_required(prop, mutable_args[idx])
            continue

        if (key := lower_kwargs.get(prop.Name.lower(), ...)) is not ...:
            kwargs[key] = _convert_struct_tuple_if_required(prop, kwargs[key])
            continue

        # If we don't have a value for this param, and it's a required out param
        # UProperty::PROP_FLAG_OPTIONAL = 0x10
        # UProperty::PROP_FLAG_OUT = 0x100
        if (prop.PropertyFlags & 0x110) == 0x100:  # noqa: PLR2004
            # Give it a default value
            mutable_args.insert(idx, _get_default_value_for_prop(prop))

        # No need to do any sanity checking on args since the default version will do that

    ret = _default_func_call(self, *mutable_args, **kwargs)
    if isinstance(ret, tuple) and ret[0] == Ellipsis:
        return tuple(ret[1:])  # type: ignore
    return ret  # type: ignore


# Brand new compatibility methods


@staticmethod
def _uobject_find_objects_containing(StringLookup: str, /) -> list[UObject]:
    # Not implementing this properly, it's only used in three places with two sets of args, so just
    # give them what they actually want
    if StringLookup == "WillowCoopGameInfo WillowGame.Default__WillowCoopGameInfo":
        return [find_class("WillowCoopGameInfo").ClassDefaultObject]
    if StringLookup == "FrontendGFxMovie ":
        return list(find_all("FrontendGFxMovie"))

    raise NotImplementedError


def _uobject_get_name(obj: UObject, /) -> str:
    return obj.Name


@staticmethod
def _uobject_path_name(obj: UObject, /) -> str:
    return obj._path_name()


def _ustructproperty_get_struct(self: UStructProperty) -> UStruct:
    return self.Struct


def _wrapped_struct_structType_getter(self: WrappedStruct) -> UStruct:
    return self._type


def _wrapped_struct_structType_setter(self: WrappedStruct, val: UStruct) -> None:
    self._type = val


_wrapped_struct_structType = property(  # noqa: N816
    _wrapped_struct_structType_getter,
    _wrapped_struct_structType_setter,
)


@contextmanager
def _unreal_method_compat_handler() -> Iterator[None]:
    UObject.__getattr__ = _uobject_getattr
    UObject.__getattribute__ = _uobject_getattribute
    UObject.__setattr__ = _uobject_setattr
    UObject.__repr__ = _uobject_repr

    WrappedStruct.__getattr__ = _struct_getattr
    WrappedStruct.__setattr__ = _struct_setattr

    WrappedArray.__getitem__ = _array_getitem  # type: ignore
    WrappedArray.__setitem__ = _array_setitem  # type: ignore
    BoundFunction.__call__ = _boundfunc_call

    UObject.FindObjectsContaining = _uobject_find_objects_containing  # type: ignore
    UObject.GetAddress = UObject._get_address  # type: ignore
    UObject.GetFullName = _uobject_repr  # type: ignore
    UObject.GetName = _uobject_get_name  # type: ignore
    UObject.PathName = _uobject_path_name  # type: ignore
    UStructProperty.GetStruct = _ustructproperty_get_struct  # type: ignore
    WrappedStruct.structType = _wrapped_struct_structType  # type: ignore

    try:
        yield
    finally:
        UObject.__getattr__ = _default_object_getattr
        UObject.__getattribute__ = _default_object_getattribute
        UObject.__setattr__ = _default_object_setattr
        UObject.__repr__ = _default_object_repr

        WrappedStruct.__getattr__ = _default_struct_getattr
        WrappedStruct.__setattr__ = _default_struct_setattr

        WrappedArray.__getitem__ = _default_array_getitem
        WrappedArray.__setitem__ = _default_array_setitem
        BoundFunction.__call__ = _default_func_call

        del UObject.FindObjectsContaining  # type: ignore
        del UObject.GetAddress  # type: ignore
        del UObject.GetFullName  # type: ignore
        del UObject.GetName  # type: ignore
        del UObject.PathName  # type: ignore
        del UStructProperty.GetStruct  # type: ignore
        del WrappedStruct.structType  # type: ignore


compat_handlers.append(_unreal_method_compat_handler)
