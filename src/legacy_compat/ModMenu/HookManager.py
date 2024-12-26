# ruff: noqa: N802, N803, D102, D103, N999

from __future__ import annotations

import functools
import weakref
from collections.abc import Callable
from inspect import Parameter, signature
from typing import Any

from legacy_compat import unrealsdk as old_unrealsdk

__all__: tuple[str, ...] = (
    "AnyHook",
    "Hook",
    "HookFunction",
    "HookMethod",
    "RegisterHooks",
    "RemoveHooks",
)


type HookFunction = Callable[
    [old_unrealsdk.UObject, old_unrealsdk.UFunction, old_unrealsdk.FStruct],
    bool | None,
]
type HookMethod = Callable[
    [Any, old_unrealsdk.UObject, old_unrealsdk.UFunction, old_unrealsdk.FStruct],
    bool | None,
]
type AnyHook = HookFunction | HookMethod


def Hook(target: str, name: str = "{0}.{1}") -> Callable[[AnyHook], AnyHook]:
    def apply_hook(function: AnyHook) -> AnyHook:
        params = signature(function).parameters
        is_method = len(params) == 4  # noqa: PLR2004

        hook_targets: set[str] | None = getattr(function, "HookTargets", None)
        if hook_targets is None:
            param_exception = ValueError(
                "Hook functions must have the signature"
                " ([self,] caller: unrealsdk.UObject, function: unrealsdk.UFunction, params:"
                " unrealsdk.FStruct)",
            )

            param_list = list(params.values())
            if is_method:
                del param_list[0]
            elif len(param_list) != 3:  # noqa: PLR2004
                raise param_exception
            for param in param_list:
                if Parameter.POSITIONAL_ONLY != param.kind != Parameter.POSITIONAL_OR_KEYWORD:
                    raise param_exception

            function.HookName = (  # type: ignore
                name
                if is_method
                else name.format(f"{function.__module__}.{function.__qualname__}", id(function))
            )

            hook_targets = set()
            function.HookTargets = hook_targets  # type: ignore

        hook_targets.add(target)

        if not is_method:
            old_unrealsdk.RunHook(target, function.HookName, function)  # type: ignore

        return function

    return apply_hook


def _create_method_wrapper(
    obj_ref: weakref.ReferenceType[object],
    obj_function: HookMethod,
) -> HookFunction:
    @functools.wraps(obj_function)
    def method_wrapper(
        caller: old_unrealsdk.UObject,
        function: old_unrealsdk.UFunction,
        params: old_unrealsdk.FStruct,
    ) -> Any:
        obj = obj_ref()
        method = obj_function.__get__(obj, type(obj))
        return method(caller, function, params)

    return method_wrapper


def RegisterHooks(obj: object) -> None:
    obj_ref = weakref.ref(obj, RemoveHooks)

    for attribute_name, function in type(obj).__dict__.items():
        if not callable(function):
            continue

        hook_targets = getattr(function, "HookTargets", None)
        if hook_targets is None or len(signature(function).parameters) != 4:  # noqa: PLR2004
            continue

        method_wrapper = _create_method_wrapper(obj_ref, function)  # type: ignore
        setattr(obj, attribute_name, method_wrapper)

        method_wrapper.HookName = function.HookName.format(  # type: ignore
            f"{function.__module__}.{function.__qualname__}",
            id(obj),
        )

        for target in hook_targets:
            old_unrealsdk.RunHook(target, method_wrapper.HookName, method_wrapper)  # type: ignore


def RemoveHooks(obj: object) -> None:
    for function in obj.__dict__.values():
        if not callable(function):
            continue

        hook_targets = getattr(function, "HookTargets", None)
        if hook_targets is None:
            continue

        for target in hook_targets:
            old_unrealsdk.RemoveHook(target, function.HookName)  # type: ignore
