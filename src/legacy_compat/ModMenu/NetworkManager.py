# ruff: noqa: N802, N803, N806, D102, D103, N999

from __future__ import annotations

import functools
import inspect
import traceback
from collections import deque
from time import time
from typing import TYPE_CHECKING, Any, TypedDict, cast

from legacy_compat import unrealsdk as old_unrealsdk

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
    PC: old_unrealsdk.UObject
    message_type: str
    arguments: str
    server: bool
    timeout: float | None

    def __init__(
        self,
        PC: old_unrealsdk.UObject,
        message_type: str,
        arguments: str,
        server: bool,
    ) -> None:
        self.ID = str(id(self))  # pyright: ignore[reportConstantRedefinition]
        self.PC = PC  # pyright: ignore[reportConstantRedefinition]
        self.message_type = message_type
        self.arguments = f"{self.ID}:{arguments}"
        self.server = server
        self.timeout = None

    def send(self) -> None:
        if self.server:
            self.PC.ServerSpeech(self.message_type, 0, self.arguments)
        else:
            self.PC.ClientMessage(self.arguments, self.message_type)
        self.timeout = time() + self.PC.PlayerReplicationInfo.ExactPing * 4


_message_queue: deque[_Message] = deque()


def _PlayerTick(
    caller: old_unrealsdk.UObject,  # noqa: ARG001
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,  # noqa: ARG001
) -> bool:
    timeout = _message_queue[0].timeout
    if timeout is None:
        _message_queue[0].send()
    elif timeout < time():
        _dequeue_message()
    return True


def _Logout(
    caller: old_unrealsdk.UObject,  # noqa: ARG001
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,
) -> bool:
    global _message_queue
    if len(_message_queue) == 0:
        return True

    purged_queue = deque(message for message in _message_queue if message.PC is not params.Exiting)

    if len(purged_queue) == 0:
        old_unrealsdk.RemoveHook("Engine.PlayerController.PlayerTick", "ModMenu.NetworkManager")

    elif purged_queue[0] is not _message_queue[0]:
        purged_queue[0].send()

    _message_queue = purged_queue
    return True


def _GameSessionEnded(
    caller: old_unrealsdk.UObject,  # noqa: ARG001
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,  # noqa: ARG001
) -> bool:
    global _message_queue
    if len(_message_queue) == 0:
        return True
    old_unrealsdk.RemoveHook("Engine.PlayerController.PlayerTick", "ModMenu.NetworkManager")
    _message_queue = deque()
    return True


def _enqueue_message(message: _Message) -> None:
    _message_queue.append(message)

    if len(_message_queue) == 1:
        message.send()
        old_unrealsdk.RunHook(
            "Engine.PlayerController.PlayerTick",
            "ModMenu.NetworkManager",
            _PlayerTick,
        )


def _dequeue_message() -> None:
    _message_queue.popleft()

    if len(_message_queue) > 0:
        _message_queue[0].send()
    else:
        old_unrealsdk.RemoveHook("Engine.PlayerController.PlayerTick", "ModMenu.NetworkManager")


_method_senders: set[Callable[..., None]] = set()


def _find_method_sender(function: Callable[..., Any]) -> Callable[..., Any] | None:
    wrapped_func: Callable[..., Any] | None = function
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
        old_unrealsdk.Log(f"Unable to register network method <{message_type}>.")
        old_unrealsdk.Log(
            "    @ServerMethod and @ClientMethod decorated methods must be mod instance methods",
        )
        return None

    del parameters[0]
    signature = signature.replace(parameters=parameters)

    specifies_pc = signature.parameters.get("PC") is not None

    @functools.wraps(function)
    def method_sender(self: SDKMod, *args: Any, **kwargs: Any) -> None:
        world_info = old_unrealsdk.GetEngine().GetCurrentWorldInfo()
        PRIs = list(world_info.GRI.PRIArray)

        NM_Client = 3
        send_server = method_sender._is_server and world_info.NetMode == NM_Client  # type: ignore
        send_client = (  # type: ignore
            method_sender._is_client and world_info.NetMode != NM_Client and len(PRIs) > 1  # type: ignore
        )
        if not (send_server or send_client):
            return

        bindings = signature.bind(*args, **kwargs)
        remote_pc = bindings.arguments.get("PC", None)
        if specifies_pc:
            bindings.arguments["PC"] = None
        arguments = type(self).NetworkSerialize({"args": bindings.args, "kwargs": bindings.kwargs})

        local_pc = old_unrealsdk.GetEngine().GamePlayers[0].Actor

        if send_server:
            _enqueue_message(_Message(local_pc, message_type, arguments, True))

        elif send_client and remote_pc is not None:
            if (
                type(remote_pc) is old_unrealsdk.UObject
                and remote_pc.Class.Name == "WillowPlayerController"
            ):
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


