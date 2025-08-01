# Changelog

## v3.8: 

### Save Options v1.3
- Fixed issue with newly created characters inheriting options from previously loaded character.

## v3.7: Meteor Shower

### [Console Mod Menu v1.6](https://github.com/bl-sdk/console_mod_menu/blob/master/Readme.md#v16)
> - Made Willow1 use UE3 controller key names.

### Legacy Compat v1.6
- Linting fixups.
- Added fixups for Reign of Giants (for real this time).

### [Mods Base v1.10](https://github.com/bl-sdk/mods_base/blob/master/Readme.md#v19)
> - Added the `ObjectFlags` enum, holding a few known useful flags.
>
> - Moved a few warnings to go through Python's system, so they get attributed to the right place.
>
> - Added a warning for initializing a non-integer slider option with `is_integer=True` (the default).
>
> - Added support for BL1.

### [pyunrealsdk v1.8.0](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v180)
> - Added `WeakPointer.replace`, to modify a pointer in-place.
>
> - Trying to overwrite the return value of a void function will now return a more appropriate error.
>
> - The type hinting of `WrappedArray`s now default to `WrappedArray[Any]`, no generic required.
>
> - Upgraded to support unrealsdk v2 - native modules can expect some breakage. The most notable
>   effect this has on Python code is a number of formerly read-only fields on core unreal types have
>   become read-write.

### Save Options v1.2
- Fixed issue where loading a character with no save option data inherited option values from
  previous character.
- Moved a few warnings to go through Python's system, so they get attributed to the right place.

### UI Utils v1.3
- Added several new helper functions:
  - `show_blocking_message`, `hide_blocking_message`
  - `show_button_prompt`, `hide_button_prompt`
  - `show_coop_message`, `hide_coop_message`
  - `show_discovery_message`
  - `show_reward_popup`
  - `show_second_wind_notification`
  
  [See examples here](https://bl-sdk.github.io/developing/ui_utils/willow2/).

### [unrealsdk v2.0.0](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v200)
> - Now supports Borderlands 1. Big thanks to Ry for doing basically all the reverse engineering.
>
> - Major refactor of the core unreal types, to cleanly allow them to change layouts at runtime. All
>   core fields have changed from members to zero-arg methods, which return a reference to the
>   member. A few classes (e.g. `UProperty` subclasses) previous had existing methods to deal with
>   the same problem, these have all been moved to the new system.
>   
>   Clang is able to detect this change, and gives a nice error recommending inserting brackets at
>   the right spot.
>
> - Removed the `UNREALSDK_UE_VERSION` and `UNREALSDK_ARCH` CMake variables, in favour a new merged
>   `UNREALSDK_FLAVOUR` variable.
>
> - Removed the (optional) dependency on libfmt, `std::format` support is now required.
>
> - Console commands registered using `unrealsdk::commands::NEXT_LINE` now (try to) only fire on
>   direct user input, and ignore commands send via automated means.
>
> - Fixed that assigning an entire array, rather than getting the array and setting it's elements,
>   would likely cause memory corruption. This was most common when using an array of large structs,
>   and when assigning to one which was previously empty.
>
> - Made `unrealsdk::memory::get_exe_range` public.

### Willow2 Mod Menu v3.5
- Linting fixups.

## v3.6: Easy Mode
Fixed that `save_options.sdkmod` wasn't actually being included in the release zip. Whoops.

### Legacy Compat v1.5
- Fixed handling of _0 names, which caused crashes in most constructor-based mods.

### Save Options v1.1
- Addressed a warning about assigning an array to itself, caused during handling save options. This
  had no runtime impact.

## v3.5: Slagga
- Upgraded the Microsoft Visual C++ version the SDK is built with. This may cause some people to
  crash immediately on launch, to fix this install the latest
  [Microsoft Visual C++ Redistrubutable](https://aka.ms/vs/17/release/vc_redist.x86.exe).

  The crash happens when then pluginloader requires a new redist. We previously lowered the version
  the sdk was built with, to try avoid needing an upgrade so that installing went smoother. However,
  turns out there's an intermediary version, where the pluginloader loads fine, but the SDK itself
  does not. This is not as obvious as an immediate crash, upgrading again to create a louder error.

- `.sdkmod`s are now migrated from the legacy mod folder, in case someone tried installing them
  before upgrading.

### [Console Mod Menu v1.5](https://github.com/bl-sdk/console_mod_menu/blob/master/Readme.md#v15)
> - Support host-only coop support value
> - Linting fixes

### Legacy Compat v1.4
- Added more fixups for previously unreported issues in Gear Randomizer, Loot Randomizer, Player
  Randomizer and Reign of Giants.

### [Mods Base v1.9](https://github.com/bl-sdk/mods_base/blob/master/Readme.md#v19)
> - Added a new `CoopSupport.HostOnly` value.
>
> - Added a helper `RestartToDisable` mod class, for mods which need a restart to fully disable.
>
> - Specifying a custom class when calling `build_mod` now type hints returning an instance of it,
>   instead of just `Mod`.
>
> - `SliderOption`s now throw if initialized with a step larger than their allowed range.
>
> - Added `_(to|from)_json()` methods to all options, and changed settings saving and loading to use
>   them.

### [pyunrealsdk v1.7.0](https://github.com/bl-sdk/pyunrealsdk/blob/master/changelog.md#v170)
> - Added `WrappedArray.emplace_struct`, to construct structs in place. This is more efficient than
>   calling `arr.insert(pos, unrealsdk.make_struct(...))`.
>
> - Added `unrealsdk.unreal.IGNORE_STRUCT`, a sentinel value which can be assigned to any struct,
>   but which does nothing. This is most useful when a function has a required struct arg.
>
> - Added support for sending property changed events. This is typically best done via the
>   `unrealsdk.unreal.notify_changes` context manager.
>
> - Fixed that it was possible for the `unrealsdk` module in the global namespace to get replaced,
>   if something during the init script messed with `sys.modules`. It is now imported during
>   initialization.

### Save Options v1.0
- New library. Allows mods to save options per-character, rather than globally.

### UI Utils v1.2
- Linting fixes.

### [unrealsdk v1.8.0](https://github.com/bl-sdk/unrealsdk/blob/master/changelog.md#v180)
> - Added support for sending property changed events, via `UObject::post_edit_change_property` and
>   `UObject::post_edit_change_chain_property`.

> - Made the error message when assigning incompatible array types more clear.    
>   See also https://github.com/bl-sdk/unrealsdk/issues/60 .
>
> - Fixed checking the setting `exe_override` rather than the full `unrealsdk.exe_override`, like
>   how it was documented / originally intended.
>
>   [3010f486](https://github.com/bl-sdk/unrealsdk/commit/3010f486)

### Willow2 Mod Menu v3.4
- Fixed that some keybinds would not be displayed properly if there were two separate grouped/nested
  options at the same level.

- Added support for the "Host Only" coop support value.

- Now prints a (dev) warning when trying to use a SliderOption with non-integer values, or with a
  step that doesn't evenly divide it's values. Neither of these cases are properly supported by the
  engine, both may have weird, unexpected, behaviour.

## v3.4: Luck Cannon

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
