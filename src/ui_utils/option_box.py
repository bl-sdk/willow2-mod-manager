from __future__ import annotations

import warnings
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Self

from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import EInputEvent, bind_all_hooks, get_pc, hook

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


__all__: tuple[str, ...] = (
    "OptionBox",
    "OptionBoxButton",
    "Page",
)


@dataclass
class OptionBoxButton:
    """
    One of the buttons you may select in an option box.

    Attributes:
        name: The name that the button should have.
        tip: A string that is added to the option box caption when hovering over this button.
    """

    name: str
    tip: str = ""


@dataclass
class OptionBox:
    """
    Handles displaying an option box, like those used to confirm playthrough.

    Attributes:
        title: The title text to display at the top of the option box.
        message: The message to display in the main body of the option box.
        tooltip: The tooltip text to display in the footer of the option box.
        buttons: The buttons which the user may pick from.
        prevent_cancelling: If True, prevents pressing ESC to cancel out without selecting anything.
        priority: The priority of the option box in reference to the game's other movies.

    Callbacks:
        on_select: Run when a button in the option box is selected. Passed the option box and the
                   button which was selected.
        on_cancel: Run when the option box is cancelled out of without selecting a button. Passed
                   the option box.
        on_input: Run on any input while the option box is open. Passed the option box, the key
                  which was pressed, and the input event. May return the Block sentinel to block the
                  game from processing the given input.
    """

    @staticmethod
    def create_tooltip_string(enter_message: str = "Select", esc_message: str = "Cancel") -> str:
        """
        Creates a tooltip string in the same format the game uses, but with custom messages.

        Args:
            enter_message: The message to display after the enter prompt.
            esc_message: The message to display after the escape prompt.
        Returns:
            A string in the same format as the game's tooltips, but with your custom prompts.
        """
        return (
            f"<StringAliasMap:GFx_Accept> {enter_message}"
            "     "
            f"<StringAliasMap:GFx_Cancel> {esc_message}"
        )

    _: KW_ONLY
    title: str
    message: str = ""
    tooltip: str = field(default=create_tooltip_string())
    buttons: Sequence[OptionBoxButton] = field(default=(), repr=False)
    prevent_cancelling: bool = False
    priority: int = 254

    on_select: Callable[[Self, OptionBoxButton], None] | None = None
    on_cancel: Callable[[Self], None] | None = None
    on_input: Callable[[Self, str, EInputEvent], Block | type[Block] | None] | None = None

    _gfx_object: WeakPointer = field(init=False, repr=False, default=WeakPointer())

    _pages: list[Page] = field(init=False, repr=False, default_factory=list["Page"])
    _current_page_idx: int = field(init=False, repr=False, default=0)

    # While we don't display previous page, defining one for use in subclasses
    _next_page: ClassVar[OptionBoxButton] = OptionBoxButton("Next Page")
    _prev_page: ClassVar[OptionBoxButton] = OptionBoxButton("Previous Page")

    def show(self, button: OptionBoxButton | None = None) -> None:
        """
        Displays the options box.

        Args:
            button: The button to try select by default, or None to select the first button.
        """
        if button is None:
            button = self.buttons[0]
        elif button not in self.buttons:
            raise ValueError(f"button is not in list: {button}")

        if self.is_showing():
            self.hide()

        self._create_pages()
        self._current_page_idx = 0

        for idx, page in enumerate(self._pages):
            if button in page.buttons:
                self._current_page_idx = idx
                page.show(button)
                return

    def is_showing(self) -> bool:
        """
        Checks if the option box is currently being displayed.

        Returns:
            True if the option box is currently being displayed, False otherwise.
        """
        if not self._pages:
            return False
        return self._pages[self._current_page_idx].is_showing()

    def hide(self) -> None:
        """Hides the training box."""
        if not self.is_showing():
            warnings.warn("Tried to hide a training box which was already hidden", stacklevel=2)
            return
        self._pages[self._current_page_idx].hide()
        self._pages.clear()

    def get_selected_button(self) -> OptionBoxButton:
        """
        While the option box is open, gets which button the user has selected.

        Returns:
            The currently selected button.
        """
        if not self.is_showing():
            raise RuntimeError(
                "Cannot get selected button of an option box that is not currently showing!",
            )
        return self._pages[self._current_page_idx].get_selected_button()

    def _create_pages(self) -> None:
        """Creates a new set of pages using the current settings."""

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
            self._pages = [
                Page(buttons=[*self.buttons[i : i + 4], self._next_page], **kwargs)
                for i in range(0, len(self.buttons), 4)
            ]

    def _get_page_edge_button(self, *, first: bool) -> OptionBoxButton:
        """
        Gets the first button (which is not used for paging) on the edge of the current page.

        Args:
            first: If True, gets the first button. If False, gets the last button.
        Returns:
            The first button.
        """
        return next(
            button
            for button in self._pages[self._current_page_idx].buttons[:: 1 if first else -1]
            if button not in (self._next_page, self._prev_page)
        )

    def _hide_page(self) -> None:
        """Hides the current page if it is showing."""
        if not self._pages:
            return
        if not (current_page := self._pages[self._current_page_idx]).is_showing():
            return
        current_page.hide()

    def _home(self) -> None:
        """Reselects the first button on the currently shown page."""
        self._hide_page()
        self._pages[self._current_page_idx].show(self._get_page_edge_button(first=True))

    def _end(self) -> None:
        """Reselects the last button on the currently shown page."""
        self._hide_page()
        self._pages[self._current_page_idx].show(self._get_page_edge_button(first=False))

    def _page_up(self) -> None:
        """Moves to the previous page."""
        self._hide_page()
        self._current_page_idx = (self._current_page_idx - 1) % len(self._pages)

        if len(self._pages) == 1:
            # If there's only a single page, select the first item on it
            button = self._get_page_edge_button(first=True)
        else:
            # Otherwise, select the last item on the previous page
            button = self._get_page_edge_button(first=False)

        self._pages[self._current_page_idx].show(button)

    def _page_down(self) -> None:
        """Moves to the next page."""
        self._hide_page()
        self._current_page_idx = (self._current_page_idx + 1) % len(self._pages)

        if len(self._pages) == 1:
            # If there's only a single page, select the last item on it
            button = self._get_page_edge_button(first=False)
        else:
            # Otherwise, select the first item on the next page
            button = self._get_page_edge_button(first=True)

        self._pages[self._current_page_idx].show(button)

    def _paging_on_select(self, _: Page, button: OptionBoxButton) -> None:
        """Selection handler for the paging system."""
        if button == self._next_page:
            self._page_down()
        elif button == self._prev_page:
            self._page_up()
        elif self.on_select is not None:
            self._hide_page()
            self._pages.clear()
            self.on_select(self, button)

    def _paging_on_cancel(self, _: Page) -> None:
        """Cancel handler for the paging system."""
        self._hide_page()
        self._pages.clear()
        if self.on_cancel is not None:
            self.on_cancel(self)

    def _paging_on_input(
        self,
        _: Page,
        key: str,
        event: EInputEvent,
    ) -> Block | type[Block] | None:
        """Input handler for the paging system."""
        match key, event:
            case "PageUp" | "XboxTypeS_LeftTrigger", EInputEvent.IE_Pressed:
                self._page_up()
                return Block
            case "PageDown" | "XboxTypeS_RightTrigger", EInputEvent.IE_Pressed:
                self._page_down()
                return Block
            case "Home", EInputEvent.IE_Pressed:
                self._home()
                return Block
            case "End", EInputEvent.IE_Pressed:
                self._end()
                return Block

            case (
                "Up" | "Gamepad_LeftStick_Up",
                EInputEvent.IE_Pressed,
            ) if self.get_selected_button() == self._prev_page:
                self._page_up()
                return Block

            case (
                "Down" | "Gamepad_LeftStick_Down",
                EInputEvent.IE_Pressed,
            ) if self.get_selected_button() == self._next_page:
                self._page_down()
                return Block

            case _, _:
                if self.on_input is not None:
                    return self.on_input(self, key, event)
                return None


