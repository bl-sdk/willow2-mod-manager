from __future__ import annotations

import copy
import enum
import json
import sys
from abc import ABCMeta
from functools import lru_cache
from os import path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, cast

from . import HookManager, KeybindManager, NetworkManager, OptionManager, SettingsManager

__all__: Tuple[str, ...] = (
    "EnabledSaveType",
    "Game",
    "ModPriorities",
    "Mods",
    "ModTypes",
    "RegisterMod",
    "SDKMod",
)


Mods: List[SDKMod] = []


def RegisterMod(mod: SDKMod) -> None:
    """
    Adds the provided mod to the mods list and loads all it's settings.

    Args:
        mod: The mod to register.
    """
    Mods.append(mod)
    SettingsManager.LoadModSettings(mod)


class ModPriorities(enum.IntEnum):
    """ Predefined mod priorities. These just provide standarization, any int value can be used. """
    High = 10
    Standard = 0
    Low = -10
    Library = Low


class ModTypes(enum.Flag):
    """ Various categories your mod might fit into, used for filtering in the mod menu. """
    NONE = 0
    Utility = enum.auto()
    Content = enum.auto()
    Gameplay = enum.auto()
    Library = enum.auto()
    All = Utility | Content | Gameplay | Library


class EnabledSaveType(enum.Enum):
    """
    The different ways a mod's enabled state may (or may not) be saved.

    Note that you must call `LoadModSettings` for the state to properly be loaded.

    If the state is saved as disabled, nothing happens. If it's saved as enabled, it's enabled by
     calling `SettingsInputPressed("Enable")`, as long as `IsEnabled` is still False.

    Values:
        NotSaved: The enabled state is not saved.
        LoadWithSettings:
            The enabled state is saved, and the mod is enabled when the mod settings are loaded.
        LoadOnMainMenu:
            The enabled state is saved, and the mod is enabled upon reaching the main menu - after
             hotfixes are all setup and all the normal packages are loaded.
    """
    NotSaved = enum.auto()
    LoadWithSettings = enum.auto()
    LoadOnMainMenu = enum.auto()


class Game(enum.Flag):
    BL2 = enum.auto()
    TPS = enum.auto()
    AoDK = enum.auto()

    @staticmethod
    @lru_cache(None)
    def GetCurrent() -> Game:
        """ Gets the current game. """
        lower_exe_names: Dict[str, Game] = {
            "borderlands2.exe": Game.BL2,
            "borderlandspresequel.exe": Game.TPS,
            "tinytina.exe": Game.AoDK,
        }

        exe = path.basename(sys.executable)
        exe_lower = exe.lower()
        if exe_lower not in lower_exe_names:
            raise RuntimeError(f"Unknown executable name '{exe}'!")
        return lower_exe_names[exe_lower]


class _ModMeta(ABCMeta):
    """
    Metaclass used to ensure that SDKMod subclasses get copies of attributes rather than references.

    It's a rather easy to mistakenly edit these references, and affect all other mods, so it's
     probably better to prevent it happening in the first place.
    """
    Attributes: Tuple[str, ...] = (
        "Author",
        "Description",
        "Version",
        "SupportedGames",
        "Types",
        "Priority",
        "SaveEnabledState",
        "Status",
        "SettingsInputs",
        "Options",
        "Keybinds",
        "_server_functions",
        "_client_functions",
        "_is_enabled",
    )

    def __init__(cls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any]) -> None:
        super().__init__(name, bases, attrs)

        for name in _ModMeta.Attributes:
            setattr(cls, name, copy.copy(getattr(cls, name)))

        functions = (attribute for attribute in cls.__dict__.values() if callable(attribute))
        for function in functions:
            method_sender = NetworkManager._find_method_sender(function)
            if method_sender is not None:
                if method_sender._is_server:  # type: ignore
                    cls._server_functions.add(method_sender)  # type: ignore
                if method_sender._is_client:  # type: ignore
                    cls._client_functions.add(method_sender)  # type: ignore


