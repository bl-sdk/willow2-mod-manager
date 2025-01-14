from mods_base.mod_list import base_mod

from .chat import show_chat_message
from .clipboard import clipboard_copy, clipboard_paste
from .hud_message import show_hud_message
from .option_box import OptionBox, OptionBoxButton
from .reorder_box import ReorderBox
from .training_box import EBackButtonScreen, TrainingBox

__all__: tuple[str, ...] = (
    "EBackButtonScreen",
    "OptionBox",
    "OptionBoxButton",
    "ReorderBox",
    "TrainingBox",
    "__author__",
    "__version__",
    "__version_info__",
    "clipboard_copy",
    "clipboard_paste",
    "show_chat_message",
    "show_hud_message",
)

__version_info__: tuple[int, int] = (1, 1)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


base_mod.components.append(base_mod.ComponentInfo("UI Utils", __version__))
