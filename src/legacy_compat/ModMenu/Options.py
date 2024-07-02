# ruff: noqa: N802, N803, D102, D103, N999

from abc import ABC, abstractmethod
from collections.abc import Sequence
from reprlib import recursive_repr
from typing import TYPE_CHECKING, Any

from mods_base import (
    JSON,
    BaseOption,
    BoolOption,
    HiddenOption,
    NestedOption,
    SliderOption,
    SpinnerOption,
    ValueOption,
)

from .DeprecationHelper import NameChangeMsg, PrintWarning

if TYPE_CHECKING:
    from ModObjects import SDKMod

__all__: tuple[str, ...] = (
    "Base",
    "Boolean",
    "Field",
    "Hidden",
    "Nested",
    "Slider",
    "Spinner",
    "Value",
)


class Base(ABC):
    Caption: str
    Description: str
    IsHidden: bool

    @abstractmethod
    def __init__(self, Caption: str, Description: str = "", *, IsHidden: bool = True) -> None:
        raise NotImplementedError


class Value[T](Base):
    CurrentValue: T
    StartingValue: T

    @abstractmethod
    def __init__(
        self,
        Caption: str,
        Description: str,
        StartingValue: T,
        *,
        IsHidden: bool = True,
    ) -> None:
        raise NotImplementedError


class Hidden[T](Value[T]):
    def __init__(
        self,
        Caption: str,
        Description: str = "",
        StartingValue: T = None,
        *,
        IsHidden: bool = True,  # noqa: ARG002
    ) -> None:
        self.Caption = Caption
        self.Description = Description
        self.CurrentValue = StartingValue
        self.StartingValue = StartingValue

    @property
    def IsHidden(self) -> bool:
        return True

    @IsHidden.setter
    def IsHidden(self, val: bool) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        pass

    @recursive_repr()
    def __repr__(self) -> str:
        return (
            f"Hidden("
            f"Caption={self.Caption!r},"
            f"Description={self.Description!r},"
            f"*,IsHidden={self.IsHidden!r}"
            f")"
        )


class Slider(Value[int]):
    CurrentValue: int
    StartingValue: int
    MinValue: int
    MaxValue: int
    Increment: int

    def __init__(
        self,
        Caption: str,
        Description: str,
        StartingValue: int,
        MinValue: int,
        MaxValue: int,
        Increment: int,
        *,
        IsHidden: bool = False,
    ) -> None:
        self.Caption = Caption
        self.Description = Description
        self.CurrentValue = StartingValue
        self.StartingValue = StartingValue
        self.MinValue = MinValue
        self.MaxValue = MaxValue
        self.Increment = Increment
        self.IsHidden = IsHidden

    @recursive_repr()
    def __repr__(self) -> str:
        return (
            f"Slider("
            f"Caption={self.Caption!r},"
            f"Description={self.Description!r},"
            f"CurrentValue={self.CurrentValue!r},"
            f"StartingValue={self.StartingValue!r},"
            f"MinValue={self.MinValue!r},"
            f"MaxValue={self.MaxValue!r},"
            f"Increment={self.Increment!r},"
            f"*,IsHidden={self.IsHidden!r}"
            f")"
        )


class Spinner(Value[str]):
    CurrentValue: str
    StartingValue: str
    Choices: Sequence[str]

    def __init__(
        self,
        Caption: str,
        Description: str,
        StartingValue: str | None = None,
        Choices: Sequence[str] | None = None,
        *,
        IsHidden: bool = False,
        StartingChoice: str | None = None,
    ) -> None:
        self.Caption = Caption
        self.Description = Description
        self.IsHidden = IsHidden

        if StartingValue is not None:
            self.StartingValue = StartingValue
            self.CurrentValue = StartingValue
        elif StartingChoice is not None:
            PrintWarning(NameChangeMsg("Spinner.StartingChoice", "Spinner.StartingValue"))
            self.StartingValue = StartingChoice
            self.CurrentValue = StartingChoice
        else:
            raise TypeError("__init__() missing 1 required positional argument: 'StartingValue'")

        if Choices is None:
            raise TypeError("__init__() missing 1 required positional argument: 'Choices'")
        self.Choices = Choices

        if self.StartingValue not in self.Choices:
            raise ValueError(
                f"Provided starting value '{self.StartingValue}' is not in the list of choices.",
            )

    @recursive_repr()
    def __repr__(self) -> str:
        return (
            f"Spinner("
            f"Caption={self.Caption!r},"
            f"Description={self.Description!r},"
            f"CurrentValue={self.CurrentValue!r},"
            f"StartingValue={self.StartingValue!r},"
            f"Choices={self.Choices!r},"
            f"*,IsHidden={self.IsHidden!r}"
            f")"
        )