class SDKMod(metaclass=_ModMeta):
    """
    The base class any SDK mod should inherit from. Describes an entry in the mod menu.

    Attributes:
        Name: The mod's name.
        Author: The mod's author(s).
        Description: A short description of the mod.
        Version:
            A string holding the mod's version. This is purely informational, no version checking is
             performed.

        SupportedGames:
            The games this mod supports - see the `Game` enum. When loaded in an unsupported one, a
             warning will be displayed and the mod will be blocked from enabling.
        Types: A list specifing all `ModTypes` the mod fits into.
        Priority: The priority of the mod in the mod list. See the `ModPriorities` enum.
        SaveEnabledState:
            If the mod's enabled state is saved across launches. See the `EnabledSaveType` enum.

        Status:
            A string holding the mod's current status. The default `SettingsInputPressed` sets it to
             "Enabled"/"Disabled" - these exact strings will automatically be coloured green/red.
        SettingsInputs:
            A dictionary mapping keys to the action the mod performs when that key is pressed in the
             mods menu. This does *not* bind in game actions, use `Keybinds` for that.
        Options: A sequence of the mod's options. These are only displayed while the mod is enabled.
        Keybinds:
            A sequence of the mod's in game keybinds. These are only displayed, and the callback
             will only be called, while the mod is enabled.

        IsEnabled:
            A bool that is True if the mod is currently enabled. For compatibility reasons, by
             default this returns if the status is currently "Enabled". Once overwritten, it will
             return whatever value it was set to.
    """
    Name: str
    Author: str = "Unknown"
    Description: str = ""
    Version: str = "Unknown Version"

    SupportedGames: Game = Game.BL2 | Game.TPS | Game.AoDK
    Types: ModTypes = ModTypes.NONE
    Priority: int = ModPriorities.Standard
    SaveEnabledState: EnabledSaveType = EnabledSaveType.NotSaved

    Status: str = "Disabled"
    SettingsInputs: Dict[str, str] = {"Enter": "Enable"}
    Options: Sequence[OptionManager.Options.Base] = []
    Keybinds: Sequence[KeybindManager.Keybind] = []

    _server_functions: Set[Callable[..., None]] = set()
    _client_functions: Set[Callable[..., None]] = set()

    _is_enabled: Optional[bool] = None

    @property
    def IsEnabled(self) -> bool:
        if self._is_enabled is None:
            return self.Status == "Enabled"
        return self._is_enabled

    @IsEnabled.setter
    def IsEnabled(self, val: bool) -> None:
        self._is_enabled = val
        if self.SaveEnabledState != EnabledSaveType.NotSaved:
            SettingsManager.SaveModSettings(self)

    def __new__(cls, *args: List[Any], **kwargs: Dict[str, Any]) -> Any:
        """
        Check if you're running in a compatible game. Do this here rather than in `__init__()`
         because it's easy to forget to also call it on the superclass when you overwrite it.
        """
        inst = super().__new__(cls)
        if Game.GetCurrent() not in inst.SupportedGames:
            try:
                del inst.SettingsInputs["Enter"]
            except KeyError:
                pass
            inst.Name = f"<font color=\"#ff0000\">{inst.Name}</font>"
            inst.Status = "<font color=\"#ff0000\">Incompatible</font>"

            if len(inst.Description) > 0:
                inst.Description += "\n\n"
            inst.Description += (
                f"<font color=\"#FF0000\">Incompatible with {Game.GetCurrent().name}!</font>"
            )

        return inst

    def Enable(self) -> None:
        """
        Called by the mod manager to enable the mod. The default implementation calls
        ModMenu.RegisterHooks(self) and ModMenu.RegisterNetworkMethods(self) on the mod.
        """
        HookManager.RegisterHooks(self)
        NetworkManager.RegisterNetworkMethods(self)

    def Disable(self) -> None:
        """
        Called by the mod manager to disable the mod. The default implementation calls
        ModMenu.UnregisterHooks(self) and ModMenu.UnregisterNetworkMethods(self) on the mod.
        """
        HookManager.RemoveHooks(self)
        NetworkManager.UnregisterNetworkMethods(self)

    def SettingsInputPressed(self, action: str) -> None:
        """
        Called by the mod manager when one of the actions in `SettingsInputs` is invoked via its key.

        Mods may should overwrite this method when they add custom actions, the base implementation
         only deals with enabling/disabling the mod.

        All arguments are provided positionally, mods can rename them as they please.

        Args:
            action: The name of the action.
        """
        # Even though we removed these from `SettingsInputs`, need this check for auto enable
        if Game.GetCurrent() not in self.SupportedGames and action in ("Enable", "Disable"):
            return

        if action == "Enable":
            if not self.IsEnabled:
                self.Enable()
                self.IsEnabled = True

                """
                Relying on these calls here should be considered deprecated.
                Unfortuantly there's no easy way to detect and print a warning where this happens.
                """
                for option in self.Options:
                    if isinstance(option, OptionManager.Options.Value):
                        self.ModOptionChanged(option, option.CurrentValue)
            self.Status = "Enabled"
            self.SettingsInputs["Enter"] = "Disable"

        elif action == "Disable":
            if self.IsEnabled:
                self.Disable()
                self.IsEnabled = False
            self.Status = "Disabled"
            self.SettingsInputs["Enter"] = "Enable"

    def GameInputPressed(self, bind: KeybindManager.Keybind, event: KeybindManager.InputEvent) -> None:
        """
        Called by the mod manager on any key event associated with one of the mod's keybindings.

        For compatibility reasons, you may define this funtion with just the first positional `bind`
         argument. Doing so will only call it for pressed events.

        All arguments are provided positionally, mods can rename them as they please.

        Arguments:
            bind: The keybind object associated with the key that was pressed.
            event: The input event type - see the `InputEvent` enum.
        """
        pass

    def ModOptionChanged(self, option: OptionManager.Options.Base, new_value: Any) -> None:
        """
        Called by the mod manager when one of the mod's options gets changed.

        Called before the option's value is updated - i.e. `option.CurrentValue` will still be the
         old value, while `new_value` is the new one.

        All arguments are provided positionally, mods can rename them as they please.

        Arguments:
            option: The option who's value was changed.
            new_value: The new value which `option.CurrentValue` will be updated to.
        """
        pass

    @staticmethod
    def NetworkSerialize(arguments: NetworkManager.NetworkArgsDict) -> str:
        """
        Called when instances of this class invoke methods decorated with `@ModMenu.ServerMethod`
        or `@ModMenu.ClientMethod`, performing the serialization of any arguments passed to said
        methods. The default implementation uses `json.dumps()`.

        Arguments:
            arguments:
                The arguments that need to be serialized. The top-level object passed will be a
                `dict` keyed with `str`, containing a `list` as well as another `dict`.
        Returns:
            The arguments serialized into a text string.
        """
        return json.dumps(arguments)

    @staticmethod
    def NetworkDeserialize(serialized: str) -> NetworkManager.NetworkArgsDict:
        """
        Called when instances of this class receive requests for methods decorated with
        `@ModMenu.ServerMethod` or `@ModMenu.ClientMethod`, performing the deserialization of any
        arguments passed to said methods. The default implementation uses `json.loads()`.

        Arguments:
            serialized:
                The string containing the serialized arguments as returned by 'NetworkSerialize'.
        Returns:
            The deserialized arguments in the same format as they were passed to `NetworkSerialize`.
        """
        return cast(NetworkManager.NetworkArgsDict, json.loads(serialized))
