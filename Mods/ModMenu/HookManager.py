from __future__ import annotations

import unrealsdk
import functools
import weakref
from inspect import Parameter, signature
from typing import Any, Callable, Optional, Tuple, Union

__all__: Tuple[str, ...] = (
    "AnyHook",
    "Hook",
    "HookFunction",
    "HookMethod",
    "RegisterHooks",
    "RemoveHooks",
)


HookFunction = Callable[
    [unrealsdk.UObject, unrealsdk.UFunction, unrealsdk.FStruct],
    Optional[bool]
]
HookMethod = Callable[
    [Any, unrealsdk.UObject, unrealsdk.UFunction, unrealsdk.FStruct],
    Optional[bool]
]
AnyHook = Union[HookFunction, HookMethod]


def Hook(target: str, name: str = "{0}.{1}") -> Callable[[AnyHook], AnyHook]:
    """
    A decorator for functions that should be invoked in response to an Unreal Engine method's
    invokation.

    The function being decorated may be a standalone function, in which case its signature must
    match that of `unrealsdk.RegisterHook` functions:
        (caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct)

    Alternatively, the function may be an instance method of any object. In this case, the hook will
    be activated once `ModMenu.RegisterHooks(object)` has been called on the object. The signature
    of the method must match that of `unrealsdk.RegisterHook` functions, with the addition of `self`
    as the first parameter:
        (self, caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct)

    Upon invokation of the Unreal Engine method, the decorated function will be called. Its `caller`
    argument will contain the Unreal Engine object whose method was invoked, the `function` argument
    will contain the Unreal Engine function that was invoked, and the `params` argument will contain
    an `FStruct` with the arguments passed to the method.

    Args:
        target:
            A string representing the Unreal Engine method that should be hooked, in the format
            "<PackageName>.<ClassName>.<MethodName>".
        name:
            A string which, when paired with the hook target, uniquely identifies this hook within
            the SDK. By default, a name is generated using the function's module, qualified name,
            and `id()` (in the case of mod instance method hooks, the mod instance's `id()` is used
            instead).

            If a custom name is provided, it may be a simple string, or a format string with either
            one or two replacement tokens. Token `{0}` will contain the function's module name and
            qualified name, separated by a ".". Argument `{1}` will contain the `id()` of the
            function or mod instance.
    """
    def apply_hook(function: AnyHook) -> AnyHook:
        # If the function has four parameters, it should be a method.
        params = signature(function).parameters
        is_method = (len(params) == 4)

        # Retrieve the function's dictionary of targets. If it does not yet have one, we preform
        # initial setup on it now.
        hook_targets = getattr(function, "HookTargets", None)
        if hook_targets is None:
            param_exception = ValueError(
                "Hook functions must have the signature"
                " ([self,] caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct)"
            )

            # If the function is an instance method, create a mutable list of the parameters and
            # remove the `self` one, so we may check the remaining ones same as a non-method.
            param_list = list(params.values())
            if is_method:
                del param_list[0]
            # If the function has neither 4 nor 3 parameters, it is invalid.
            elif len(param_list) != 3:
                raise param_exception
            # If the functions parameters do not accept positional arguments, it is invalid.
            for param in param_list:
                if Parameter.POSITIONAL_ONLY != param.kind != Parameter.POSITIONAL_OR_KEYWORD:
                    raise param_exception

            # If the function is a method, store the name format string on it for formatting with
            # future instances. If it's a simple function, format its name for use now.
            function.HookName = name if is_method else name.format(  # type: ignore
                f"{function.__module__}.{function.__qualname__}", id(function)
            )

            # With the function now known as valid, create its set of targets.
            hook_targets = function.HookTargets = set()  # type: ignore

        hook_targets.add(target)

        if not is_method:
            unrealsdk.RunHook(target, function.HookName, function)  # type: ignore

        return function
    return apply_hook


def _create_method_wrapper(obj_ref: weakref.ReferenceType[object], obj_function: HookMethod) -> HookFunction:
    """Return a "true" function for the given bound method, passable to `unrealsdk.RegisterHook`."""
    @functools.wraps(obj_function)
    def method_wrapper(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> Any:
        obj = obj_ref()
        method = obj_function.__get__(obj, type(obj))  # type: ignore
        return method(caller, obj_function, params)
    return method_wrapper


def RegisterHooks(obj: object) -> None:
    """
    Registers all `@Hook` decorated methods for the object. Said methods will subsequently be called
    in response to the hooked Unreal Engine methods.

    Args:
        obj: The object for which to register method hooks.
    """

    # Create a weak reference to the object which we may use in attributes on it without creating
    # cyclical references. Before destruction, `RemoveHooks` should be called on the object to
    # ensure there are no remaining hooks that reference it.
    obj_ref = weakref.ref(obj, RemoveHooks)

    # Iterate over each attribute on the object's class that contains a function.
    for attribute_name, function in type(obj).__dict__.items():
        if not callable(function):
            continue

        # Attempt to get the set of hook targets from the function. If it doesn't have one, or if
        # its signature doesn't have 4 parameters, it is not a hook method.
        hook_targets = getattr(function, "HookTargets", None)
        if hook_targets is None or len(signature(function).parameters) != 4:
            continue

        # Create a wrapper to replace the descriptor of the attribute, "binding" the function to the
        # mod's weak reference, in a function that can be passed to `unrealsdk.RunHook`.
        method_wrapper = _create_method_wrapper(obj_ref, function)
        setattr(obj, attribute_name, method_wrapper)

        # Format the provided hook name.
        method_wrapper.HookName = function.HookName.format(  # type: ignore
            f"{function.__module__}.{function.__qualname__}", id(obj)
        )

        for target in hook_targets:
            unrealsdk.RunHook(target, method_wrapper.HookName, method_wrapper)  # type: ignore


def RemoveHooks(obj: object) -> None:
    """
    Unregisters all `@Hook` decorated methods for the object. Said methods will no longer be called
    in response to the hooked Unreal Engine methods.

    Args:
        obj: The object for which to unregister method hooks.
    """
    for function in obj.__dict__.values():
        if not callable(function):
            continue

        hook_targets = getattr(function, "HookTargets", None)
        if hook_targets is None:
            continue

        for target in hook_targets:
            unrealsdk.RemoveHook(target, function.HookName)
