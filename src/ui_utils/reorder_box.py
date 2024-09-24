import warnings
from collections.abc import Callable, MutableSequence
from dataclasses import KW_ONLY, dataclass, field
from typing import Any, Literal, Self

from unrealsdk.hooks import Block

from mods_base import EInputEvent

from .option_box import OptionBox, OptionBoxButton, Page


@dataclass
class ReorderBox(OptionBox):
    """
    A custom option box where the entries may be re-ordered by the user.

    Compared to a regular options box, the 'on_select' and 'prevent_cancelling' fields can no longer
    be set, as all selection logic is overwritten. Use the 'on_move' callback instead.

    Attributes:
        title: The title text to display at the top of the reorder box.
        message: The message to display in the main body of the reorder box.
        tooltip: The tooltip text to display in the footer of the reorder box.
        buttons: The buttons which the user may pick from. Must be mutable.
        priority: The priority of the reorder box in reference to the game's other movies.

    Callbacks:
        on_cancel: Run when the reorder box is cancelled out of without selecting a button. Passed
                   the reorder box.
        on_input: Run on any input while the reorder box is open. Passed the reorder box, the key
                  which was pressed, and the input event. May return the Block sentinel to block the
                  game from processing the given input.
        on_move: Called when a button is moved into it's new location, after the button list is
                 updated. Passed the reorder box and the button which was moved.
    """

    @staticmethod
    def create_tooltip_string(
        enter_message: str = "Select",
        esc_message: str = "Cancel",
        reorder_message: str = "Move",
    ) -> str:
        """
        Creates a tooltip string in the same format the game uses, but with custom messages.

        Args:
            enter_message: The message to display after the enter prompt.
            esc_message: The message to display after the escape prompt.
            reorder_message: The message to display after the up.down prompt.
        Returns:
            A string in the same format as the game's tooltips, but with your custom prompts.
        """
        return (
            f"<StringAliasMap:GFx_Accept> {enter_message}"
            "     "
            f"[Up / Down] {reorder_message}"
            "     "
            f"<StringAliasMap:GFx_Cancel> {esc_message}"
        )

    _: KW_ONLY
    tooltip: str = field(default=create_tooltip_string())
    buttons: MutableSequence[OptionBoxButton] = field(default_factory=list, repr=False)  # pyright: ignore[reportIncompatibleVariableOverride]

    on_move: Callable[[Self, OptionBoxButton], None] | None = None

    _is_currently_moving: bool = field(init=False, repr=False, default=False)

    # Stub properties from parent class

    prevent_cancelling: Literal[False] = field(init=False, default=False)  # pyright: ignore[reportRedeclaration, reportAssignmentType]

    @property
    def prevent_cancelling(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]  # noqa: D102, F811
        return False

    @prevent_cancelling.setter
    def prevent_cancelling(self, value: bool) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        if not isinstance(value, property) and value:  # pyright: ignore[reportUnnecessaryIsInstance]
            warnings.warn("Cannot prevent cancelling on a ReorderBox", stacklevel=2)

    on_select: None = field(init=False, default=None)  # pyright: ignore[reportRedeclaration, reportAssignmentType]

    @property
    def on_select(self) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]  # noqa: D102, F811
        return None

    @on_select.setter
    def on_select(self, value: Callable[[Self, OptionBoxButton], None] | None) -> None:  # pyright: ignore[reportIncompatibleVariableOverride]
        if not isinstance(value, property) and value is not None:  # pyright: ignore[reportUnnecessaryIsInstance]
            warnings.warn("Cannot set a select callback on a ReorderBox", stacklevel=2)

    # Really just redefining this for a different docstring
    def get_selected_button(self) -> OptionBoxButton:
        """
        While the option box is open, gets which button the user has selected.

        Note that if a button is currently being moved (and thus this function would return it) then
        it's name will be prefixed with "-- " and suffixed with " --".

        Returns:
            The currently selected button.
        """
        return super().get_selected_button()

    def _create_pages(self) -> None:
        # Every page has all args common *except* for the buttons
        kwargs: dict[str, Any] = {
            "title": self.title,
            "message": self.message,
            "tooltip": self.tooltip,
            "prevent_cancelling": self.prevent_cancelling,
            "priority": self.priority,
            "on_select": self._paging_on_select,
            "on_input": self._paging_on_input,
            "on_cancel": self._paging_on_cancel,
        }

        if len(self.buttons) <= 5:  # noqa: PLR2004
            self._pages = [Page(buttons=self.buttons, **kwargs)]
        else:
            # First page has 4 normal buttons and the next button
            button_groups = [[*self.buttons[:4], self._next_page]]

            # Fill in all other pages with 3 normal buttons and next + previous
            button_groups += [
                [self._prev_page, *self.buttons[i : i + 3], self._next_page]
                for i in range(4, len(self.buttons), 3)
            ]
            # Remove the next page button from the last page
            button_groups[-1].pop()

            # If a single normal button got left on the last page, move it back to the previous page
            # replacing it's next page button
            if len(button_groups[-1]) == 2:  # noqa: PLR2004
                button_groups[-2][-1] = button_groups[-1][1]
                button_groups.pop()

            self._pages = [Page(buttons=group, **kwargs) for group in button_groups]

    def _paging_on_select(self, _: Page, button: OptionBoxButton) -> None:
        if self._is_currently_moving:
            button.name = button.name[3:-3]
            if self.on_move is not None:
                self.on_move(self, button)

            self._is_currently_moving = False
        else:
            button.name = f"-- {button.name} --"
            self._is_currently_moving = True

        self.show(button)

    def _paging_on_input(  # noqa: C901
        self,
        _: Page,
        key: str,
        event: EInputEvent,
    ) -> Block | type[Block] | None:
        current_index = self.buttons.index(self.get_selected_button())
        new_index: int

        match key, event:
            case "Up" | "Gamepad_LeftStick_Up", EInputEvent.IE_Pressed:
                new_index = max(current_index - 1, 0)
            case "Down" | "Gamepad_LeftStick_Down", EInputEvent.IE_Pressed:
                new_index = min(current_index + 1, len(self.buttons) - 1)

            case "PageUp" | "XboxTypeS_LeftTrigger", EInputEvent.IE_Pressed:
                # On page 1, return 3 (last in page 0)
                # On page n, return 3 after what page n-1 returned
                # F(n) = 3n
                # On page 0, return 0 - which fits in the formula already
                new_index = self._current_page_idx * 3

            case "PageDown" | "XboxTypeS_RightTrigger", EInputEvent.IE_Pressed:
                # On page 0, return 4 (first in page 1)
                # On page n, return 3 after what page n-1 returned
                # F(n) = 3n + 4
                # On the last page, return the last index
                new_index = (
                    len(self.buttons) - 1
                    if self._current_page_idx == (len(self._pages) - 1)
                    else (3 * self._current_page_idx) + 4
                )

            case "Home", EInputEvent.IE_Pressed:
                # On page 1, return 4 (first in page 1)
                # On page n, return 3 after what page n-1 returned
                # F(n) = 3n + 1
                # On page 0, return 0
                new_index = 0 if self._current_page_idx == 0 else (3 * self._current_page_idx) + 1

            case "End", EInputEvent.IE_Pressed:
                # On page 0, return 3 (last in page 0)
                # On page n, return 3 after what page n-1 returned
                # F(n) = 3(n + 1)
                # On the last page, return the last index
                new_index = (
                    len(self.buttons) - 1
                    if self._current_page_idx == (len(self._pages) - 1)
                    else 3 * (self._current_page_idx + 1)
                )

            case _, _:
                if self.on_input is not None:
                    return self.on_input(self, key, event)
                return None

        if new_index != current_index:
            self.hide()

            if self._is_currently_moving:
                self.buttons.insert(new_index, self.buttons.pop(current_index))

            self.show(self.buttons[new_index])

        return Block
