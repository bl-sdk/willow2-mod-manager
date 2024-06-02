import zipfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from io import TextIOWrapper
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO, Literal, overload


@overload
def open_in_mod_dir(
    path: Path,
    binary: Literal[False] = False,
) -> AbstractContextManager[IO[str]]: ...


@overload
def open_in_mod_dir(path: Path, binary: Literal[True]) -> AbstractContextManager[IO[bytes]]: ...


@contextmanager
def open_in_mod_dir(
    path: Path,
    binary: bool = False,
) -> Iterator[IO[str]] | Iterator[IO[bytes]]:
    """
    Opens a file in a mod folder for reading, handling possibly being inside a .sdkmod.

    Transforms the `KeyError` from a file not existing in a zip into a `FileNotFoundError` - so you
    only need to catch a single exception.

    Args:
        path: The path to open. This should generally be constructed relative to `__file__`.
        binary: True if to open in binary mode.
    Returns:
        An open file object.
    """
    dot_sdkmod = next(
        (p for p in path.parents if p.is_file() and p.suffix == ".sdkmod"),
        None,
    )

    # If we don't have a .sdkmod, if we're just an actual directory
    if dot_sdkmod is None:
        # Use a plain open

        # Separate the two paths for type hinting
        if binary:
            with path.open("rb") as file:
                yield file
        else:
            with path.open("r") as file:
                yield file

        return

    # If in a .sdkmod
    with zipfile.ZipFile(str(dot_sdkmod)) as zip_file:
        # Ensure the path has posix separators
        relative_path = path.relative_to(dot_sdkmod)

        # According to the standard, zip files are suppoosed to use posix separators
        # However, some old programs throw windows ones in
        # If we don't see the file, try the other separator - and if that fails just let the
        # exception bubble up
        inner_path = zipfile.Path(zip_file, str(PurePosixPath(relative_path)))
        if not inner_path.exists():
            inner_path = zipfile.Path(zip_file, str(PureWindowsPath(relative_path)))

        try:
            file = inner_path.open("rb")
        except KeyError as ex:
            raise FileNotFoundError from ex

        with file:
            if binary:
                yield file
            else:
                yield TextIOWrapper(file)
