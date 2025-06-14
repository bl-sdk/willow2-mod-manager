from mods_base.mod_list import base_mod

from .chat import show_chat_message
from .clipboard import clipboard_copy, clipboard_paste
from .hud_message import (
    ERewardPopup,
    hide_button_prompt,
    show_button_prompt,
    show_discovery_message,
    show_hud_message,
    show_reward_popup,
    show_second_wind_notification,
)
from .online_message import (
    hide_blocking_message,
    hide_coop_message,
    show_blocking_message,
    show_coop_message,
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
    "clipboard_copy",
    "clipboard_paste",
    "hide_blocking_message",
    "hide_button_prompt",
    "hide_coop_message",
    "show_blocking_message",
    "show_button_prompt",
    "show_chat_message",
    "show_coop_message",
    "show_discovery_message",
    "show_hud_message",
    "show_reward_popup",
    "show_second_wind_notification",
)

__version_info__: tuple[int, int] = (1, 4)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


base_mod.components.append(base_mod.ComponentInfo("UI Utils", __version__))
