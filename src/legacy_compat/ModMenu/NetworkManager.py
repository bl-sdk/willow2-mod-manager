# ruff: noqa: N802, N803, N806, D102, D103, N999

from __future__ import annotations

import functools
import inspect
import traceback
from collections import deque
from time import time
from typing import TYPE_CHECKING, Any, TypedDict, cast

from mods_base import ENGINE, hook
from unrealsdk import logging
from unrealsdk.hooks import Block, Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

if TYPE_CHECKING:
    from collections.abc import Callable

    from .ModObjects import SDKMod

__all__: tuple[str, ...] = (
    "ClientMethod",
    "NetworkArgsDict",
    "RegisterNetworkMethods",
    "ServerMethod",
    "UnregisterNetworkMethods",
)


class NetworkArgsDict(TypedDict):
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class _Message:
    ID: str
    PC: UObject
    message_type: str
    arguments: str
    server: bool
    timeout: float | None

    def __init__(self, PC: UObject, message_type: str, arguments: str, server: bool) -> None:
        self.ID = str(id(self))  # pyright: ignore[reportConstantRedefinition]
        self.PC = PC  # pyright: ignore[reportConstantRedefinition]
        self.message_type = message_type
        self.arguments = f"{self.ID}:{arguments}"
        self.server = server
        self.timeout = None

    def send(self) -> None:
        """Send the message."""
        if self.server:
            self.PC.ServerSpeech(self.message_type, 0, self.arguments)
        else:
            self.PC.ClientMessage(self.arguments, self.message_type)
        self.timeout = time() + self.PC.PlayerReplicationInfo.ExactPing * 4


_message_queue: deque[_Message] = deque()


@hook("Engine.PlayerController:PlayerTick", Type.PRE)
def _PlayerTick(*_: Any) -> None:
    timeout = _message_queue[0].timeout
    if timeout is None:
        _message_queue[0].send()
    elif timeout < time():
        _dequeue_message()


@hook("Engine.GameInfo:Logout", Type.PRE, auto_enable=True)
def _Logout(_1: UObject, args: WrappedStruct, _3: Any, _4: BoundFunction) -> None:  # pyright: ignore[reportUnusedFunction]
    global _message_queue
    if len(_message_queue) == 0:
        return

    purged_queue = deque(message for message in _message_queue if message.PC is not args.Exiting)

    if len(purged_queue) == 0:
        _PlayerTick.disable()

    elif purged_queue[0] is not _message_queue[0]:
        purged_queue[0].send()

    _message_queue = purged_queue


@hook("Engine.GameViewportClient:GameSessionEnded", Type.PRE, auto_enable=True)
def _GameSessionEnded(*_: Any) -> None:  # pyright: ignore[reportUnusedFunction]
    global _message_queue
    if len(_message_queue) == 0:
        return
    _PlayerTick.disable()
    _message_queue = deque()


def _enqueue_message(message: _Message) -> None:
    _message_queue.append(message)
    if len(_message_queue) == 1:
        message.send()
        _PlayerTick.enable()


def _dequeue_message() -> None:
    _message_queue.popleft()
    if len(_message_queue) > 0:
        _message_queue[0].send()
    else:
        _PlayerTick.disable()


_method_senders: set[Callable[..., None]] = set()


def _find_method_sender(function: Callable[..., Any]) -> Callable[..., Any] | None:
    wrapped_func = function
    while wrapped_func is not None:
        if wrapped_func in _method_senders:
            break
        wrapped_func = getattr(wrapped_func, "__wrapped__", None)  # type: ignore
    return wrapped_func


