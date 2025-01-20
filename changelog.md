# Changelog

## v3.4 (upcoming)

### Legacy Compat v1.3
- Added more fixups for previously unreported issues in Skill Randomizer and Skill Saver.
- Slightly extended the list of allowed versions before the kill switch activates.

### [Mods Base v1.8](https://github.com/bl-sdk/mods_base/blob/master/Readme.md#v18)
> - Fixed that nested and grouped options' children would not get their `.mod` attribute set.

### Networking v1.1
- Linting fixes.

### [pyunrealsdk v1.6.0](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v160)
> - `WrappedStruct` now supports being copied via the `copy` module.
>
> - Fixed that `WrappedArray.index` would not check the last item in the array. It also now accepts
>   start/stop indexes beyond the array bounds, like `list.index` does.
>
> - Hook return values and array access now have the same semantics as normal property accesses. In
>   practice this means:
>
>   - Getting an enum property will convert it to a python `IntFlag` enum (rather than an int).
>   - Setting an array property will accept any sequence (rather than just wrapped arrays).
>   
>   All other property types had the same semantics already, so this is backwards compatible.
>
> - Added a `_get_address` method to `WrappedArray`, `WrappedMulticastDelegate`, and `WrappedStruct`.

### UI Utils v1.1
- Fixed some oddities that occurred if you re-showed an `OptionBox` during it's `on_select`
  callback.

### [unrealsdk v1.7.0](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v170)
> - `unrealsdk::unreal::cast` now copies the const-ness of its input object to its callbacks.
> 
> - Reworked `PropertyProxy` to be based on `UnrealPointer` (and reworked it too). This fixes some
>   issues with ownership and possible use after frees.
>   
>   *This breaks binary compatibility*, though existing code should work pretty much as is after a
>   recompile.

### Willow2 Mod Menu v3.3
- Allowed quick enabling/disabling a mod from the main menu using space, like in the legacy mod
  menu. While in game you'll still need to check under each mod individually.

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
