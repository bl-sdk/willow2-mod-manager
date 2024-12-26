import traceback
from typing import TYPE_CHECKING, Any

import unrealsdk
from unrealsdk import logging
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from mods_base import ENGINE, get_pc, hook

from .registration import handle_received_message

if TYPE_CHECKING:
    from enum import auto

    from unrealsdk.unreal._uenum import UnrealEnum  # pyright: ignore[reportMissingModuleSource]

    class ENetMode(UnrealEnum):
        NM_Standalone = auto()
        NM_DedicatedServer = auto()
        NM_ListenServer = auto()
        NM_Client = auto()
        NM_MAX = auto()

else:
    ENetMode = unrealsdk.find_enum("ENetMode")

"""
This file implements the low level transmission between players.

To start with, we need to go over how unreal's replication works, at least wrt. to how we use it.

The current WorldInfo points to the current GameReplicationInfo, which has a list of
PlayerReplicationInfo objects. These contain the minimal required info to replicate the remote
player (who could've guessed), stuff like the skin they use and what items they're holding.
Importantly for us, this list is synced between all players, entries are added/removed as they
join/leave. We use the PlayerReplicationInfo::PlayerID field to uniquely identify players (object
names are NOT stable).

Now another object we're interested in is the PlayerController, which are replicated a little
differently. The host can see every player controller in the current game, but each client can only
see themselves.

To transmit messages we rely on the following two functions, which are both under PlayerController.
There aren't any good equivalents under PlayerReplicationInfo, otherwise we'd use them.

// Engine.PlayerController:ServerSpeech
reliable server function ServerSpeech(name Type, int Index, string Callsign)

// Engine.PlayerController:ClientMessage
// WillowGame.WillowPlayerController:ClientMessage
reliable client simulated event ClientMessage(coerce string S, optional name Type, optional float MsgLifeTime)

Firstly, since both of these functions are reliable, we don't need to implement any sequencing or
ack mechanisms, the engine takes care of it for us.

Since ServerSpeech is a server method, when anyone calls it, it also runs on the server, on the
server's copy of the player controller that triggered it. When called directly on the server,
there's just the single hook activation, when called on a client it activates once on each side.
This gives us a simple client -> server message.

Conversely ClientMessage is a client method, so when called it runs on the relevant client. If
called on yourself, the hook triggers once, and if the server calls it on a different player it
triggers once on each end. This covers server -> client messages.

The one case we're still missing is client -> client messages, which we need to implement with a
jump through the server.

Now regarding the args, all we actually need to get message passing working is a single string, we
could encode any extra requirements within it. Since we happen to have two very similar sets of args
though, we might as well make use of them:

ServerSpeech | ClientMessage | Usage
:------------|:--------------|:-------------------------------------------------------
Type         | Type          | The message identifier.
Callsign     | S             | The user defined string being transmitted.
Index        | MsgLifeTime   | A PlayerID relating to this message - see table below.

Player ID Usage
Function      | Broadcast Message | Targeted Message
:-------------|:------------------|:-----------------
ServerSpeech  | Unused            | Target's
ClientMessage | Original Sender's | Original Sender's

Since MsgLifeTime is a float, while Index and PlayerID are ints, there's the possibility of losing
precision. In practice the player ids stay low, so we just throw when this happens.

"""  # noqa: E501

# Since we have a limited amount of bandwidth, and since we're transmitting them, try keep the
# message types a bit shorter
CUSTOM_MESSAGE = "!willow_nw:"
BROADCAST_MESSAGE = f"{CUSTOM_MESSAGE}b!"
TARGETED_MESSAGE = f"{CUSTOM_MESSAGE}t!"

CUSTOM_MESSAGE_PREFIX_LEN = len(BROADCAST_MESSAGE)
assert len(TARGETED_MESSAGE) == CUSTOM_MESSAGE_PREFIX_LEN

# The range where float32s still have integer precision
VALID_SENDER_ID_RANGE = range(-0x1000000, 0x1000000)


def get_player_id(pri: UObject) -> int:
    """
    Helper to safely get the player ID while validating it's in range.

    Args:
        pri: The player replication info to get the ID of.
    Returns:
        The player ID.
    """
    player_id = pri.PlayerID
    if player_id not in VALID_SENDER_ID_RANGE:
        raise RuntimeError(
            "Unable to transmit message due to out of range player id!",
            player_id,
        )
    return player_id


def checked_get_pc() -> UObject:
    """
    Gets the current local player controller, while validating it's not null due to thread trickery.

    Returns:
        The player controller.
    """
    pc = get_pc(possibly_loading=True)
    if pc is None:
        raise RuntimeError("Unable to transmit message since player controller could not be found!")
    return pc