def _create_method_sender(function: Callable[..., None]) -> Callable[..., None] | None:  # noqa: C901
    message_type = f"unrealsdk.{function.__module__}.{function.__qualname__}"

    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())
    if len(parameters) < 1:
        logging.dev_warning(f"Unable to register network method <{message_type}>.")
        logging.dev_warning(
            "    @ServerMethod and @ClientMethod decorated methods must be mod instance methods",
        )
        return None

    del parameters[0]
    signature = signature.replace(parameters=parameters)

    specifies_pc = signature.parameters.get("PC") is not None

    @functools.wraps(function)
    def method_sender(self: SDKMod, *args: Any, **kwargs: Any) -> None:
        world_info = ENGINE.GetCurrentWorldInfo()
        PRIs = list(world_info.GRI.PRIArray)

        send_server = method_sender._is_server and world_info.NetMode == 3  # type: ignore  # noqa: PLR2004
        send_client = method_sender._is_client and world_info.NetMode != 3 and len(PRIs) > 1  # type: ignore # noqa: PLR2004
        if not (send_server or send_client):
            return

        bindings = signature.bind(*args, **kwargs)
        remote_pc = bindings.arguments.get("PC", None)
        if specifies_pc:
            bindings.arguments["PC"] = None
        arguments = type(self).NetworkSerialize({"args": bindings.args, "kwargs": bindings.kwargs})

        local_pc = ENGINE.GamePlayers[0].Actor

        if send_server:
            _enqueue_message(_Message(local_pc, message_type, arguments, True))

        elif send_client and remote_pc is not None:
            if type(remote_pc) is UObject and remote_pc.Class.Name == "WillowPlayerController":
                _enqueue_message(_Message(remote_pc, message_type, arguments, False))
            else:
                raise TypeError(
                    f"Invalid player controller specified for {message_type}. Expected"
                    f" unrealsdk.UObject of UClass WillowPlayerController, received {remote_pc}.",
                )

        elif send_client:
            for PRI in PRIs:
                if PRI.Owner is not None and PRI.Owner is not local_pc:
                    _enqueue_message(_Message(PRI.Owner, message_type, arguments, False))

    method_sender._message_type = message_type  # type: ignore
    method_sender._is_server = False  # type: ignore
    method_sender._is_client = False  # type: ignore

    _method_senders.add(method_sender)
    return method_sender


def ServerMethod(function: Callable[..., None]) -> Callable[..., None]:
    method_sender = _find_method_sender(function)
    if method_sender is None:
        method_sender = _create_method_sender(function)
        if method_sender is None:
            return function

    method_sender._is_server = True  # type: ignore
    return method_sender


def ClientMethod(function: Callable[..., None]) -> Callable[..., None]:
    method_sender = _find_method_sender(function)
    if method_sender is None:
        method_sender = _create_method_sender(function)
        if method_sender is None:
            return function

    method_sender._is_client = True  # type: ignore
    return method_sender


_server_message_types: dict[str, set[Callable[..., None]]] = {}
_client_message_types: dict[str, set[Callable[..., None]]] = {}


def RegisterNetworkMethods(mod: SDKMod) -> None:
    cls = type(mod)

    for function in cls.server_functions:
        method = function.__wrapped__.__get__(mod, cls)  # type: ignore
        _server_message_types.setdefault(function._message_type, set()).add(method)  # type: ignore

    for function in cls.client_functions:
        method = function.__wrapped__.__get__(mod, cls)  # type: ignore
        _client_message_types.setdefault(function._message_type, set()).add(method)  # type: ignore


def UnregisterNetworkMethods(mod: SDKMod) -> None:
    cls = type(mod)

    for function in cls.server_functions:
        methods = _server_message_types.get(function._message_type)  # type: ignore
        if methods is not None:
            methods.discard(function.__wrapped__.__get__(mod, cls))  # type: ignore
            if len(methods) == 0:
                del _server_message_types[function._message_type]  # type: ignore

    for function in cls.client_functions:
        methods = _client_message_types.get(function._message_type)  # type: ignore
        if methods is not None:
            methods.discard(function.__wrapped__.__get__(mod, cls))  # type: ignore
            if len(methods) == 0:
                del _client_message_types[function._message_type]  # type: ignore


