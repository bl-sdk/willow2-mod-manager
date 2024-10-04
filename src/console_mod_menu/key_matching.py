from collections.abc import Iterable
from os import path

from mods_base import Game

# region Known Keys

KNOWN_UE3_CONTROLLER_KEYS: set[str] = {
    "Gamepad_LeftStick_Down",
    "Gamepad_LeftStick_Left",
    "Gamepad_LeftStick_Right",
    "Gamepad_LeftStick_Up",
    "Gamepad_RightStick_Down",
    "Gamepad_RightStick_Left",
    "Gamepad_RightStick_Right",
    "Gamepad_RightStick_Up",
    "XboxTypeS_A",
    "XboxTypeS_B",
    "XboxTypeS_Back",
    "XboxTypeS_DPad_Down",
    "XboxTypeS_DPad_Left",
    "XboxTypeS_DPad_Right",
    "XboxTypeS_DPad_Up",
    "XboxTypeS_LeftShoulder",
    "XboxTypeS_LeftThumbStick",
    "XboxTypeS_LeftTrigger",
    "XboxTypeS_LeftTriggerAxis",
    "XboxTypeS_LeftX",
    "XboxTypeS_LeftY",
    "XboxTypeS_RightShoulder",
    "XboxTypeS_RightThumbStick",
    "XboxTypeS_RightTrigger",
    "XboxTypeS_RightTriggerAxis",
    "XboxTypeS_RightX",
    "XboxTypeS_RightY",
    "XboxTypeS_Start",
    "XboxTypeS_X",
    "XboxTypeS_Y",
}

KNOWN_UE4_CONTROLLER_KEYS: set[str] = {
    "Gamepad_DPad_Down",
    "Gamepad_DPad_Left",
    "Gamepad_DPad_Right",
    "Gamepad_DPad_Up",
    "Gamepad_FaceButton_Bottom",
    "Gamepad_FaceButton_Left",
    "Gamepad_FaceButton_Right",
    "Gamepad_FaceButton_Top",
    "Gamepad_LeftShoulder",
    "Gamepad_LeftThumbstick",
    "Gamepad_LeftTrigger",
    "Gamepad_LeftTriggerAxis",
    "Gamepad_LeftX",
    "Gamepad_LeftY",
    "Gamepad_RightShoulder",
    "Gamepad_RightThumbstick",
    "Gamepad_RightTrigger",
    "Gamepad_RightTriggerAxis",
    "Gamepad_RightX",
    "Gamepad_RightY",
    "Gamepad_Special_Left",
    "Gamepad_Special_Right",
}

KNOWN_KEYS: set[str] = {
    "A",
    "Add",
    "Apostrophe",
    "Asterix",
    "B",
    "BackSpace",
    "Backslash",
    "C",
    "CapsLock",
    "Comma",
    "D",
    "Decimal",
    "Delete",
    "Divide",
    "Down",
    "E",
    "Eight",
    "End",
    "Enter",
    "Equals",
    "Escape",
    "F",
    "F1",
    "F10",
    "F11",
    "F12",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "Five",
    "Four",
    "G",
    "H",
    "Home",
    "Hyphen",
    "I",
    "Insert",
    "J",
    "K",
    "L",
    "Left",
    "LeftAlt",
    "LeftBracket",
    "LeftControl",
    "LeftMouseButton",
    "LeftShift",
    "M",
    "MiddleMouseButton",
    "MouseScrollDown",
    "MouseScrollUp",
    "MouseWheelAxis",
    "Multiply",
    "N",
    "Nine",
    "NumLock",
    "NumPadEight",
    "NumPadFive",
    "NumPadFour",
    "NumPadNine",
    "NumPadOne",
    "NumPadSeven",
    "NumPadSix",
    "NumPadThree",
    "NumPadTwo",
    "NumPadZero",
    "O",
    "One",
    "P",
    "PageDown",
    "PageUp",
    "Pause",
    "Period",
    "Q",
    "R",
    "Right",
    "RightAlt",
    "RightBracket",
    "RightControl",
    "RightMouseButton",
    "RightShift",
    "S",
    "ScrollLock",
    "Semicolon",
    "Seven",
    "Six",
    "Slash",
    "SpaceBar",
    "Subtract",
    "T",
    "Tab",
    "Three",
    "ThumbMouseButton",
    "ThumbMouseButton2",
    "Tilde",
    "Two",
    "U",
    "Up",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "Zero",
    *(KNOWN_UE3_CONTROLLER_KEYS if Game.get_tree() == Game.Willow2 else KNOWN_UE4_CONTROLLER_KEYS),
}

# endregion
# region Misspellings

# Python has code to suggest other names on an attribute or name error - we want to do the same when
# someone gives an invalid key name.
# Unfortunately, it doesn't seem to be exposed, so we manually replicate it instead
# Based on Python/suggestions.c:calculate_suggestions

# ruff: noqa: ERA001

MOVE_COST = 2
CASE_COST = 1
MAX_STRING_SIZE = 40


def _substitution_cost(a: str, b: str) -> int:
    if a == b:
        return 0
    if a.lower() == b.lower():
        return CASE_COST

    return MOVE_COST