def broadcast(identifier: str, msg: str) -> None:
    """
    Broadcasts a message to all players.

    Args:
        identifier: The message identifier.
        msg: The message to broadcast.
    """
    local_pc = checked_get_pc()
    sender_id = get_player_id(local_pri := local_pc.PlayerReplicationInfo)
    message_type = BROADCAST_MESSAGE + identifier

    world_info = ENGINE.GetCurrentWorldInfo()
    if world_info.NetMode == ENetMode.NM_Client:
        # If we're a client, tell the server to broadcast this message
        local_pc.ServerSpeech(message_type, 0, msg)
        # And handle it ourselves immediately
        handle_received_message(local_pri, identifier, msg)
    else:
        # If we're the server, broadcast the message to all players, including ourselves
        for pri in world_info.GRI.PRIArray:
            if (remote_pc := pri.Owner) is None:
                continue
            remote_pc.ClientMessage(msg, message_type, float(sender_id))


def transmit(pri: UObject, identifier: str, msg: str) -> None:
    """
    Transmits a message to a player.

    Args:
        pri: The PlayerReplicationInfo of the player to transmit to.
        identifier: The message identifier.
        msg: The message to transmit.
    """
    local_pc = checked_get_pc()
    target_id = get_player_id(pri)

    local_pri = local_pc.PlayerReplicationInfo
    if pri == local_pri:
        # If we're sending a message to ourselves, just process it immediately
        handle_received_message(pri, identifier, msg)
        return

    message_type = TARGETED_MESSAGE + identifier

    if ENGINE.GetCurrentWorldInfo().NetMode == ENetMode.NM_Client:
        # If we're a client, tell the server we want to send to this target
        local_pc.ServerSpeech(message_type, target_id, msg)
    elif (remote_pc := pri.Owner) is not None:
        # If we're the server, send a message from ourselves
        remote_pc.ClientMessage(msg, message_type, float(local_pri.PlayerID))


def get_host_pri() -> UObject:
    """
    Gets the hosts's PlayerReplicationInfo object.

    Returns:
        The hosts's PlayerReplicationInfo.
    """
    # Seems they're always entry 0?
    return ENGINE.GetCurrentWorldInfo().GRI.PRIArray[0]


@hook("WillowGame.WillowPlayerController:ClientMessage", immediately_enable=True)
def client_message_hook(  # noqa: D103
    calling_pc: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    # We only care if this is a message for the local PC, not one the server is sending off
    if calling_pc != get_pc():  # doesn't need to be checked
        return None

    if not args.Type.startswith(CUSTOM_MESSAGE):
        return None
    # No matter how we receive the message, if it gets here it's always something we want to process

    # Recover the sender's PRI
    sender_id = int(args.MsgLifeTime)
    for pri in ENGINE.GetCurrentWorldInfo().GRI.PRIArray:
        if pri.PlayerID == sender_id:
            handle_received_message(
                pri,
                args.Type[CUSTOM_MESSAGE_PREFIX_LEN:],
                args.S,
            )
            return Block

    logging.warning(
        f"Got network message from unknown sender player id {sender_id}. Message type: {args.Type}",
    )
    return Block


@hook("Engine.PlayerController:ServerSpeech", immediately_enable=True)
def server_speech_hook(  # noqa: D103
    sender_pc: UObject,
    args: WrappedStruct,
    _3: Any,
    _4: BoundFunction,
) -> type[Block] | None:
    if not args.Type.startswith(CUSTOM_MESSAGE):
        return None

    world_info = ENGINE.GetCurrentWorldInfo()

    # If we're a client, we need to let the calls through so they get transmitted to the server
    if world_info.NetMode == ENetMode.NM_Client:
        return None

    try:
        sender_id = get_player_id(sender_pri := sender_pc.PlayerReplicationInfo)

        if args.Type.startswith(BROADCAST_MESSAGE):
            # Rebroadcast it to all clients but the sender
            for pri in world_info.GRI.PRIArray:
                if pri == sender_pri:
                    continue

                pri.Owner.ClientMessage(args.Callsign, args.Type, float(sender_id))

        elif args.Type.startswith(TARGETED_MESSAGE):
            # Find the target and forward it to them
            target_id = args.Index
            for pri in world_info.GRI.PRIArray:
                if pri.PlayerID != target_id:
                    continue

                pri.Owner.ClientMessage(args.Callsign, args.Type, float(sender_id))
                break
            else:
                logging.warning(
                    f"Got network message from targeting player id {target_id}, which does not"
                    f" exist. Message type: {args.Type}",
                )

    except Exception:  # noqa: BLE001
        traceback.print_exc()

    return Block