@dataclass
class Page:
    """
    Handles displaying a single option box "page". You should probably use OptionBox over this.

    The raw options boxes are a little awkward to work with, most notably due to only supporting a
    maximum of 5 buttons. OptionsBox adds extra logic to support multiple pages. You should only
    really need this class if you want to create your own paging logic from scratch.

    Attributes:
        title: The title text to display at the top of the option box.
        message: The message to display in the main body of the option box.
        tooltip: The tooltip text to display in the footer of the option box.
        buttons: The buttons which the user may pick from.
        prevent_cancelling: If True, prevents pressing ESC to cancel out without selecting anything.
        priority: The priority of the option box in reference to the game's other movies.

    Callbacks:
        on_select: Run when a button in the option box is selected. Passed the option box and the
                   button which was selected.
        on_cancel: Run when the option box is cancelled out of without selection a button. Passed
                   the option box.
        on_input: Run on any input while the option box is open. Passed the option box, the key
                  which was pressed, and the input event. May return the Block sentinel to block the
                  game from processing the given input.
    """

    _: KW_ONLY
    title: str
    message: str = ""
    tooltip: str = field(default=OptionBox.create_tooltip_string())
    buttons: Sequence[OptionBoxButton] = field(default=(), repr=False)
    prevent_cancelling: bool = False
    priority: int = 254

    on_select: Callable[[Self, OptionBoxButton], None] | None = None
    on_cancel: Callable[[Self], None] | None = None
    on_input: Callable[[Self, str, EInputEvent], Block | type[Block] | None] | None = None

    _gfx_object: WeakPointer = field(init=False, default=WeakPointer())

    def __post_init__(self) -> None:
        # In case you open multiple dialogs at once, we don't want the identifier to conflict, so
        # that closing one removes the hook of the other
        # Don't want to use `id(self)`, so that these are still constant if you reload the module
        bind_all_hooks(self, f"{hash(self.title):x}:{hash(self.message):x}")

    def show(self, button: OptionBoxButton | None = None) -> None:
        """
        Displays the options box.

        Args:
            button: The button to try select by default, or None to select the first button.
        """
        pc = get_pc(possibly_loading=True)
        if pc is None:
            raise RuntimeError(
                "Unable to show training box since player controller could not be found!",
                self.message,
            )

        if self.is_showing():
            self.hide()

        button_idx = 0 if button is None else self.buttons.index(button)

        dialog: UObject = pc.GFxUIManager.ShowDialog()
        dialog.SetText(self.title, self.message)
        dialog.SetTooltips(self.tooltip)
        dialog.SetPriority(self.priority)
        dialog.bNoCancel = self.prevent_cancelling

        # We give each button a tag based on index so that you can add two with the same name
        for idx, button_to_draw in enumerate(self.buttons):
            dialog.AppendButton(f"ui_utils:button:{idx}", button_to_draw.name, button_to_draw.tip)

        dialog.SetDefaultButton(f"ui_utils:button:{button_idx}", True)
        dialog.ApplyLayout()
        self._gfx_object = WeakPointer(dialog)

        self._enable_hooks()

    def is_showing(self) -> bool:
        """
        Checks if the option box is currently being displayed.

        Returns:
            True if the option box is currently being displayed, False otherwise.
        """
        return self._gfx_object() is not None

    def hide(self) -> None:
        """Hides the training box."""
        self._disable_hooks()

        dialog = self._gfx_object()
        if dialog is None:
            warnings.warn("Tried to hide an option box which was already hidden", stacklevel=2)
            return

        dialog.Close()
        self._gfx_object = WeakPointer()

    def get_selected_button(self) -> OptionBoxButton:
        """
        While the option box is open, gets which button the user has selected.

        Returns:
            The currently selected button.
        """
        dialog = self._gfx_object()
        if dialog is None:
            raise RuntimeError(
                "Cannot get selected button of an option box that is not currently showing!",
            )
        selection: int = dialog.CurrentSelection
        return self.buttons[selection]

    def _enable_hooks(self) -> None:
        """Enables all hooks required for this options box."""
        self._option_box_input_key.enable()
        self._option_box_accepted.enable()
        self._option_box_cancelled.enable()

    def _disable_hooks(self) -> None:
        """Disables all hooks required for this options box."""
        self._option_box_input_key.disable()
        self._option_box_accepted.disable()
        self._option_box_cancelled.disable()

    def _is_correct_option_box(self, obj: UObject) -> bool:
        """
        Checks if the passed option box corresponds with this object.

        Args:
            obj: The object to check.
        Returns:
            True if the passed object is the correct option box to continue with.
        """
        dialog = self._gfx_object()

        # Clean up if our dialog got gc'd
        if dialog is None:
            self._disable_hooks()
            return False

        return obj == dialog

    @hook("WillowGame.WillowGFxDialogBox:HandleInputKey")
    def _option_box_input_key(
        self,
        obj: UObject,
        args: WrappedStruct,
        _3: Any,
        _4: BoundFunction,
    ) -> Block | type[Block] | None:
        if not self._is_correct_option_box(obj):
            return None

        if self.on_input is not None:
            key: str = args.ukey
            event: EInputEvent = args.uevent
            return self.on_input(self, key, event)

        return None

    @hook("WillowGame.WillowGFxDialogBox:Accepted")
    def _option_box_accepted(
        self,
        obj: UObject,
        _2: WrappedStruct,
        _3: Any,
        _4: BoundFunction,
    ) -> None:
        if not self._is_correct_option_box(obj):
            return
        self._disable_hooks()

        if self.on_select is not None:
            self.on_select(self, self.get_selected_button())

    @hook("WillowGame.WillowGFxDialogBox:Cancelled")
    def _option_box_cancelled(
        self,
        obj: UObject,
        _2: WrappedStruct,
        _3: Any,
        _4: BoundFunction,
    ) -> None:
        if not self._is_correct_option_box(obj):
            return
        self._disable_hooks()

        if self.on_cancel is not None:
            self.on_cancel(self)
