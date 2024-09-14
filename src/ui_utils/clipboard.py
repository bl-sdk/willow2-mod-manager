import ctypes as ct
import ctypes.wintypes as wt

OpenClipboard = ct.windll.user32.OpenClipboard
OpenClipboard.argtypes = (wt.HWND,)
OpenClipboard.restype = wt.BOOL

CloseClipboard = ct.windll.user32.CloseClipboard
CloseClipboard.argtypes = ()
CloseClipboard.restype = wt.BOOL

EmptyClipboard = ct.windll.user32.EmptyClipboard
EmptyClipboard.argtypes = ()
EmptyClipboard.restype = wt.BOOL

GetClipboardData = ct.windll.user32.GetClipboardData
GetClipboardData.argtypes = (wt.UINT,)
GetClipboardData.restype = wt.HANDLE

SetClipboardData = ct.windll.user32.SetClipboardData
SetClipboardData.argtypes = (wt.UINT, wt.HANDLE)
SetClipboardData.restype = wt.HANDLE

GlobalLock = ct.windll.kernel32.GlobalLock
GlobalLock.argtypes = (wt.HANDLE,)
GlobalLock.restype = wt.LPVOID

GlobalUnlock = ct.windll.kernel32.GlobalUnlock
GlobalUnlock.argtypes = (wt.HGLOBAL,)
GlobalUnlock.restype = wt.BOOL

GlobalAlloc = ct.windll.kernel32.GlobalAlloc
GlobalAlloc.argtypes = (wt.UINT, ct.c_size_t)
GlobalAlloc.restype = wt.HGLOBAL


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x2


def clipboard_copy(contents: str) -> None:
    """
    Copies a string to the clipboard.

    Args:
        contents: The contents to copy.
    """
    if OpenClipboard(None):
        EmptyClipboard()

        # Don't need to do anything more if we have an empty string
        if contents:
            data = contents.encode("utf-16le") + b"\0\0"
            size = len(data)

            handle = GlobalAlloc(GMEM_MOVEABLE, size)
            if handle:
                locked_handle = GlobalLock(handle)
                if locked_handle:
                    ct.memmove(locked_handle, data, size)
                    GlobalUnlock(handle)

                    SetClipboardData(CF_UNICODETEXT, handle)

        CloseClipboard()


def clipboard_paste() -> str | None:
    """
    Pastes a string from the clipboard.

    Returns:
        The string in the clipboard, or None if it doesn't contain a string.
    """
    contents: str | None = None

    if OpenClipboard(None):
        handle = GetClipboardData(CF_UNICODETEXT)
        if handle:
            locked_handle = GlobalLock(handle)
            if locked_handle:
                contents = ct.wstring_at(locked_handle)

            GlobalUnlock(handle)

        CloseClipboard()

    return contents
