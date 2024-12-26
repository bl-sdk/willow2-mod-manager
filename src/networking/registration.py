import traceback
from collections.abc import Callable

from unrealsdk import logging
from unrealsdk.unreal import UObject

type NetworkCallback = Callable[[UObject, str], None]

registered_callbacks: dict[str, NetworkCallback] = {}
warned_unknown_identifiers: set[str] = set()


def add_network_callback(identifier: str, callback: NetworkCallback) -> None:
    """
    Registers a callback to run when a network message with the given identifier is received.

    Network callbacks take two positional arguments:
        sender: The PlayerReplicationInfo of the player who sent the message.
        msg: The message which was sent.

    Args:
        identifier: The message identifier to look for.
        callback: The callback to run on messages matching the given identifier.
    """
    registered_callbacks[identifier] = callback

    # On adding the callback, allow warning about it again, in case someone goes from having the mod
    # disabled -> enabled -> disabled
    warned_unknown_identifiers.discard(identifier)


def remove_network_callback(identifier: str) -> None:
    """
    Removes a previously registered network callback.

    Args:
        identifier: The message identifier it was registered under.
    """
    registered_callbacks.pop(identifier)


def handle_received_message(sender: UObject, identifier: str, msg: str) -> None:
    """
    Handles a message being received on the game instance it's intended for.

    Args:
        sender: The PlayerReplicationInfo of the player who sent it.
        identifier: The message identifier.
        msg: The received message.
    """
    if identifier not in registered_callbacks:
        if identifier not in warned_unknown_identifiers:
            logging.warning(f"Received a network message with unknown identifier: {identifier}")
            logging.warning("Are you sure you have all the same mods enabled as the other players?")
            warned_unknown_identifiers.add(identifier)
        return

    try:
        registered_callbacks[identifier](sender, msg)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
