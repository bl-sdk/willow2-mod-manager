from datetime import datetime
from types import EllipsisType

import unrealsdk

from mods_base import get_pc


def show_chat_message(
    message: str,
    user: str | None = None,
    timestamp: datetime | None | EllipsisType = ...,
) -> None:
    """
    Prints a message to chat - with protection against the offline crash.

    Args:
        message: The message to print.
        user: The user to print the chat message as. If None, defaults to the current user.
        timestamp: The timestamp to print alongside the message. If None, doesn't print a timestamp,
                   if Ellipsis (the default) prints using the current time.
    """

    pc = get_pc(possibly_loading=True)
    if pc is None:
        raise RuntimeError(
            "Unable to show chat message since player controller could not be found!",
            message,
        )

    if user is None:
        user = pc.PlayerReplicationInfo.PlayerName

    if timestamp is ...:
        timestamp = datetime.now()  # noqa: DTZ005 - explicitly want local

    if timestamp is not None:
        is12h = unrealsdk.find_class("WillowSaveGameManager").ClassDefaultObject.TimeFormat == "12"
        time_str = timestamp.strftime("[%I:%M:%S%p]" if is12h else "[%H:%M:%S]").lower()
        user = f"{user} {time_str}"

    pc.GetTextChatMovie().AddChatMessageInternal(user, message)
