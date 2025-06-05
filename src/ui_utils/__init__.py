from mods_base.mod_list import base_mod

from .chat import show_chat_message
from .clipboard import clipboard_copy, clipboard_paste
from .hud_message import (
    ERewardPopup,
    blocking_message_hide,
    blocking_message_show,
    contextual_prompt_hide,
    contextual_prompt_show,
    display_blocking_message,
    display_contextual_prompt,
    display_message,
    message_hide,
    message_show,
    show_big_notification,
    show_hud_message,
    show_reward_popup,
    show_top_center_message,
)
from .option_box import OptionBox, OptionBoxButton
from .reorder_box import ReorderBox
from .training_box import EBackButtonScreen, TrainingBox

__all__: tuple[str, ...] = (
    "EBackButtonScreen",
    "ERewardPopup",
    "OptionBox",
    "OptionBoxButton",
    "ReorderBox",
    "TrainingBox",
    "__author__",
    "__version__",
    "__version_info__",
    "blocking_message_hide",
    "blocking_message_show",
    "clipboard_copy",
    "clipboard_paste",
    "contextual_prompt_hide",
    "contextual_prompt_show",
    "display_blocking_message",
    "display_contextual_prompt",
    "display_message",
    "message_hide",
    "message_show",
    "show_big_notification",
    "show_chat_message",
    "show_hud_message",
    "show_reward_popup",
    "show_top_center_message",
)

__version_info__: tuple[int, int] = (1, 3)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


base_mod.components.append(base_mod.ComponentInfo("UI Utils", __version__))
