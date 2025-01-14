# Changelog

## v3.4 (upcoming)

### Networking v1.1
- Linting fixes.

### UI Utils v1.1
- Linting fixes.

## v3.3: Naught

### Keybinds v1.1
- Updated with new `mods_base` keybind interface, fixing that `is_enabled` wasn't being set.

### Legacy Compat v1.2
- Fixed that some more legacy mods would not auto-enable properly.
- Added more fixups for previously unreported issues in Arcania, Better Damage Feedback, BL2Fix,
  Exodus, Reign of Giants, and Reward Reroller.

### [Mods Base v1.7](https://github.com/bl-sdk/mods_base/blob/master/Readme.md#v17)
> - The "Update Available" notification should now immediately go away upon updating, instead of
>   waiting a day for the next check.
>
> - Changed the functions the keybind implementation should overwrite from `KeybindType.enable` to
>   `KeybindType._enable` (+ same for disable). These functions don't need to set `is_enabled`.

### Willow2 Mod Menu v3.2
- Fixed that on lower aspect ratios, trying to open the keybinds screen would instead show
  controller bindings, making changing keybinds impossible.

## v3.2: Razorback

### Legacy Compat v1.1
- Fixed that some legacy mods would not auto-enable properly.
- Added a compat handler for object names - they didn't use to include the number. This fixes a
  previously unreported crash when trying to load Exodus.
- Added a fixup for a previously unreported issue in Constructor, and Constructor-based mods, to
  handle the new mod folder location.

### [pyunrealsdk v1.5.2](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v152)
This version has no `pyunrealsdk` changes, it simply pulled in a new version of `unrealsdk`.

### [unrealsdk v1.6.1](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v161)
> - Handled `UClass::Interfaces` also having a different offset between BL2 and TPS.

### Willow2 Mod Menu v3.1
- Fixed mouse input not working properly in the main menu mod list.

## v3.1: Omni-Cannon

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
