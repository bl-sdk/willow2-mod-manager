from __future__ import annotations

import argparse
import shlex
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, overload

from unrealsdk.commands import NEXT_LINE, add_command, has_command, remove_command


@dataclass
class AbstractCommand(ABC):
    cmd: str

    def __post_init__(self) -> None:
        for char in " \f\n\r\t\v":
            if char in self.cmd:
                raise ValueError("Command cannot contain whitespace")

    @abstractmethod
    def _handle_cmd(self, line: str, cmd_len: int) -> None:
        """
        Handles the command being run.

        Args:
            line: The full line which triggered the callback - including any whitespace.
            cmd_len: The length of the matched command, including leading whitespace - i.e.
                     `line[cmd_len]` points to the first whitespace char after the command (or off
                     the end of the string if there was none).
        """
        raise NotImplementedError

    def enable(self) -> None:
        """Enables this command."""
        self.disable()
        add_command(self.cmd, self._handle_cmd)

    def disable(self) -> None:
        """Disables this command."""
        remove_command(self.cmd)

    def is_registered(self) -> bool:
        """
        Checks if a command matching this one is registered.

        Note this doesn't necessarily mean it's registered to this command.

        Returns:
            True if a command matching this one is registered.
        """
        return has_command(self.cmd)


type ARGPARSE_CALLBACK = Callable[[argparse.Namespace], None]
type ARGPARSE_SPLITTER = Callable[[str], list[str]]


@dataclass
class ArgParseCommand(AbstractCommand):
    callback: ARGPARSE_CALLBACK
    parser: argparse.ArgumentParser
    splitter: ARGPARSE_SPLITTER

    def _handle_cmd(self, line: str, cmd_len: int) -> None:
        try:
            args = self.parser.parse_args(self.splitter(line[cmd_len:]))
            self.callback(args)
        # Help/version/invalid args all call exit by default, just suppress that
        except SystemExit:
            pass

    def add_argument(self, *args: Any, **kwargs: Any) -> argparse.Action:
        """Wrapper which forwards to the parser's add_argument method."""
        return self.parser.add_argument(*args, **kwargs)

    def __call__(self, args: argparse.Namespace) -> None:
        """Wrapper which forwards to the callback."""
        self.callback(args)


@overload
def command(
    cmd: str | None = None,
    splitter: ARGPARSE_SPLITTER = shlex.split,
    **kwargs: Any,
) -> Callable[[ARGPARSE_CALLBACK], ArgParseCommand]: ...


@overload
def command(callback: ARGPARSE_CALLBACK, /) -> ArgParseCommand: ...


def command(
    cmd: str | None | ARGPARSE_CALLBACK = None,
    splitter: ARGPARSE_SPLITTER = shlex.split,
    **kwargs: Any,
) -> Callable[[ARGPARSE_CALLBACK], ArgParseCommand] | ArgParseCommand:
    """
    Decorator factory to create an argparse command.

    Note this returns the command object, not a function, so should always be the outermost level.

    Args:
        cmd: The command to register. If None, defaults to the wrapped function's name.
        splitter: A function which splits the full command line into individual args.
        **kwargs: Passed to `ArgumentParser` constructor.
    """
    # Disambiguate between being called as a decorator or a decorator factory
    cmd_name: str | None = None
    callback: ARGPARSE_CALLBACK | None = None
    if isinstance(cmd, Callable):
        callback = cmd
    else:
        cmd_name = cmd
    del cmd

    def decorator(func: Callable[[argparse.Namespace], None]) -> ArgParseCommand:
        nonlocal cmd_name
        cmd_name = cmd_name or func.__name__

        # It's important to set `prog`, since otherwise it defaults to `sys.argv[0]`, which causes
        # an index error since it's empty
        if "prog" not in kwargs:
            kwargs["prog"] = cmd_name

        return ArgParseCommand(cmd_name, func, argparse.ArgumentParser(**kwargs), splitter)

    if callback is None:
        return decorator

    return decorator(callback)


def capture_next_console_line(callback: Callable[[str], None]) -> None:
    """
    Captures the very next line submitted to console, regardless of what it is.

    Only triggers once. May re-register during the callback to capture multiple lines.

    Args:
        callback: The callback to run when  the next line is submitted.
    """
    if has_command(NEXT_LINE):
        raise RuntimeError(
            "Tried to register a next console line callback when one was already registered!",
        )

    add_command(NEXT_LINE, lambda line, _: callback(line))


def remove_next_console_line_capture() -> None:
    """If a next console line capture is currently active, removes it."""
    remove_command(NEXT_LINE)
