from collections import deque
from dataclasses import dataclass
from typing import Any

from unrealsdk.unreal import UObject

from mods_base import ENGINE, hook

from . import transmission

# The engine imposes some sort of bandwidth cap on messages between players. This file implements a
# message queue, and only transmits a handful of messages per tick, to try avoid running into it.

MAX_MESSAGES_PER_TICK = 1


def broadcast(identifier: str, msg: str) -> None:
    """
    Queues up a message to broadcasts to all players.

    Args:
        identifier: The message identifier.
        msg: The message to broadcast.
    """
    message_queue.append(BroadcastMessage(identifier, msg))
    tick_hook.enable()


def transmit(pri: UObject, identifier: str, msg: str) -> None:
    """
    Queues up a message to be transmitted to a player.

    Args:
        pri: The PlayerReplicationInfo of the player to transmit to.
        identifier: The message identifier.
        msg: The message to transmit.
    """
    message_queue.append(TargetedMessage(pri.PlayerID, identifier, msg))
    tick_hook.enable()


@dataclass
class BroadcastMessage:
    identifier: str
    msg: str

    def send(self) -> None:
        """Transmits this message."""
        transmission.broadcast(self.identifier, self.msg)


@dataclass
class TargetedMessage:
    player_id: int
    identifier: str
    msg: str

    def send(self) -> None:
        """Transmits this message."""
        # Find the relevant PRI object again
        # Every level change creates a new object, so we can't just store a weak pointer, have to
        # look it up using the player id
        for pri in ENGINE.GetCurrentWorldInfo().GRI.PRIArray:
            if pri.PlayerID == self.player_id:
                transmission.transmit(pri, self.identifier, self.msg)
                break

        # If we failed to find it, the player must have left, just silently drop it


message_queue: deque[BroadcastMessage | TargetedMessage] = deque()


@hook("Engine.PlayerController:PlayerTick", immediately_enable=True)
def tick_hook(*_1: Any) -> None:  # noqa: D103
    for _2 in range(MAX_MESSAGES_PER_TICK):
        if len(message_queue) == 0:
            tick_hook.disable()
            return

        message_queue.popleft().send()
