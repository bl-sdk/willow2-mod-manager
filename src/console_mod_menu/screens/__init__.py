from abc import ABC, abstractmethod
from dataclasses import dataclass

from mods_base import capture_next_console_line

from console_mod_menu.draw import draw


@dataclass
class AbstractScreen(ABC):
    name: str

    @abstractmethod
    def draw(self) -> None:
        """Draws this screen."""
        raise NotImplementedError

    @abstractmethod
    def handle_input(self, line: str) -> bool:
        """
        Handles a user input.

        Args:
            line: The line the user submitted, with whitespace stripped.
        Returns:
            True if able to parse the line, false otherwise.
        """
        raise NotImplementedError


screen_stack: list[AbstractScreen] = []


def push_screen(new_screen: AbstractScreen) -> None:
    """
    Switches to a new screen.

    Args:
        new_screen: The new screen to switch to.
    """
    screen_stack.append(new_screen)


def pop_screen() -> None:
    """Closes the current screen."""
    screen_stack.pop()


_should_restart_interactive_menu: bool = False


def _handle_interactive_input(line: str) -> None:
    """Main input loop."""
    global _should_restart_interactive_menu
    stripped = line.strip()

    if stripped == (
        "Help I got the menu stuck in an infinite loop and need a debug option to break out!"
    ):
        return

    parsed_input = screen_stack[-1].handle_input(stripped)

    if len(screen_stack) > 0:
        screen_stack[-1].draw()
        capture_next_console_line(_handle_interactive_input)

    if not parsed_input:
        draw("")
        draw(f"Unrecognised input '{stripped}'.")

    if _should_restart_interactive_menu:
        start_interactive_menu()
    _should_restart_interactive_menu = False


def start_interactive_menu() -> None:
    """Starts the interactive mods menu."""
    screen_stack[:] = [home := HomeScreen()]
    home.draw()

    capture_next_console_line(_handle_interactive_input)


def quit_interactive_menu(restart: bool = False) -> None:
    """
    Tries to quits out of the interactive mods menu.

    May not quit if there are unsaved changes and the user does not discard.

    Args:
        restart: If true, immediately re-opens the menu on the home screen after closing.
    """
    global _should_restart_interactive_menu

    screen_stack.clear()

    if restart:
        _should_restart_interactive_menu = True


def draw_stack_header() -> None:
    """Draws a header combining all the items in the stack."""
    draw(" / ".join(x.name for x in screen_stack))


def draw_standard_commands() -> None:
    """Draws the standard commands which apply across all screens."""
    draw("[Q] Quit")

    if len(screen_stack) > 1:
        draw("[B] Back")

    draw("[?] Re-draw this screen")


def handle_standard_command_input(line: str) -> bool:
    """
    Checks if a user input matched a standard command, and processes it.

    Args:
        line: The line the user submitted, with whitespace stripped.
    Returns:
        True if able to parse the line, false otherwise.
    """
    match lower_line := line.lower():
        case "q" | "quit" | "exit" | "mods":
            quit_interactive_menu(restart=lower_line == "mods")
            return True

        case "b" | "back" if len(screen_stack) > 1:
            pop_screen()
            return True

        case "?" | "help":
            return True

        case _:
            return False


# Avoid circular imports
from .home import HomeScreen  # noqa: E402
