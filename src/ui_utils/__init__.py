from mods_base.mod_list import base_mod

from .chat import show_chat_message
from .clipboard import clipboard_copy, clipboard_paste
from .hud_message import show_hud_message

__all__: tuple[str, ...] = (
    "__author__",
    "__version__",
    "__version_info__",
    "clipboard_copy",
    "clipboard_paste",
    "show_chat_message",
    "show_hud_message",
)

__version_info__: tuple[int, int] = (1, 0)
__version__: str = f"{__version_info__[0]}.{__version_info__[1]}"
__author__: str = "bl-sdk"


base_mod.components.append(base_mod.ComponentInfo("UI Utils", __version__))
