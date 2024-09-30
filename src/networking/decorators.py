import inspect
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import update_wrapper
from typing import Any, Concatenate, Self

from unrealsdk.unreal import UObject

from . import queue
from .registration import add_network_callback, remove_network_callback
from .transmission import get_host_pri


@dataclass
class NetworkFunction[**WrappedParams, **CallingParams](ABC):
    __wrapped__: Callable[WrappedParams, None]

    network_identifier: str = None  # type: ignore
    sender: UObject = field(init=False, repr=False, default=None)  # type: ignore

    def __post_init__(self) -> None:
        update_wrapper(self, self.__wrapped__)

        if self.network_identifier is None:  # type: ignore
            module_name = (
                "unknown_module"
                if (module := inspect.getmodule(self.__wrapped__)) is None
                else module.__name__
            )
            self.network_identifier = f"{module_name}:{self.__wrapped__.__qualname__}"

    def enable(self) -> None:
        """Enables listening for this function's network messages."""

        def callback(sender: UObject, msg: str) -> None:
            self.sender = sender
            try:
                self._decode_message_and_run(msg)
            finally:
                self.sender = None  # type: ignore

        add_network_callback(self.network_identifier, callback)

    def disable(self) -> None:
        """Disables listening for this function's network messages."""
        remove_network_callback(self.network_identifier)

    def bind(self, obj: object, identifier_extension: str | None = None) -> Self:
        """
        Creates a new network function bound to the given object.

        This must be called if the current function wraps a method. You must only interact with the
        function this returns, you may not enable the hook on this level, otherwise you will get
        exceptions for missing or misaligned of parameters.

        Generally you want to call this using:
            self.some_func = self.some_func.bind(self, identifier_extension)

        Args:
            obj: The object to bind to.
            identifier_extension: If not None, extends the network identifier with the given string.
                                  You must provide different extensions if you intend to enable
                                  multiple functions on different instances at the same time,
                                  otherwise their identifiers will conflict.
        Return:
            The new network function.
        """
        return type(self)(
            self.__wrapped__.__get__(obj, type(obj)),
            (
                self.network_identifier
                if identifier_extension is None
                else f"{self.network_identifier}:{identifier_extension}"
            ),
        )

    @abstractmethod
    def _encode_message(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> str:
        """Encodes the function args into a string."""
        raise NotImplementedError

    @abstractmethod
    def _decode_message_and_run(self, msg: str) -> None:
        """Decodes the received message and runs the wrapped function with it."""
        raise NotImplementedError

    @abstractmethod
    def __call__(self, *args: CallingParams.args, **kwargs: CallingParams.kwargs) -> None:
        """Encodes the function args and transmits them to the relevant players."""
        raise NotImplementedError


class _EmptyEncoder:
    __wrapped__: Callable[[], None]

    def _encode_message(self) -> str:
        return ""

    def _decode_message_and_run(self, msg: str) -> None:  # noqa: ARG002
        self.__wrapped__()


class _StringEncoder:
    __wrapped__: Callable[[str], None]

    def _encode_message(self, msg: str) -> str:
        return msg

    def _decode_message_and_run(self, msg: str) -> None:
        self.__wrapped__(msg)


class _JsonEncoder:
    __wrapped__: Callable[..., None]

    def _encode_message(self, *args: Any, **kwargs: Any) -> str:
        return json.dumps([list(args), kwargs], indent=None, separators=(",", ":"))

    def _decode_message_and_run(self, msg: str) -> None:
        args, kwargs = json.loads(msg)
        self.__wrapped__(*args, **kwargs)


class broadcast:  # noqa: N801
    class _Transmitter[**WrappedParams](ABC):
        network_identifier: str

        @abstractmethod
        def _encode_message(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> str:
            raise NotImplementedError

        def __call__(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> None:
            queue.broadcast(self.network_identifier, self._encode_message(*args, **kwargs))

    @dataclass
    class message(_EmptyEncoder, _Transmitter[[]], NetworkFunction[[], []]): ...  # noqa: N801

    @dataclass
    class string_message(_StringEncoder, _Transmitter[[str]], NetworkFunction[[str], [str]]): ...  # noqa: N801

    @dataclass
    class json_message[**P](  # noqa: N801
        _JsonEncoder,
        _Transmitter[P],
        NetworkFunction[P, Concatenate[UObject, P]],
    ): ...


class host:  # noqa: N801
    class _Transmitter[**WrappedParams](ABC):
        network_identifier: str

        @abstractmethod
        def _encode_message(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> str:
            raise NotImplementedError

        def __call__(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> None:
            queue.transmit(
                get_host_pri(),
                self.network_identifier,
                self._encode_message(*args, **kwargs),
            )

    @dataclass
    class message(_EmptyEncoder, _Transmitter[[]], NetworkFunction[[], []]): ...  # noqa: N801

    @dataclass
    class string_message(_StringEncoder, _Transmitter[[str]], NetworkFunction[[str], [str]]): ...  # noqa: N801

    @dataclass
    class json_message[**P](  # noqa: N801
        _JsonEncoder,
        _Transmitter[P],
        NetworkFunction[P, Concatenate[UObject, P]],
    ): ...


class targeted:  # noqa: N801
    class _Transmitter[**WrappedParams](ABC):
        network_identifier: str

        @abstractmethod
        def _encode_message(self, *args: WrappedParams.args, **kwargs: WrappedParams.kwargs) -> str:
            raise NotImplementedError

        def __call__(
            self,
            pri: UObject,
            /,
            *args: WrappedParams.args,
            **kwargs: WrappedParams.kwargs,
        ) -> None:
            queue.transmit(pri, self.network_identifier, self._encode_message(*args, **kwargs))

    @dataclass
    class message(_EmptyEncoder, _Transmitter[[]], NetworkFunction[[], [UObject]]): ...  # noqa: N801

    @dataclass
    class string_message(  # noqa: N801
        _StringEncoder,
        _Transmitter[[str]],
        NetworkFunction[[str], [UObject, str]],
    ): ...

    @dataclass
    class json_message[**P](  # noqa: N801
        _JsonEncoder,
        _Transmitter[P],
        NetworkFunction[P, Concatenate[UObject, P]],
    ): ...
