import functools
import inspect
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Self, cast, overload

from unrealsdk.hooks import Block, Type, add_hook, has_hook, remove_hook
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

type HookBlockSignal = None | Block | type[Block]
type PreHookRet = HookBlockSignal | tuple[HookBlockSignal, Any]
type PostHookRet = None

type HookCallbackFunction[R: (PreHookRet, PostHookRet)] = Callable[
    [UObject, WrappedStruct, Any, BoundFunction],
    R,
]
type HookCallbackMethod[R: (PreHookRet, PostHookRet)] = Callable[
    [Any, UObject, WrappedStruct, Any, BoundFunction],
    R,
]


@dataclass
class HookType[R: (PreHookRet, PostHookRet) = PreHookRet | PostHookRet]:
    __wrapped__: Callable[[UObject, WrappedStruct, Any, BoundFunction], R]

    hook_identifier: str
    hook_funcs: list[tuple[str, Type]] = field(default_factory=list)

    def enable(self) -> None:
        """Enables all hooks this function is bound to."""
        # Disable first, to make sure we always use the latest version when enabling
        self.disable()

        for hook_func, hook_type in self.hook_funcs:
            add_hook(hook_func, hook_type, self.hook_identifier, self.__wrapped__)

    def disable(self) -> None:
        """Disables all hooks this function is bound to."""
        for hook_func, hook_type in self.hook_funcs:
            remove_hook(hook_func, hook_type, self.hook_identifier)

    def get_active_count(self) -> int:
        """
        Gets the amount of hooks this function is bound to which are active.

        Note this doesn't necessarily mean they're bound to this function.

        Returns:
            The number of active hooks.
        """
        return sum(
            1
            for hook_func, hook_type in self.hook_funcs
            if has_hook(hook_func, hook_type, self.hook_identifier)
        )

    def bind(self, obj: object, identifier_extension: str | None = None) -> Self:
        """
        Creates a new hook function bound to the given object.

        This must be called if the current hook wraps a method. You must only interact with the hook
        this returns, you may not enable the hook on this level, otherwise you will get exceptions
        for missing or misaligned of parameters.

        Generally you want to call this using:
            self.some_hook = self.some_hook.bind(self, identifier_extension)

        Args:
            obj: The object to bind to.
            identifier_extension: If not None, extends the hook identifier with the given string.
                                  You must provide different extensions if you intend to enable
                                  multiple hooks on different instances at the same time, otherwise
                                  their identifiers will conflict.
        Return:
            The new hook function.
        """
        return type(self)(
            self.__wrapped__.__get__(obj, type(obj)),
            (
                self.hook_identifier
                if identifier_extension is None
                else f"{self.hook_identifier}:{identifier_extension}"
            ),
            self.hook_funcs,
        )

    def __call__(
        self,
        obj: UObject,
        args: WrappedStruct,
        ret: Any,
        func: BoundFunction,
    ) -> R:
        """Calls the wrapped hook callback."""
        return self.__wrapped__(obj, args, ret, func)


@overload
def hook[R: (PreHookRet, PostHookRet)](
    hook_func: str,
    hook_type: Literal[Type.PRE] = Type.PRE,
    *,
    immediately_enable: bool = False,
) -> Callable[[HookCallbackFunction[R] | HookCallbackMethod[R]], HookType[R]]: ...


@overload
@warnings.deprecated(
    "The 'auto_enable' arg has been deprecated due to being misleading, you likely don't need it.",
)
def hook[R: (PreHookRet, PostHookRet)](
    hook_func: str,
    hook_type: Literal[Type.PRE] = Type.PRE,
    *,
    auto_enable: bool,
    immediately_enable: bool = False,
) -> Callable[[HookCallbackFunction[R] | HookCallbackMethod[R]], HookType[R]]: ...


@overload
def hook(
    hook_func: str,
    hook_type: Literal[Type.POST, Type.POST_UNCONDITIONAL],
    *,
    immediately_enable: bool = False,
) -> Callable[
    [HookCallbackFunction[PostHookRet] | HookCallbackMethod[PostHookRet]],
    HookType[PostHookRet],
]: ...


@overload
@warnings.deprecated(
    "The 'auto_enable' arg has been deprecated due to being misleading, you likely don't need it.",
)
def hook(
    hook_func: str,
    hook_type: Literal[Type.POST, Type.POST_UNCONDITIONAL],
    *,
    auto_enable: bool,
    immediately_enable: bool = False,
) -> Callable[
    [HookCallbackFunction[PostHookRet] | HookCallbackMethod[PostHookRet]],
    HookType[PostHookRet],
]: ...


