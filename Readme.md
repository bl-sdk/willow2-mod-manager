# Willow 2 Mod Manager
[![Support Discord](https://img.shields.io/static/v1?label=&message=Support%20Discord&logo=discord&color=424)](https://discord.gg/bXeqV8Ef9R)
[![Developer Discord](https://img.shields.io/static/v1?label=&message=Developer%20Discord&logo=discord&color=222)](https://discord.gg/VJXtHvh)

[For installation instructions / the mod database, see the project site.](https://bl-sdk.github.io/willow2-mod-db/)

<br>

The [pyunrealsdk](https://github.com/bl-sdk/pyunrealsdk) mod manager for:
- Borderlands 2
- Borderlands: The Pre-Sequel
- Tiny Tina's Assault on Dragon Keep Standalone

# Development
When developing, it's recommended to point pyunrealsdk directly at this repo. To do this:

1. Navigate to the plugins folder - `<game>\Binaries\Win32\Plugins\`

2. Create/edit `unrealsdk.user.toml`, adding the following:
   ```toml
   [pyunrealsdk]
   init_script = "<path to repo>\\src\\__main__.py"
   ```

3. (Optional) Update `pyunrealsdk.pyexec_root` to the same folder, to make sure pyexec commands go
   where you expect.

4. (Optional) Add the path to your old `sdk_mods` folder to the `mod_manager.extra_folders` array,
   so they continue getting loaded.

5. (Optional) Copy/symlink your original settings folder into `src\settings` - settings are only
   loaded from the base mods folder.

Once you've done this, you can modify the python files in place.

## Native code
The mod manager currently doesn't rely on any native modules. You may however still want to
edit/debug the base pyunrealsdk code while working on this project. The sdk supports five different
toolchains:

- MSVC
- Clang (Windows)
- Clang (Cross Compile) <sup>*</sup>
- MinGW <sup>*</sup>
- LLVM MinGW <sup>*</sup>

The toolchains with an asterix are all cross compiling toolchains. These all also have an associated
dev container, which is the recommended way of building them. The `clang-cross-*` presets in
particular hardcode a path assuming they're running in the container.

1. Initialize the git submodules.
   ```sh
   git submodule update --init --recursive
   ```
   You can also clone and initialize the submodules in a single step.
   ```sh
   git clone --recursive https://github.com/bl-sdk/willow2-mod-manager.git
   ```

2. Make sure you have Python with requests on your PATH. This doesn't need to be the same version
   as what the SDK uses, it's just used by the script which downloads the correct one.
   ```sh
   pip install requests
   python -c 'import requests'
   ```

   If cross compiling, and not using one of the dev containers, make sure `msiextract` is also on
   your PATH. This is typically part of an `msitools` package.
   ```sh
   apt install msitools # Or equivalent
   msiextract --version 
   ```

3. Choose a preset, and run CMake. Most IDEs will be able to do this for you,
   ```
   cmake . --preset msvc-debug
   cmake --build out/build/msvc-debug
   ```

4. (OPTIONAL) If you need to debug your module, and you own the game on Steam, add a
   `steam_appid.txt` in the same folder as the executable, containing the game's Steam App Id.

   Normally, games compiled with Steamworks will call
   [`SteamAPI_RestartAppIfNecessary`](https://partner.steamgames.com/doc/sdk/api#SteamAPI_RestartAppIfNecessary),
   which will drop your debugger session when launching the exe directly - adding this file prevents
   that. Not only does this let you debug from entry, it also unlocks some really useful debugger
   features which you can't access from just an attach (i.e. Visual Studio's Edit and Continue).