def _levenshtein_distance(a: str, b: str, max_cost: int) -> int:
    """Calculate the Levenshtein distance between string1 and string2."""

    # Both strings are the same
    if a == b:
        return 0

    # Trim away common affixes.
    common_prefix = path.commonprefix((a, b))
    a = a.removeprefix(common_prefix)
    b = b.removeprefix(common_prefix)

    common_suffix = path.commonprefix((a[::-1], b[::-1]))
    a = a.removesuffix(common_suffix)
    b = b.removesuffix(common_suffix)

    a_size = len(a)
    b_size = len(b)
    if a_size == 0 or b_size == 0:
        return (a_size + b_size) * MOVE_COST

    if a_size > MAX_STRING_SIZE or b_size > MAX_STRING_SIZE:
        return max_cost + 1

    # Prefer shorter buffer
    if b_size < a_size:
        a, b = b, a
        a_size, b_size = b_size, a_size

    # quick fail when a match is impossible.
    if (b_size - a_size) * MOVE_COST > max_cost:
        return max_cost + 1

    # Instead of producing the whole traditional len(a)-by-len(b)
    # matrix, we can update just one row in place.
    # Initialize the buffer row
    # cost from b[:0] to a[:i+1]
    buffer = [(i + 1) * MOVE_COST for i in range(a_size)]

    result = 0
    for b_index in range(b_size):
        code = b[b_index]
        # cost(b[:b_index], a[:0]) == b_index * MOVE_COST
        distance = result = b_index * MOVE_COST
        minimum = None
        for index in range(a_size):
            # cost(b[:b_index+1], a[:index+1]) = min(
            #     # 1) substitute
            #     cost(b[:b_index], a[:index])
            #         + substitution_cost(b[b_index], a[index]),
            #     # 2) delete from b
            #     cost(b[:b_index], a[:index+1]) + MOVE_COST,
            #     # 3) delete from a
            #     cost(b[:b_index+1], a[index]) + MOVE_COST
            # )

            # 1) Previous distance in this row is cost(b[:b_index], a[:index])
            substitute = distance + _substitution_cost(code, a[index])
            # 2) cost(b[:b_index], a[:index+1]) from previous row
            distance = buffer[index]
            # 3) existing result is cost(b[:b_index+1], a[index])

            insert_delete = min(result, distance) + MOVE_COST
            result = min(insert_delete, substitute)

            # cost(b[:b_index+1], a[:index+1])
            buffer[index] = result
            if minimum is None or result < minimum:
                minimum = result
        if minimum is None or minimum > max_cost:
            # Everything in this row is too big, so bail early.
            return max_cost + 1
    return result


def suggest_misspelt_key(invalid_key: str) -> Iterable[str]:
    """
    Given an invalid key name, suggest a misspelling.

    Args:
        invalid_key: The invalid key name.
    Returns:
        A list of possible misspellings (which may be empty).
    """
    suggestion_distance: int | None = None
    suggestion: str | None = None
    for item in KNOWN_KEYS:
        if item == invalid_key:
            continue

        # No more than 1/3 of the involved characters should need changed.
        max_distance = (len(invalid_key) + len(item) + 3) * MOVE_COST // 6

        # Don't take matches we've already beaten.
        if suggestion_distance is not None and (suggestion_distance - 1) < max_distance:
            max_distance = suggestion_distance - 1

        current_distance = _levenshtein_distance(invalid_key, item, max_distance)

        if current_distance > max_distance:
            continue
        if (
            suggestion is None
            or suggestion_distance is None
            or current_distance < suggestion_distance
        ):
            suggestion = item
            suggestion_distance = current_distance

    if suggestion is None:
        return ()
    return (suggestion,)


# endregion
# region Symbols

SYMBOL_NAMES: dict[str, tuple[str, ...]] = {
    # Ignoring the symbols which require shift
    "-": ("Hyphen", "Subtract"),
    ",": ("Comma",),
    ";": ("Semicolon",),
    ".": ("Decimal", "Period"),
    "'": ("Apostrophe",),
    "[": ("LeftBracket",),
    "]": ("RightBracket",),
    "*": ("Asterix", "Multiply"),
    "/": ("Divide", "Slash"),
    "\\": ("Backslash",),
    "+": ("Add",),
    "=": ("Equals",),
    "~": ("Tilde",),
    "0": ("Zero", "NumPadZero"),
    "1": ("One", "NumPadOne"),
    "2": ("Two", "NumPadTwo"),
    "3": ("Three", "NumPadThree"),
    "4": ("Four", "NumPadFour"),
    "5": ("Five", "NumPadFive"),
    "6": ("Six", "NumPadSix"),
    "7": ("Seven", "NumPadSeven"),
    "8": ("Eight", "NumPadEight"),
    "9": ("Nine", "NumPadNine"),
}


def suggest_symbol_name(invalid_key: str) -> Iterable[str]:
    """
    Given an invalid key name, check if it's referencing to a symbol instead of its name.

    Args:
        invalid_key: The invalid key name.
    Returns:
        A list of possible names (which may be empty).
    """
    return SYMBOL_NAMES.get(invalid_key, ())


# endregion


def suggest_keys(invalid_key: str) -> Iterable[str]:
    """
    Given an invalid key name, suggest what the user might have intended.

    Args:
        invalid_key: The invalid key name.
    """
    return (
        *suggest_misspelt_key(invalid_key),
        *suggest_symbol_name(invalid_key),
    )
