# ruff: noqa: N802, N803, D102, D103, N999

import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
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
    "DoInjectedCallNext",
    "FArray",
    "FindAll",
    "FindClass",
    "FindObject",
    "FScriptInterface",
    "FStruct",
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


# There is no longer an equivalent of this type, but we need to keep something around for isinstance
# checks
class FScriptInterface:
    pass


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
) -> UObject:
    return construct_object(Class, Outer, Name, SetFlags, Template)


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


def RegisterHook(func_name: str, hook_id: str, hook_function: _SDKHook, /) -> None:
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
    # Don't think this loop is strictly necessary - the parent objects should stay loaded since
    # they're referenced via Outer - but it's replicating the old code
    iter_obj: UObject | None = obj
    while iter_obj is not None:
        iter_obj.ObjectFlags |= 0x4000
        iter_obj = iter_obj.Outer


# ==================================================================================================
# Compatibility methods wrappers

# There are a number of things we're fixing with these:
# 1. The legacy sdk had you set structs via a tuple of their values in sequence, we need to convert
#    them to a wrapped struct instance.
# 2. The legacy sdk had interface properties return an FScriptInterface struct, but since you only
#    ever accessed the object, the new sdk just returns it directly. This means old code already has
#    a UObject, but tries to access the `ObjectPointer` field, which we replace with a no-op.
# 3. The legacy sdk treated all out params as be optional, even if they weren't actually.
# 4. The new sdk always returns Ellipsis for a void function, meaning a void function with out
#    params returns an extra value compared to the legacy one.
_default_object_getattr = UObject.__getattr__
_default_object_setattr = UObject.__setattr__
_default_struct_setattr = WrappedStruct.__setattr__
_default_func_call = BoundFunction.__call__


@wraps(UObject.__getattr__)
def _object_getattr(self: UObject, name: str) -> Any:
    try:
        return _default_object_getattr(self, name)
    except AttributeError as ex:
        if name != "ObjectPointer":
            raise ex
        return self


@wraps(UObject.__setattr__)
def _object_setattr(self: UObject, name: str, value: Any) -> None:
    if isinstance(value, tuple):
        with suppress(ValueError):
            prop = self.Class._find_prop(name)
            if isinstance(prop, UStructProperty):
                value = WrappedStruct(prop.Struct, *value)
    _default_object_setattr(self, name, value)


@wraps(WrappedStruct.__setattr__)
def _struct_setattr(self: WrappedStruct, name: str, value: Any) -> None:
    if isinstance(value, tuple):
        with suppress(ValueError):
            prop = self._type._find_prop(name)
            if isinstance(prop, UStructProperty):
                value = WrappedStruct(prop.Struct, *value)
    _default_struct_setattr(self, name, value)


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
def _boundfunc_call(self: BoundFunction, *args: Any, **kwargs: Any) -> Any:  # noqa: C901 - just barely over and not worth splitting more
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
            if isinstance(prop, UStructProperty) and isinstance(value := mutable_args[idx], tuple):
                mutable_args[idx] = WrappedStruct(prop.Struct, *value)
            continue

        if (key := lower_kwargs.get(prop.Name.lower(), ...)) is not ...:
            if isinstance(prop, UStructProperty) and isinstance(value := kwargs[key], tuple):
                kwargs[key] = WrappedStruct(prop.Struct, *value)
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


def _ustructproperty_get_struct(self: UStructProperty) -> UStruct:
    return self.Struct


@staticmethod
def uobject_path_name(obj: UObject, /) -> str:
    return obj._path_name()


@contextmanager
def _unreal_method_compat_handler() -> Iterator[None]:
    UObject.__getattr__ = _object_getattr
    UObject.__setattr__ = _object_setattr
    BoundFunction.__call__ = _boundfunc_call
    WrappedStruct.__setattr__ = _struct_setattr

    UObject.FindObjectsContaining = _uobject_find_objects_containing  # type: ignore
    UStructProperty.GetStruct = _ustructproperty_get_struct  # type: ignore
    UObject.PathName = uobject_path_name  # type: ignore

    try:
        yield
    finally:
        UObject.__getattr__ = _default_object_getattr
        UObject.__setattr__ = _default_object_setattr
        BoundFunction.__call__ = _default_func_call
        WrappedStruct.__setattr__ = _default_struct_setattr

        del UObject.FindObjectsContaining  # type: ignore
        del UStructProperty.GetStruct  # type: ignore
        del UObject.PathName  # type: ignore


compat_handlers.append(_unreal_method_compat_handler)
