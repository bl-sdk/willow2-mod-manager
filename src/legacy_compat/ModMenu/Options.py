# ruff: noqa: N802, N803, D102, D103, N999

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import KW_ONLY, dataclass
from reprlib import recursive_repr
from typing import TYPE_CHECKING, Any

from legacy_compat import legacy_compat
from mods_base import (
    JSON,
    BaseOption,
    BoolOption,
    ButtonOption,
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


# Some mods edit the options shown under a nested option. Create a proxy type which generates it's
# children lazily, so that these update without needing the option itself to be replaced.
@dataclass
class _NestedProxy(NestedOption):
    _: KW_ONLY
    legacy_option: Nested
    # Since we're using a custom type anyway, add a callback needed by some of the option fixups
    on_enter: Callable[["_NestedProxy"], None] | None = None

    @property
    def children(self) -> Sequence[BaseOption]:  # pyright: ignore[reportIncompatibleVariableOverride]
        if self.on_enter is not None:
            self.on_enter(self)

        return convert_option_list_to_new_style_options(
            self.legacy_option.Children,
            None if (new_mod := self.mod) is None else new_mod.legacy_mod,  # type: ignore
        )

    @children.setter
    def children(self, value: Sequence[BaseOption]) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        pass


def _apply_hardcoded_option_fixups[J: JSON](  # noqa: C901 - will always need complex mod specific code
    option: Base,
    mod: "SDKMod | None",
    on_change: Callable[[ValueOption[J], Any], None],
) -> BaseOption | None:
    """
    Applies any hardcoded, mod-specific, option fixups, if applicable.

    Args:
        option: The legacy option to check for fixups.
        mod: The legacy mod this option is from.
        on_change: The on change callback to use (if a value option).
    Returns:
        The new style option, or None to use the standard conversion.
    """
    # This will need a rewrite if we want to be more generic
    if mod is None:
        return None
    if mod.Name not in {"Commander", "Loot Randomizer"}:
        return None
    del on_change

    # Loot randomizer's callback fields map nicely onto a button
    if type(option).__name__ == "CallbackField" and isinstance(option, Field):

        def on_press(_: ButtonOption) -> None:
            with legacy_compat():
                option.Callback()  # type: ignore

        return ButtonOption(
            option.Caption,
            description=option.Description,
            is_hidden=option.IsHidden,
            on_press=on_press,
        )

    # And with out custom _NestedProxy, callback nesteds are relatively simple too
    if type(option).__name__ == "CallbackNested" and isinstance(option, Nested):

        def on_enter(_: _NestedProxy) -> None:
            with legacy_compat():
                option.Callback()  # type: ignore

        return _NestedProxy(
            option.Caption,
            tuple(convert_option_list_to_new_style_options(option.Children, mod)),
            description=option.Description,
            is_hidden=option.IsHidden,
            legacy_option=option,
            on_enter=on_enter,
        )

    # The new seed option only gets filled after enabling the mod. Replicating it's logic is a bit
    # too complex, so just place a default dummy option telling people to do that.
    if option.Caption == "New Seed" and isinstance(option, Nested) and len(option.Children) == 0:
        return NestedOption(
            option.Caption,
            (
                ButtonOption("Please enable the mod first,"),
                ButtonOption("then re-open the mod menu"),
            ),
            description=option.Description,
            is_hidden=option.IsHidden,
        )

    # Commander's custom commands option is the only custom one it uses, so it hides all its logic
    # inside the hook. This is difficult to get to, so we instead just recreate it from scratch.
    if option.Caption == "Custom Commands" and isinstance(option, Field):

        def custom_command_callback(_: ButtonOption) -> None:
            with legacy_compat():
                try:
                    from Mods.Commander import Configurator  # type: ignore

                    Configurator.CustomConfigurator()  # type: ignore
                except ImportError:
                    import webbrowser

                    webbrowser.open(
                        "https://github.com/mopioid/Borderlands-Commander/wiki/Custom-Commands",
                    )

        return ButtonOption(
            option.Caption,
            description=option.Description,
            is_hidden=option.IsHidden,
            on_press=custom_command_callback,
        )

    return None


def convert_option_list_to_new_style_options(  # noqa: C901 - isn't a great way to make this simpler
    legacy_options: Sequence[Base],
    mod: "SDKMod | None" = None,
) -> list[BaseOption]:
    """
    Converts a list of legacy option to new-style options.

    Args:
        legacy_options: The list of legacy options.
        mod: The legacy mod object to send change callbacks to.
    Returns:
        A list of new-style options.
    """
    new_options: list[BaseOption] = []
    for option in legacy_options:

        def on_change[J: JSON](
            _: ValueOption[J],
            new_val: Any,
            legacy_option: Base = option,
        ) -> None:
            if (
                mod is not None
                and mod.new_mod_obj.is_enabled
                and not mod.new_mod_obj.suppress_mod_option_changed
            ):
                with legacy_compat():
                    mod.ModOptionChanged(legacy_option, new_val)  # type: ignore
            legacy_option.CurrentValue = new_val  # type: ignore

        converted_option = _apply_hardcoded_option_fixups(option, mod, on_change)

        if converted_option is None:
            match option:
                case Nested():
                    converted_option = _NestedProxy(
                        option.Caption,
                        tuple(convert_option_list_to_new_style_options(option.Children, mod)),
                        description=option.Description,
                        is_hidden=option.IsHidden,
                        legacy_option=option,
                    )
                case Field():
                    converted_option = ButtonOption(
                        option.Caption,
                        description=option.Description,
                        is_hidden=option.IsHidden,
                    )
                case Boolean():
                    converted_option = BoolOption(
                        option.Caption,
                        option.CurrentValue,
                        option.Choices[1],
                        option.Choices[0],
                        description=option.Description,
                        is_hidden=option.IsHidden,
                        on_change=on_change,
                    )
                case Spinner():
                    converted_option = SpinnerOption(
                        option.Caption,
                        option.CurrentValue,
                        list(option.Choices),
                        description=option.Description,
                        is_hidden=option.IsHidden,
                        on_change=on_change,
                    )
                case Slider():
                    converted_option = SliderOption(
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
                    converted_option = HiddenOption(
                        hidden_option.Caption,
                        hidden_option.CurrentValue,
                        description=hidden_option.Description,
                        on_change=on_change,
                    )
                case _:
                    raise TypeError(f"Unable to convert legacy option of type {type(option)}")

        if mod is not None:
            converted_option.mod = mod.new_mod_obj
        new_options.append(converted_option)
    return new_options
