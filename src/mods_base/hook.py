import functools
import inspect
from collections.abc import Callable
from types import EllipsisType
from typing import Any, Literal, Protocol, Self, cast, overload, runtime_checkable

from unrealsdk.hooks import Block, Type, add_hook, has_hook, remove_hook
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

type HookBlockSignal = None | EllipsisType | Block | type[Block]

type AnyPreHook = (
    Callable[
        [UObject, WrappedStruct, Any, BoundFunction],
        HookBlockSignal | tuple[HookBlockSignal, Any],
    ]
    | Callable[
        [Any, UObject, WrappedStruct, Any, BoundFunction],
        HookBlockSignal | tuple[HookBlockSignal, Any],
    ]
)
type AnyPostHook = (
    Callable[[UObject, WrappedStruct, Any, BoundFunction], None]
    | Callable[[Any, UObject, WrappedStruct, Any, BoundFunction], None]
)


@runtime_checkable
class HookProtocol(Protocol):
    hook_funcs: list[tuple[str, Type]]
    hook_identifier: str

    obj_to_bind_hooks_to: Any | None = None

    def enable(self) -> None:
        """Enables all hooks this function is bound to."""
        raise NotImplementedError

    def disable(self) -> None:
        """Disables all hooks this function is bound to."""
        raise NotImplementedError

    def get_active_count(self) -> int:
        """
        Gets the amount of hooks this function is bound to which are active.

        Note this doesn't necessarily mean they're bound to this function.

        Returns:
            The number of active hooks.
        """
        raise NotImplementedError

    def bind(self, obj: Any) -> Self:
        """
        Binds this hook to a specific object - to be used if this function is a method.

        If this function is a method, this must be done before enabling the hook.

        Args:
            obj: The object to bind to.
        Return:
            A reference to this hook.
        """
        raise NotImplementedError

    @overload
    def __call__(
        self,
        obj: UObject,
        args: WrappedStruct,
        ret: Any,
        func: BoundFunction,
    ) -> HookBlockSignal | tuple[HookBlockSignal, Any]: ...

    @overload
    def __call__(
        self,
        bound_obj: Any,
        obj: UObject,
        args: WrappedStruct,
        ret: Any,
        func: BoundFunction,
    ) -> HookBlockSignal | tuple[HookBlockSignal, Any]: ...


def _hook_enable(self: HookProtocol) -> None:
    # Disable first, to make sure we always use the latest version when enabling
    _hook_disable(self)

    func = (
        self.__call__
        if self.obj_to_bind_hooks_to is None
        else functools.partial(self.__call__, self.obj_to_bind_hooks_to)
    )
    for hook_func, hook_type in self.hook_funcs:
        add_hook(hook_func, hook_type, self.hook_identifier, func)


def _hook_disable(self: HookProtocol) -> None:
    for hook_func, hook_type in self.hook_funcs:
        remove_hook(hook_func, hook_type, self.hook_identifier)


def _hook_get_active_count(self: HookProtocol) -> int:
    return sum(
        1
        for hook_func, hook_type in self.hook_funcs
        if has_hook(hook_func, hook_type, self.hook_identifier)
    )


def _hook_bind(self: HookProtocol, obj: Any) -> HookProtocol:
    self.obj_to_bind_hooks_to = obj
    return self


@overload
def hook(
    hook_func: str,
    hook_type: Literal[Type.PRE] = Type.PRE,
    *,
    auto_enable: bool = False,
) -> Callable[[AnyPreHook], HookProtocol]: ...


@overload
def hook(
    hook_func: str,
    hook_type: Literal[Type.POST, Type.POST_UNCONDITIONAL],
    *,
    auto_enable: bool = False,
) -> Callable[[AnyPostHook], HookProtocol]: ...


def hook(
    hook_func: str,
    hook_type: Type = Type.PRE,
    *,
    auto_enable: bool = False,
    hook_identifier: str | None = None,
) -> Callable[[AnyPreHook], HookProtocol] | Callable[[AnyPostHook], HookProtocol]:
    """
    Decorator to register a function as a hook.

    May be stacked on the same function multiple times - even with other decorators inbetween
    (assuming they follow the `__wrapped__` convention).

    When using multiple decorators, the outermost one should always be a hook, to give you access to
    the functions it adds, and to make sure hook autodetection can pick it up properly.

    Args:
        hook_func: The unrealscript function to hook.
        hook_type: What type of hook to add.
    Keyword Args:
        auto_enable: If true, enables the hook after registering it. Should only be set on the
                     outermost decorator.
        hook_identifier: If not None, specified a custom hook identifier. May only be set on the
                         innermost decorator. If None, generates one using the wrapped function's
                         module and qualified name.
    """

    def decorator(func: AnyPreHook | AnyPostHook) -> HookProtocol:
        if not isinstance(func, HookProtocol):
            func = cast(HookProtocol, func)

            # Check if this function is a wrapper of an existing hook, and if so copy it's data
            wrapped_func = func
            while (wrapped_func := getattr(wrapped_func, "__wrapped__", None)) is not None:
                if isinstance(wrapped_func, HookProtocol):
                    func.hook_funcs = wrapped_func.hook_funcs
                    func.hook_identifier = wrapped_func.hook_identifier
                    func.obj_to_bind_hooks_to = wrapped_func.obj_to_bind_hooks_to
                    break
            else:
                # Didn't find an existing hook, initialize our own data
                func.hook_funcs = []

                if hook_identifier is None:
                    # Don't want to add qualname to the protocol, but we know it must exist since
                    # it's actually a function
                    func_name = func.__qualname__  # type: ignore

                    module_name = (
                        "unknown_module"
                        if (module := inspect.getmodule(func)) is None
                        else module.__name__
                    )

                    func.hook_identifier = f"{__name__}:hook-id:{module_name}.{func_name}"
                else:
                    func.hook_identifier = hook_identifier

                func.obj_to_bind_hooks_to = None

            func.enable = _hook_enable.__get__(func, type(func))
            func.disable = _hook_disable.__get__(func, type(func))
            func.get_active_count = _hook_get_active_count.__get__(func, type(func))
            func.bind = _hook_bind.__get__(func, type(func))

        func.hook_funcs.append((hook_func, hook_type))

        if auto_enable:
            func.enable()

        return func

    return decorator
