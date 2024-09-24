import warnings
from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any, Self

import unrealsdk
from unrealsdk.hooks import Block
from unrealsdk.unreal import BoundFunction, UObject, WeakPointer, WrappedStruct

from mods_base import EInputEvent, bind_all_hooks, get_pc, hook

if TYPE_CHECKING:
    from enum import auto

    from unrealsdk.unreal._uenum import UnrealEnum  # pyright: ignore[reportMissingModuleSource]

    class EBackButtonScreen(UnrealEnum):
        CS_None = auto()
        CS_MissionLog = auto()
        CS_Map = auto()
        CS_Inventory = auto()
        CS_Skills = auto()
        CS_Challenges = auto()
        CS_MAX = auto()

else:
    EBackButtonScreen = unrealsdk.find_enum("EBackButtonScreen")


@dataclass
class TrainingBox:
    """
    Handles displaying a training dialog box, like those used for the tutorial messages.

    Attributes:
        title: The title text to display at the top of the training box.
        message: The message to display in the main body of the training box.
        min_duration: How long to display the training box for before the user may close it.
        pauses_game: If the training box should pause the game while it is displayed.
        menu_hint: Which menu to hint at opening when you close this training box.
        priority: The priority of the training box in reference to the game's other movies.

    Callbacks:
        on_exit: Run when the training box is closed. Passed the training box.
        on_input: Run on any input while the training box is open. Passed the training box, the key
                  which was pressed, and the input event. May return the Block sentinel to block the
                  game from processing the given input.
    """

    _: KW_ONLY
    title: str
    message: str
    min_duration: float = 0
    pauses_game: bool = False
    menu_hint: EBackButtonScreen = EBackButtonScreen.CS_None
    priority: int = 254

    on_exit: Callable[[Self], None] | None = None
    on_input: Callable[[Self, str, EInputEvent], Block | type[Block] | None] | None = None

    _gfx_object: WeakPointer = field(init=False, default=WeakPointer(None))

    def __post_init__(self) -> None:
        # In case you open multiple dialogs at once, we don't want the identifier to conflict, so
        # that closing one removes the hook of the other
        # Don't want to use `id(self)`, so that these are still constant if you reload the module
        bind_all_hooks(self, f"{hash(self.title):x}:{hash(self.message):x}")

    def show(self) -> None:
        """Displays the training box."""
        pc = get_pc(possibly_loading=True)
        if pc is None:
            raise RuntimeError(
                "Unable to show training box since player controller could not be found!",
                self.message,
            )

        if self.is_showing():
            self.hide()

        dialog: UObject = pc.GFxUIManager.ShowTrainingDialog(
            self.message,
            self.title,
            self.min_duration,
            self.menu_hint,
            not self.pauses_game,
        )
        dialog.SetPriority(self.priority)
        dialog.ApplyLayout()
        self._gfx_object = WeakPointer(dialog)

        self._training_box_input_key.enable()
        self._training_box_on_close.enable()

    def is_showing(self) -> bool:
        """
        Checks if the training box is currently being displayed.

        Returns:
            True if the training box is currently being displayed, False otherwise.
        """
        return self._gfx_object() is not None

    def hide(self) -> None:
        """Hides the training box."""
        self._training_box_input_key.disable()
        self._training_box_on_close.disable()

        dialog = self._gfx_object()
        if dialog is None:
            warnings.warn("Tried to hide a training box which was already hidden", stacklevel=2)
            return

        dialog.Close()
        self._gfx_object = WeakPointer(None)

    def _is_correct_training_box(self, obj: UObject) -> bool:
        """
        Checks if the passed training box corresponds with this object.

        Args:
            obj: The object to check.
        Returns:
            True if the passed object is the correct training box to continue with.
        """
        dialog = self._gfx_object()

        # Clean up if our dialog got gc'd
        if dialog is None:
            self._training_box_input_key.disable()
            self._training_box_on_close.disable()
            return False

        return obj == dialog

    @hook("WillowGame.WillowGFxTrainingDialogBox:HandleInputKey")
    def _training_box_input_key(
        self,
        obj: UObject,
        args: WrappedStruct,
        _3: Any,
        _4: BoundFunction,
    ) -> Block | type[Block] | None:
        if not self._is_correct_training_box(obj):
            return None

        if self.on_input is not None:
            key: str = args.ukey
            event: EInputEvent = args.uevent
            return self.on_input(self, key, event)

        return None

    @hook("WillowGame.WillowGFxTrainingDialogBox:OnClose")
    def _training_box_on_close(
        self,
        obj: UObject,
        _2: WrappedStruct,
        _3: Any,
        _4: BoundFunction,
    ) -> None:
        if not self._is_correct_training_box(obj):
            return

        self._training_box_input_key.disable()
        self._training_box_on_close.disable()

        if self.on_exit is not None:
            self.on_exit(self)
