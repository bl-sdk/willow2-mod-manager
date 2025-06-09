from mods_base import get_pc

__all__: tuple[str, ...] = (
    "hide_blocking_message",
    "hide_message",
    "show_blocking_message",
    "show_message",
)


def show_blocking_message(msg: str, reason: str | None = None) -> None:
    """
    Displays a blocking message with the given text.

    This message will stay until it is explicitly hidden, see `hide_blocking_message`.

    This message will block any input until it is hidden.

    Args:
        msg: The message to display.
        reason: An optional reason for the blocking message, which will be displayed as a subtitle.
                If None, the default text will show.
    """
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    backup = msg_movie.BlockingSubtitle
    msg_movie.BlockingSubtitle = reason if reason is not None else backup
    msg_movie.DisplayBlockingMessage(msg)
    msg_movie.BlockingSubtitle = backup


def hide_blocking_message() -> None:
    """Hides the currently displayed blocking message, if any."""
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.HideBlocking()


def show_message(msg: str) -> None:
    """
    Displays a message on the left side of the screen.

    This message will stay until it is explicitly hidden, see `hide_message`.

    Args:
        msg: The message to display.
    """
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.DisplayMessage(msg)


def hide_message() -> None:
    """Hides the currently displayed message in the online message movie."""
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.Hide()