class Boolean(Spinner, Value[bool]):  # pyright: ignore[reportGeneralTypeIssues]
    StartingValue: bool
    Choices: tuple[str, str]

    _current_value: bool

    def __init__(
        self,
        Caption: str,
        Description: str,
        StartingValue: bool,
        Choices: tuple[str, str] = ("Off", "On"),
        *,
        IsHidden: bool = False,
    ) -> None:
        self.Caption = Caption
        self.Description = Description
        self.StartingValue = StartingValue  # pyright: ignore[reportIncompatibleVariableOverride]
        self.IsHidden = IsHidden

        self.Choices = Choices  # pyright: ignore[reportIncompatibleVariableOverride]
        self.CurrentValue = StartingValue  # pyright: ignore[reportIncompatibleVariableOverride]

        if len(self.Choices) != 2:  # noqa: PLR2004
            raise ValueError(
                f"Invalid amount of choices passed to boolean option, expected 2 not"
                f" {len(self.Choices)}.",
            )

    @property
    def CurrentValue(self) -> bool:
        return self._current_value

    @CurrentValue.setter
    def CurrentValue(self, val: Any) -> None:
        if val in self.Choices:
            self._current_value = bool(self.Choices.index(val))
        else:
            self._current_value = bool(val)

    @recursive_repr()
    def __repr__(self) -> str:
        return (
            f"Boolean("
            f"Caption={self.Caption!r},"
            f"Description={self.Description!r},"
            f"CurrentValue={self.CurrentValue!r},"
            f"StartingValue={self.StartingValue!r},"
            f"Choices={self.Choices!r},"
            f"*,IsHidden={self.IsHidden!r}"
            f")"
        )


class Field(Base):
    pass


class Nested(Field):
    Children: Sequence[Base]

    def __init__(
        self,
        Caption: str,
        Description: str,
        Children: Sequence[Base],
        *,
        IsHidden: bool = False,
    ) -> None:
        self.Caption = Caption
        self.Description = Description
        self.Children = Children
        self.IsHidden = IsHidden

    @recursive_repr()
    def __repr__(self) -> str:
        return (
            f"Nested("
            f"Caption={self.Caption!r},"
            f"Description={self.Description!r},"
            f"Children={self.Children!r},"
            f"*,IsHidden={self.IsHidden!r}"
            f")"
        )


def convert_to_new_style_option(option: Base, mod: "SDKMod | None" = None) -> BaseOption:
    """
    Converts a legacy option to a new-style option.

    Args:
        option: The legacy option.
        mod: The legacy mod object to send change callbacks to.
    Returns:
        The new-style option.
    """

    def on_change[J: JSON](_: ValueOption[J], new_val: Any) -> None:
        if mod is not None:
            mod.ModOptionChanged(option, new_val)  # type: ignore
        option.CurrentValue = new_val  # type: ignore

    def create() -> BaseOption:
        match option:
            case Nested():
                return NestedOption(
                    option.Caption,
                    tuple(convert_to_new_style_option(opt, mod) for opt in option.Children),
                    description=option.Description,
                    is_hidden=option.IsHidden,
                )
            case Boolean():
                return BoolOption(
                    option.Caption,
                    option.CurrentValue,
                    option.Choices[1],
                    option.Choices[0],
                    description=option.Description,
                    is_hidden=option.IsHidden,
                    on_change=on_change,
                )
            case Spinner():
                return SpinnerOption(
                    option.Caption,
                    option.CurrentValue,
                    list(option.Choices),
                    description=option.Description,
                    is_hidden=option.IsHidden,
                    on_change=on_change,
                )
            case Slider():
                return SliderOption(
                    option.Caption,
                    option.CurrentValue,
                    option.MinValue,
                    option.MaxValue,
                    option.Increment,
                    description=option.Description,
                    is_hidden=option.IsHidden,
                    on_change=on_change,
                )
            case Hidden():
                hidden_option: Hidden[Any] = option
                return HiddenOption(
                    hidden_option.Caption,
                    hidden_option.CurrentValue,
                    description=hidden_option.Description,
                    on_change=on_change,
                )
            case _:
                raise TypeError(f"Unable to convert legacy option of type {type(option)}")

    new_option = create()
    if mod is not None:
        new_option.mod = mod.new_mod_obj
    return new_option
