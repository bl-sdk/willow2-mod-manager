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
    "hide_button_prompt",
    "show_button_prompt",
    "show_discovery_message",
    "show_hud_message",
    "show_reward_popup",
    "show_second_wind_notification",
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


def show_second_wind_notification(
    msg: str,
    ui_sound: unreal.UObject | None | EllipsisType = ...,
) -> None:
    """
    Displays a big notification message in the main in game hud.

    Uses the message style of the Second Wind notification.

    Note this should not be used for critical messages, it may silently fail at any point.

    Args:
        msg: The message to display.
        ui_sound: An optional AkEvent to play when the message is displayed.
                  If Ellipsis, default sound will be used.
    """
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return

    sound_backup = None
    sw_interaction = None
    for interaction in hud_movie.InteractionOverrideSounds:
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


def show_discovery_message(msg: str, show_discovered_message: bool = False) -> None:
    """
    Displays a message in the top center of the screen.

    Uses the style of the new area discovered message.

    Note this should not be used for critical messages, it may silently fail at any point.

    Args:
        msg: The message to display.
        show_discovered_message: If True, the message 'You have discovered' header will show.
    """
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    hud_movie.ShowWorldDiscovery("", msg, show_discovered_message, False)


def show_reward_popup(
    msg: str,
    reward_type: ERewardPopup = ERewardPopup.ERP_BadassToken,
) -> None:
    """
    Displays a reward popup with the given message and reward type.

    Note this should not be used for critical messages, it may silently fail at any point.

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


def show_button_prompt(reason: str, button: str) -> None:
    """
    Displays a contextual prompt with the given text and button string.

    This will stay visible until it is explicitly hidden, see `hide_contextual_prompt`.

    Note this should not be used for critical messages, it may silently fail at any point.

    Args:
        reason: The text top to display in the prompt.
        button: The button string to display in the prompt.
    """

    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    contextual_prompt = hud_movie.ContextualPromptButtonString
    hud_movie.ContextualPromptButtonString = button
    hud_movie.ToggleContextualPrompt(reason, True)
    hud_movie.ContextualPromptButtonString = contextual_prompt


def hide_button_prompt() -> None:
    """Hides the currently displayed contextual prompt, if any."""
    if (hud_movie := get_pc().GetHUDMovie()) is None:
        return
    hud_movie.ToggleContextualPrompt("", False)
