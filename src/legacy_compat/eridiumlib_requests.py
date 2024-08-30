# This dummy module exists purely to pretend to be requests in EridiumLib
# There's some issue with running a version of six written for five major python versions ago, which
# blocks us from just loading the version it ships with
# Since EridiumLib blocks several other mods, and only uses it for a version check, we can just
# patch in this version instead to get them all working again


def get(url: str, timeout: int) -> str:  # noqa: D103
    raise NotImplementedError
