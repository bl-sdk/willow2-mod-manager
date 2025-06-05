from collections.abc import Iterator
from contextlib import contextmanager
from types import EllipsisType
from typing import TYPE_CHECKING

import unrealsdk
from unrealsdk import unreal

from mods_base import get_pc

if TYPE_CHECKING:
    from enum import IntEnum

    class ERewardPopup(IntEnum):
        ERP_BadassToken = 0
        ERP_CharacterHead = 1
        ERP_CharacterSkin = 2
        ERP_VehicleSkin = 3
        ERP_MAX = 4

else:
    ERewardPopup = unrealsdk.find_enum("ERewardPopup")

__all__: tuple[str, ...] = (
    "ERewardPopup",
    "blocking_message_hide",
    "blocking_message_show",
    "contextual_prompt_hide",
    "contextual_prompt_show",
    "display_blocking_message",
    "display_contextual_prompt",
    "display_message",
    "message_hide",
    "message_show",
    "show_big_notification",
    "show_hud_message",
    "show_reward_popup",
    "show_top_center_message",
)


def show_hud_message(title: str, msg: str, duration: float = 2.5) -> None:
    """
    Displays a short, non-blocking message in the main in game hud.

    Uses the same message style as those for respawning.

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


def show_big_notification(
    msg: str,
    ui_sound: unreal.UObject | None | EllipsisType = ...,
) -> None:
    """
    Displays a big notification message in the main in game hud.

    Uses the message style of the Second Wind notification.

    Note this message can only display up to 33 characters.

    Args:
        msg: The message to display.
        ui_sound: An optional AkEvent to play when the message is displayed.
            If Ellipsis, default sound will be used.
    """
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return

    sound_backup = None
    sw_interaction = None
    for gfx_movie in unrealsdk.find_all("GearboxGFxMovie", exact=False):
        for interaction in gfx_movie.InteractionOverrideSounds:
            if interaction.Interaction == "SecondWind":
                sound_backup = interaction.AkEvent
                sw_interaction = interaction
                break

    if ui_sound is not Ellipsis and sw_interaction:
        sw_interaction.AkEvent = ui_sound

    backup_string = hud_movie.SecondWindString
    hud_movie.SecondWindString = msg
    hud_movie.DisplaySecondWind()
    hud_movie.SecondWindString = backup_string
    if sw_interaction:
        sw_interaction.AkEvent = sound_backup


def show_top_center_message(msg: str, show_discovered_message: bool = False) -> None:
    """
    Displays a message in the top center of the screen.

    Uses the style of the new area discovered message.

    Note this message can only display up to 41 characters.

    Args:
        msg: The message to display.
        show_discovered_message: If True, the message 'You have discovered' header will show.
    """
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    hud_movie.ShowWorldDiscovery("", "msg", show_discovered_message, False)


def show_reward_popup(
    msg: str,
    reward_type: ERewardPopup = ERewardPopup.ERP_BadassToken,
) -> None:
    """
    Displays a reward popup with the given message and reward type.

    Note this message can only display up to 33 characters.

    Args:
        msg: The message to display in the popup.
        reward_type: The type of reward to display. Defaults to ERewardPopup.ERP_BadassToken.
    """
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return

    icon = {
        ERewardPopup.ERP_BadassToken: "token",
        ERewardPopup.ERP_CharacterHead: "head",
        ERewardPopup.ERP_CharacterSkin: "playerSkin",
        ERewardPopup.ERP_VehicleSkin: "vehicleSkin",
    }.get(reward_type, "token")

    hud_movie.SingleArgInvokeS("p1.badassToken.gotoAndStop", "stop")
    hud_movie.SingleArgInvokeS("p1.badassToken.gotoAndStop", "go")
    hud_movie.SingleArgInvokeS("p1.badassToken.inner.gotoAndStop", icon)
    hud_movie.SetVariableString("p1.badassToken.inner.dispText.text", msg)


def contextual_prompt_show(text: str, button_string: str) -> None:
    """
    Displays a contextual prompt with the given text and button string.

    Note both text and button_string can each display up to 16 characters.

    Args:
        text: The text top to display in the prompt.
        button_string: The button string to display in the prompt.
    """

    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    contextual_prompt = hud_movie.ContextualPromptButtonString
    hud_movie.ContextualPromptButtonString = button_string
    hud_movie.ToggleContextualPrompt(text, True)
    hud_movie.ContextualPromptButtonString = contextual_prompt


def contextual_prompt_hide() -> None:
    """Hides the currently displayed contextual prompt, if any."""
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    hud_movie.ToggleContextualPrompt("", False)


@contextmanager
def display_contextual_prompt(text: str, button_string: str) -> Iterator[None]:
    """
    Context manager to display and hide a contextual prompt.

    This will display the prompt when entering the context and hide it when exiting.

    Args:
        text: The text to display in the prompt.
        button_string: The button string to display in the prompt.
    """
    contextual_prompt_show(text, button_string)
    try:
        yield
    finally:
        contextual_prompt_hide()


def blocking_message_show(msg: str, reason: str | None = None) -> None:
    """
    Displays a blocking message with the given text.

    This message will block any input until it is hidden.

    Note this message has no character limit, but only scales horizontally.
    Multiple lines will not be displayed correctly.

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


def blocking_message_hide() -> None:
    """Hides the currently displayed blocking message, if any."""
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.HideBlocking()


@contextmanager
def display_blocking_message(msg: str, reason: str | None = None) -> Iterator[None]:
    """
    Context manager to display and hide a blocking message.

    This will display the message when entering the context and hide it when exiting.

    Args:
        msg: The message to display.
        reason: An optional reason for the blocking message, which will be displayed as a subtitle.
            If None, the default text will show.
    """
    blocking_message_show(msg, reason)
    try:
        yield
    finally:
        blocking_message_hide()


def message_show(msg: str) -> None:
    """
    Displays a message on the left side of the screen.

    Note this message has no character limit, but only scales horizontally.
    Multiple lines will not be displayed correctly.

    Args:
        msg: The message to display.
    """
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.DisplayMessage(msg)


def message_hide() -> None:
    """Hides the currently displayed message in the online message movie."""
    if (msg_movie := get_pc().GetOnlineMessageMovie()) is None:
        return

    msg_movie.Hide()


@contextmanager
def display_message(msg: str) -> Iterator[None]:
    """
    Context manager to display and hide a message.

    This will display the message when entering the context and hide it when exiting.

    Args:
        msg: The message to display.
    """
    message_show(msg)
    try:
        yield
    finally:
        message_hide()
