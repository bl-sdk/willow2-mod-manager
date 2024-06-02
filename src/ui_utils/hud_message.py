import unrealsdk
from mods_base import get_pc

__all__: tuple[str, ...] = ("show_hud_message",)


def show_hud_message(title: str, msg: str, duration: float = 2.5) -> None:
    """
    Displays a short, non-blocking message in the main in game hud.

    Uses the same message style as those for coop players joining/leaving or shift going down.

    Note this should not be used for critical messages, it may silently fail at any point, and
    messages may be dropped if multiple are shown too close to each other.

    Args:
        title: The title of the message box.
        msg: The message to display.
        duration: The duration to display the message for.
    """
    pc = get_pc()

    hud_movie = pc.GetHUDMovie()

    if hud_movie is None:
        return

    hud_movie.ClearTrainingText()
    hud_movie.AddTrainingText(
        msg,
        title,
        duration,
        unrealsdk.make_struct("Color"),
        "",
        False,
        0,
        pc.PlayerReplicationInfo,
        True,
        0,
    )