@hook("Engine.PlayerController:ServerSpeech", Type.PRE, auto_enable=True)
def _server_speech(  # noqa: C901  # pyright: ignore[reportUnusedFunction]
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    message = args.Callsign
    message_type = args.Type
    if message_type is None or not message_type.startswith("unrealsdk."):
        return None

    # Check if the message type indicates an acknowledgement from a client for the previous message
    # we had sent. If so, and its ID matches that of our last message, dequeue it and we are done.
    if message_type == "unrealsdk.__clientack__":
        if len(_message_queue) > 0 and message == _message_queue[0].ID:
            _dequeue_message()
        return Block

    # This message's ID and serialized arguments should be separated by a ":". If not, ignore it.
    message_components = message.split(":", 1)
    if len(message_components) != 2:  # noqa: PLR2004
        return Block
    message_id = message_components[0]

    # Get the list of methods registered to respond to this message type. If none are, we're done.
    methods = _server_message_types.get(message_type)
    if methods is not None and len(methods) > 0:
        # All of the methods in this set are known to be identical functions, just bound to
        # different instances. Retrieve any one of them, and get the mod's class from it.
        sample_method = next(iter(methods))
        cls = cast("type[SDKMod]", type(sample_method.__self__))  # type: ignore

        # Attempt to use the class's deserializer callable to deserialize the message's arguments.
        arguments = None
        try:
            arguments = cls.NetworkDeserialize(message_components[1])
        except Exception:  # noqa: BLE001
            logging.error(f"Unable to deserialize arguments for '{message_type}'")
            tb = traceback.format_exc().split("\n")
            logging.dev_warning(f"    {tb[-4].strip()}")
            logging.dev_warning(f"    {tb[-3].strip()}")
            logging.dev_warning(f"    {tb[-2].strip()}")

        if arguments is not None:
            # Use the inspect module to correctly map the received arguments to their parameters.
            bindings = inspect.signature(sample_method).bind(
                *arguments["args"],
                **arguments["kwargs"],  # type: ignore
            )
            # If this method has a parameter through which to pass a player controller, assign the
            # caller to it.
            if bindings.signature.parameters.get("PC") is not None:
                bindings.arguments["PC"] = obj

            # Invoke each registered method with the mapped arguments.
            for method in methods:
                try:
                    method(*bindings.args, **bindings.kwargs)
                except Exception:  # noqa: BLE001
                    logging.error(f"Unable to call remotely requested {method}.")
                    tb = traceback.format_exc().split("\n")
                    logging.dev_warning(f"    {tb[-4].strip()}")
                    logging.dev_warning(f"    {tb[-3].strip()}")
                    logging.dev_warning(f"    {tb[-2].strip()}")

    # Send acknowledgement of the message back to the client.
    obj.ClientMessage("unrealsdk.__serverack__", message_id)
    return Block


@hook("WillowGame.WillowPlayerController:ClientMessage", Type.PRE, auto_enable=True)
def _client_message(  # pyright: ignore[reportUnusedFunction]
    obj: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    message = args.S
    message_type = args.Type
    if message_type is None or not message_type.startswith("unrealsdk."):
        return None

    if message_type == "unrealsdk.__serverack__":
        if len(_message_queue) > 0 and message == _message_queue[0].ID:
            _dequeue_message()
        return Block

    message_components = message.split(":", 1)
    if len(message_components) != 2:  # noqa: PLR2004
        return Block
    message_id = message_components[0]

    methods = _client_message_types.get(message_type)
    if methods is not None and len(methods) > 0:
        sample_method = next(iter(methods))
        cls = cast("type[SDKMod]", type(sample_method.__self__))  # type: ignore

        arguments = None
        try:
            arguments = cls.NetworkDeserialize(message_components[1])
        except Exception:  # noqa: BLE001
            logging.error(f"Unable to deserialize arguments for '{message_type}'")
            tb = traceback.format_exc().split("\n")
            logging.dev_warning(f"    {tb[-4].strip()}")
            logging.dev_warning(f"    {tb[-3].strip()}")
            logging.dev_warning(f"    {tb[-2].strip()}")

        if arguments is not None:
            for method in methods:
                try:
                    method(*arguments["args"], **arguments["kwargs"])
                except Exception:  # noqa: BLE001
                    logging.error(f"Unable to call remotely requested {method}.")
                    tb = traceback.format_exc().split("\n")
                    logging.dev_warning(f"    {tb[-4].strip()}")
                    logging.dev_warning(f"    {tb[-3].strip()}")
                    logging.dev_warning(f"    {tb[-2].strip()}")

    obj.ServerSpeech(message_id, 0, "unrealsdk.__clientack__")
    return Block
