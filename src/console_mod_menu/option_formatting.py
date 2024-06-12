from typing import overload

from mods_base import JSON, BaseOption, BoolOption, KeybindOption, ValueOption

from .draw import draw, draw_description
from .screens import draw_stack_header


@overload
def get_option_value_str[J: JSON](option: ValueOption[J]) -> str: ...


@overload
def get_option_value_str(option: BaseOption) -> str | None: ...


def get_option_value_str(option: BaseOption) -> str | None:
    """
    Gets the string to use for the option's value.

    Args:
        option: The option to get the value string of.
    Returns:
        The option's value string, or None if it doesn't have a value.
    """
    match option:
        case BoolOption():
            return (option.false_text or "Off", option.true_text or "On")[option.value]
        case KeybindOption():
            key = str(option.value)
            if option.value is None:
                key = "Unbound"
            if option.is_rebindable:
                return key
            return f"Locked: {key}"
        case ValueOption():
            # The generics mean the type of value is technically unknown here
            return str(option.value)  # type: ignore
        case _:
            return None


def draw_option_header(option: BaseOption) -> None:
    """
    Draws the header for a particular option.

    Args:
        option: The option to draw the header for.
    """
    draw_stack_header()

    title = option.display_name
    value_str = get_option_value_str(option)
    if value_str is not None:
        title += f" ({value_str})"
    draw(title)

    if option.description_title != option.display_name:
        draw(option.description_title)

    if len(option.description) > 0:
        draw("=" * 32)
        draw_description(option.description)

    draw("")
