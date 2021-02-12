import unrealsdk
from unrealsdk import *
from Mods import ModMenu
from Mods.ModMenu import EnabledSaveType, Mods, ModTypes, Options, RegisterMod, SDKMod, Hook
from typing import List


_DefaultGameInfo = UObject.FindObjectsContaining("WillowCoopGameInfo WillowGame.Default__WillowCoopGameInfo")[0]


def _DisplayFeedback(message, time=2.0) -> None:
    playerController = GetEngine().GamePlayers[0].Actor
    HUDMovie = playerController.GetHUDMovie()
    if HUDMovie is None:
        return
    duration = time * _DefaultGameInfo.GameSpeed
    HUDMovie.ClearTrainingText()
    HUDMovie.AddTrainingText(
        message, "Map Loader", duration, (), "", False, 0, playerController.PlayerReplicationInfo, True
    )


def _StoreLocation() -> None:
    PC = GetEngine().GamePlayers[0].Actor
    locale = PC.Pawn.Location
    _Position = [locale.X, locale.Y, locale.Z]
    _ModInstance.Coords[0] = locale.X
    _ModInstance.Coords[1] = locale.Y
    _ModInstance.Coords[2] = locale.Z
    rotate = PC.Rotation
    _ModInstance.Rotation[0] = rotate.Pitch
    _ModInstance.Rotation[1] = rotate.Roll
    _ModInstance.Rotation[2] = rotate.Yaw
    Log(f"[Map Loader] Storing location: ({_ModInstance.Coords}), ({_ModInstance.Rotation})")


def _RestoreLocation() -> None:
    PC = GetEngine().GamePlayers[0].Actor
    # Restore our location.
    PC.Pawn.Location.X = _ModInstance.Coords[0]
    PC.Pawn.Location.Y = _ModInstance.Coords[1]
    PC.Pawn.Location.Z = _ModInstance.Coords[2]
    Log(f"[Map Loader] Restoring location: ({_ModInstance.Coords}), ({_ModInstance.Rotation})")
    rotate = PC.Rotation
    rotate.Pitch = _ModInstance.Rotation[0]
    rotate.Roll = _ModInstance.Rotation[1]
    rotate.Yaw = _ModInstance.Rotation[2]


def _ReloadCurrentMap(skipSave):
    PC = GetEngine().GamePlayers[0].Actor
    if _ModInstance.toggledLocation:
        if _ModInstance.consistentLocation:
            _StoreLocation()
    else:
        if not _ModInstance.consistentLocation:
            _StoreLocation()

    _ModInstance.toggledLocation = False
    # Our currently selected difficulty for the main menu
    _ModInstance.SelectedDifficulty = PC.GetCurrentPlaythrough()
    # Get our current save game we'll need it for the OP levels
    wsg = PC.GetCachedSaveGame()

    # Our current OP level if we need it, game is weird
    if wsg.LastOverpowerChoice and wsg.NumOverpowerLevelsUnlocked:
        _ModInstance.OverpoweredLevel = max(min(wsg.LastOverpowerChoice, wsg.NumOverpowerLevelsUnlocked), 0)
    else:
        _ModInstance.OverpoweredLevel = -1

    # Load Map
    _ModInstance.loading = True
    # This is the function that BL2 uses for save quits.
    # ReturnToTitleScreen(optional bool bSkipSave, optional bool bRemoveSplitPlayer)
    #   (In the SDK, optional arguments aren't optional)

    PC.ReturnToTitleScreen(skipSave, False)


@Hook("WillowGame.WillowHUD.CreateWeaponScopeMovie")
def _MapLoadHook(caller: UObject, function: UFunction, params: FStruct) -> None:
    if _ModInstance.restoreLocation and _ModInstance.loading:
        pc = GetEngine().GamePlayers[0].Actor
        HUDMovie = pc.myHUD.HUDMovie
        # PC is sometimes none when the hooked function is called, this means that the hook is running to early.
        # Same thing with the HUDMovie.
        if pc.Pawn is None or HUDMovie is None:
            return True
        _RestoreLocation()
        _DisplayFeedback("Farming Location Restored", 3.0)
        _ModInstance.loading = False
    return True


# This is how we know that we're in the main menu. Its slightly janky, but it works.
@Hook("WillowGame.FrontendGFxMovie.OnTick")
def _MainMenuHook(caller: UObject, function: UFunction, params: FStruct) -> None:
    try:
        if _ModInstance.loading == True:
            PC = GetEngine().GamePlayers[0].Actor
            # We'll need this to reload to the current difficulty.
            gfx = UObject.FindObjectsContaining("FrontendGFxMovie ")[1]
            if gfx is None or PC is None:
                return True
            # This is how the game knows what OP level we're on.
            if _ModInstance.OverpoweredLevel != -1:
                PC.OnSelectOverpowerLevel(PC.GetCachedSaveGame(), _ModInstance.OverpoweredLevel)
                # I don't *think* this does anything, might want to do it just in case. Weird Game.
                gfx.CurrentSelectedOverpowerLevel = _ModInstance.OverpoweredLevel
            Log(f"[Map Loader] Loading WSG @ {_ModInstance.SelectedDifficulty}, OP{_ModInstance.OverpoweredLevel}")
            # Here we reload our save, like how the `Continue` button does.
            gfx.LaunchSaveGame(_ModInstance.SelectedDifficulty)
    except:
        pass
    return True


class MapLoader(SDKMod):
    Name: str = "Borderlands 2 Map Reloader"
    Version: str = "1.1"
    Author: str = "FromDarkHell"
    Description: str = "Quickly farm items and save quit at a button press!\n\nLocation Restore: Whether to restore location on quickload"
    Types: ModTypes = ModTypes.Utility
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    Keybinds: List[ModMenu.Keybind] = [
        ModMenu.Keybind("Quickload w/o Saving", "F7"),
        ModMenu.Keybind("Quickload w/ Saving", "F8"),
        ModMenu.Keybind("Toggle Location Restore", "F10"),
        ModMenu.Keybind("Save Location", "F5"),
    ]

    def __init__(self):
        # It might be a good idea to restore our position after a load.
        self.restoreLocation = True
        self.loading = False
        self.consistentLocation = False
        self.toggledLocation = False
        # Store some data that we can use to reload the map
        self.SelectedDifficulty = 0
        self.OverpoweredLevel = 0
        self.Coords = [0, 0, 0]  # X, Y, Z
        self.Rotation = [0, 0, 0]  # Pitch, Roll, Yaw

    def GameInputPressed(self, input) -> None:
        name = input.Name
        if name == "Quickload w/o Saving":
            _ReloadCurrentMap(True)
        elif name == "Quickload w/ Saving":
            _ReloadCurrentMap(False)
        elif name == "Toggle Location Restore":
            self.restoreLocation = not self.restoreLocation
            state = "Location restoration is now {}".format("enabled" if self.restoreLocation else "disabled")
            Log(f"[Map Loader] {state}")
            _DisplayFeedback(state)
        elif name == "Save Location":
            self.toggledLocation = True
            self.consistentLocation = not self.consistentLocation
            state = "Save Location is now {}".format(
                "enabled (Saves on quickload quit)" if self.consistentLocation else "disabled"
            )
            Log(f"[Map Loader] {state}")
            _DisplayFeedback(state)

    def Enable(self) -> None:
        super().Enable()

    def Disable(self) -> None:
        ModMenu.RemoveHooks(self)


_ModInstance = MapLoader()
RegisterMod(_ModInstance)
