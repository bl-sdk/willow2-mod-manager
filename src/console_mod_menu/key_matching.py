from os import path

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
}


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


def suggest_key(invalid_key: str) -> str | None:
    """
    Given an invalid key name, suggest what the user might have misspelt.

    Args:
        invalid_key: the invalid key name
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

    return suggestion
