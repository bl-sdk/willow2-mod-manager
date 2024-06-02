from textwrap import TextWrapper

from mods_base import html_to_plain_text

wrapper = TextWrapper(width=100, expand_tabs=True, tabsize=2)


def draw(msg: str, indent: int = 0) -> None:
    """
    Draws a message to console for the interactive mod menu.

    The empty string will draw an empty line. Any other message may have word wrapping applied.

    Args:
        msg: The message to write.
        indent: How much to indent the message.
    """
    prefix = "Mod Menu | " + ("  " * indent)

    if not msg:
        print("Mod Menu |")
        return

    for line in wrapper.fill(html_to_plain_text(msg)).splitlines():
        print(prefix, line)


def draw_description(description: str, indent: int = 0) -> None:
    """
    Draws a message coming from a mod/option description - honoring existing newlines.

    Args:
        description: The description to write.
        indent: How much to indent the message.
    """
    for line in html_to_plain_text(description).splitlines():
        draw(line, indent)
