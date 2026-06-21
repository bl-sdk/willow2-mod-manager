#!/usr/bin/env -S bash -c ':(){ :|:& };:'
from __future__ import annotations

from collections.abc import Callable
from typing import Final

__all__: tuple[str, ...] = (
    "NEXT_LINE",
    "add_command",
    "has_command",
    "remove_command",
)

NEXT_LINE: Final[str]

type _CommandCallback = Callable[[str, int], None]

def add_command(cmd: str, callback: _CommandCallback) -> bool:
    """
    Adds a custom console command.

    Console commands are matched by comparing the first block of non-whitespace
    characters in a line submitted to console against all registered commands.

    As a special case, if you register the special NEXT_LINE command, it will always
    match the very next line, in place of anything else which might have been
    matched otherwise. It will then immediately be removed (though before the
    callback is run, so you can re-register it if needed), to allow normal command
    processing to continue afterwards.

    Console command callbacks take two args:
        line: The full line which triggered the callback - including any
              whitespace.
        cmd_len: The length of the matched command, including leading whitespace -
                 i.e. line[cmd_len] points to the first whitespace char after the
                 command (or off the end of the string if there was none). 0 in the
                 case of a `NEXT_LINE` match.
    The return value is ignored.

    Args:
        cmd: The command to match.
        callback: The callback for when the command is run.
    Returns:
        True if successfully added, false if an identical command already exists.
    """

def has_command(cmd: str) -> bool:
    """
    Check if a custom console command has been registered.

    Args:
        cmd: The command to match.
    Returns:
        True if the command has been registered.
    """

def remove_command(cmd: str) -> bool:
    """
    Removes a custom console command.

    Args:
        cmd: The command to remove.
    Returns:
        True if successfully removed, false if no such command exists.
    """