def _server_speech(  # noqa: C901
    caller: old_unrealsdk.UObject,
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,
) -> bool:
    message = params.Callsign
    message_type = params.Type
    if message_type is None or not message_type.startswith("unrealsdk."):
        return True

    if message_type == "unrealsdk.__clientack__":
        if len(_message_queue) > 0 and message == _message_queue[0].ID:
            _dequeue_message()
        return False

    message_components = message.split(":", 1)
    if len(message_components) != 2:  # noqa: PLR2004
        return False
    message_id = message_components[0]

    methods = _server_message_types.get(message_type)
    if methods is not None and len(methods) > 0:
        sample_method = next(iter(methods))
        cls = cast(type["SDKMod"], type(sample_method.__self__))  # type: ignore

        arguments = None
        try:
            arguments = cls.NetworkDeserialize(message_components[1])
        except Exception:  # noqa: BLE001
            old_unrealsdk.Log(f"Unable to deserialize arguments for '{message_type}'")
            tb = traceback.format_exc().split("\n")
            old_unrealsdk.Log(f"    {tb[-4].strip()}")
            old_unrealsdk.Log(f"    {tb[-3].strip()}")
            old_unrealsdk.Log(f"    {tb[-2].strip()}")

        if arguments is not None:
            bindings = inspect.signature(sample_method).bind(
                *arguments["args"],
                **arguments["kwargs"],
            )
            if bindings.signature.parameters.get("PC") is not None:
                bindings.arguments["PC"] = caller

            for method in methods:
                try:
                    method(*bindings.args, **bindings.kwargs)
                except Exception:  # noqa: BLE001
                    old_unrealsdk.Log(f"Unable to call remotely requested {method}.")
                    tb = traceback.format_exc().split("\n")
                    old_unrealsdk.Log(f"    {tb[-4].strip()}")
                    old_unrealsdk.Log(f"    {tb[-3].strip()}")
                    old_unrealsdk.Log(f"    {tb[-2].strip()}")

    # Send acknowledgement of the message back to the client.
    caller.ClientMessage("unrealsdk.__serverack__", message_id)
    return False


def _client_message(
    caller: old_unrealsdk.UObject,
    function: old_unrealsdk.UFunction,  # noqa: ARG001
    params: old_unrealsdk.FStruct,
) -> bool:
    message = params.S
    message_type = params.Type
    if message_type is None or not message_type.startswith("unrealsdk."):
        return True

    if message_type == "unrealsdk.__serverack__":
        if len(_message_queue) > 0 and message == _message_queue[0].ID:
            _dequeue_message()
        return False

    message_components = message.split(":", 1)
    if len(message_components) != 2:  # noqa: PLR2004
        return False
    message_id = message_components[0]

    methods = _client_message_types.get(message_type)
    if methods is not None and len(methods) > 0:
        sample_method = next(iter(methods))
        cls = cast(type["SDKMod"], type(sample_method.__self__))  # type: ignore

        arguments = None
        try:
            arguments = cls.NetworkDeserialize(message_components[1])
        except Exception:  # noqa: BLE001
            old_unrealsdk.Log(f"Unable to deserialize arguments for '{message_type}'")
            tb = traceback.format_exc().split("\n")
            old_unrealsdk.Log(f"    {tb[-4].strip()}")
            old_unrealsdk.Log(f"    {tb[-3].strip()}")
            old_unrealsdk.Log(f"    {tb[-2].strip()}")

        if arguments is not None:
            for method in methods:
                try:
                    method(*arguments["args"], **arguments["kwargs"])
                except Exception:  # noqa: BLE001
                    old_unrealsdk.Log(f"Unable to call remotely requested {method}.")
                    tb = traceback.format_exc().split("\n")
                    old_unrealsdk.Log(f"    {tb[-4].strip()}")
                    old_unrealsdk.Log(f"    {tb[-3].strip()}")
                    old_unrealsdk.Log(f"    {tb[-2].strip()}")

    caller.ServerSpeech(message_id, 0, "unrealsdk.__clientack__")
    return False


old_unrealsdk.RunHook(
    "Engine.PlayerController.ServerSpeech",
    "ModMenu.NetworkManager",
    _server_speech,
)
old_unrealsdk.RunHook(
    "WillowGame.WillowPlayerController.ClientMessage",
    "ModMenu.NetworkManager",
    _client_message,
)
old_unrealsdk.RunHook("Engine.GameInfo.Logout", "ModMenu.NetworkManager", _Logout)
old_unrealsdk.RunHook(
    "Engine.GameViewportClient.GameSessionEnded",
    "ModMenu.NetworkManager",
    _GameSessionEnded,
)