def hook[R: (PreHookRet, PostHookRet)](  # noqa: D417 - deprecated arg
    hook_func: str,
    hook_type: Type = Type.PRE,
    *,
    auto_enable: bool | None = None,
    immediately_enable: bool = False,
    hook_identifier: str | None = None,
) -> Callable[[HookCallbackFunction[R] | HookCallbackMethod[R]], HookType[R]]:
    """
    Decorator to register a function as a hook.

    When used on a method, this essentially creates a factory. You MUST bind it to a specific
    instance before using it further - see `HookType.bind()` or `bind_all_hooks()`. This is done
    automatically on subclasses of `Mod`.

    May be stacked on the same function multiple times - even with other decorators inbetween
    (assuming they follow the `__wrapped__` convention).

    When using multiple decorators, the outermost one should always be a hook, to give you access to
    the functions it adds, and to make sure hook autodetection can pick it up properly.

    Args:
        hook_func: The unrealscript function to hook.
        hook_type: What type of hook to add.
    Keyword Args:
        immediately_enable: If true, enables the hook *immediately after registering it*. Useful for
                            test code and always-on libraries. DO NOT SET on hooks you expect to be
                            enabled/disabled when your mod is. Should only be set on the outermost
                            decorator.
        hook_identifier: If not None, specifies a custom hook identifier. May only be set on the
                         innermost decorator. If None, generates one using the wrapped function's
                         module and qualified name.
    """
    if auto_enable is not None:
        warnings.warn(
            "The 'auto_enable' arg has been deprecated due to being misleading, you likely don't"
            " need it. Hooks which are parts of your mod are always automatically enabled when the"
            " mod is, setting the arg would in fact enable them even when it wasn't.",
            DeprecationWarning,
            stacklevel=2,
        )
        immediately_enable = auto_enable
    del auto_enable

    def decorator(func: HookCallbackFunction[R] | HookCallbackMethod[R]) -> HookType[R]:
        # HACK: There's no way to tell if we've wrapped a method or a function  # noqa: FIX004
        #
        # At the point decorators run, they're all functions, just with an extra arg - but we can't
        # rely on any specific number of args or arg name.
        #
        # We also can't just wrap the function and see how it's called, since typically they're just
        # passed straight to the hook, we're more of a registering decorator than a wrapping one.
        #
        # Regardless of what type we have, we need to store it on the hook function object. Since we
        # can't at all tell between the two, we have to just store them in the same field, pretend
        # it's always a function, and just hope the user calls bind as appropriate.
        func = cast(HookCallbackFunction[R], func)

        hook: HookType[R]
        if isinstance(func, HookType):
            # If we're directly wrapping another hook, use it
            hook = func
        else:
            # Look to see if we wrapped another hook function inbetween somewhere
            wrapped_func = func
            while (wrapped_func := getattr(wrapped_func, "__wrapped__", None)) is not None:
                if isinstance(wrapped_func, HookType):
                    # The functions wrapping this hook might rely on it, we can't really reuse the
                    # same object, just copy it's identifier and funcs
                    hook = HookType(func, wrapped_func.hook_identifier, wrapped_func.hook_funcs)
                    functools.update_wrapper(hook, func)
                    break
            else:
                # There are no existing hooks, we're making the first one
                identifier: str
                if hook_identifier is None:
                    module_name = (
                        "unknown_module"
                        if (module := inspect.getmodule(func)) is None
                        else module.__name__
                    )
                    identifier = f"{__name__}:{module_name}:{func.__qualname__}"
                else:
                    identifier = hook_identifier

                hook = HookType(func, identifier)
                functools.update_wrapper(hook, func)

        # If we already have hooks, make sure we're not trying to redefine the identifier
        if hook.hook_funcs and hook_identifier is not None:
            warnings.warn(
                "Explicitly giving identifiers to outer hook decorators has no effect. Only set"
                " one on the innermost decorator.",
                stacklevel=3,
            )

        # Add this function
        hook.hook_funcs.append((hook_func, hook_type))

        if immediately_enable:
            hook.enable()
        return hook

    return decorator


def bind_all_hooks(obj: object, identifier_extension: str | None = None) -> None:
    """
    Binds all hooks on the given object, replacing the instance vars with their bound equivalents.

    Equivalent to the following, for all hooks on the object:
        obj.some_hook = obj.some_hook.bind(obj, identifier_extension)

    Args:
        obj: The object to bind to.
        identifier_extension: If not None, extends the hook identifier with the given string. You
                              You must provide different extensions if you intend to enable multiple
                              hooks on different instances at the same time, otherwise their
                              identifiers will conflict.
    """
    for name, value in inspect.getmembers(obj):
        if isinstance(value, HookType):
            setattr(obj, name, value.bind(obj, identifier_extension))
