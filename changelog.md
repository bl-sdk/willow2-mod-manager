# Changelog

## v3.1: (codename tbd)

### [pyunrealsdk v1.5.1](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v151)
> - Changed type hinting of `unrealsdk.find_all` to return an `Iterable[UObject]`, instead of
>   `Iterator[UObject]`. This mirrors what was actually happening at runtime.

### [unrealsdk v1.6.0](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v160)
> - Handled `UStruct` differing in size between BL2 and TPS.

## v3.0: Sheriff's Badge
Completely rewrite. Broad overview:

- Upgraded to Python 3.13.1 (6 major versions!).
- Native Python modules (e.g. ctypes, ssl) are included by default.
- Added support for writing your own native Python modules which integrate with the SDK.
- Python's stdout and stderr are hooked up to the SDK's logging system.

- Hooks can now be explicitly specified as pre or post-hooks.
- Pre-hooks can now overwrite a function's return value.

- Several new property types are supported (e.g. attribute properties).
- Some types of properties return a more appropriate value - e.g. interface properties return the
  object directly, enum properties return a Python enum.

- Functions with an out array or out struct no longer result in a use after free, they now return
  valid references.

- The new `build_mod()` factory greatly reduces the boilerplate required to register a mod. 
- Mods are now expected to provide a `pyproject.toml`. Both `build_mod()` and the mod db (and maybe
  more in future) read from it.
- Mods can be exported as a single `.sdkmod` file, to help avoid installation issues.

See all the docstrings for more in-depth documentation.

## v2.5b / 0.7.11
This is a transitionary version, which doesn't quite follow the practices of versions either side of
it. At the time, we made no distinction between the mod *manager* and mod *menu*'s versions. This
version only upgraded the sdk, but made no changes to the mod menu since v2.5, and thus was given
the slightly odd "v2.5b" version.

- Fixed an issue where spurious exceptions would be created when using Wine/Proton, preventing a
  number of mods from running properly. These exceptions always took the form
  `SystemError: <...> returned NULL without setting an error`.

## Older
All older versions were developed alongside the sdk, in lockstep, as part of the
[PythonSDK](https://github.com/bl-sdk/PythonSDK/releases) repo, see it for a full changelog.
