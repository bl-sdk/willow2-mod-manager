from unrealsdk import *
from ..ModManager import BL2MOD, RegisterMod
import math

class ReadOnly(BL2MOD):
    Name = "Borderlands Easy Read Only"
    Description = "Toggle Read Only on a button press"
    readOnly = False
    toggledReadOnly = False

    DefaultGameInfo = UObject.FindObjectsContaining("WillowCoopGameInfo WillowGame.Default__WillowCoopGameInfo")[0]
    Keybinds = [["Toggle Read Only", "F2"]]

    def displayFeedback(self):
        PC = GetEngine().GamePlayers[0].Actor
        HUDMovie = PC.myHUD.HUDMovie
        try:
            if PC is None or HUDMovie is None:
                return True
            if self.readOnly:           
                HUDMovie.AddTrainingText("Read Only: Enabled", "Read Only", math.inf, (), "", False, 0, PC.PlayerReplicationInfo, True, 0, 0)
            elif self.toggledReadOnly: 
                self.toggledReadOnly = False
                HUDMovie.ClearTrainingText()
        except:
            return True
        return True

    def GameInputPressed(self, input):
        if input.Name == "Toggle Read Only":
            self.toggledReadOnly = True
            self.readOnly = not self.readOnly
            self.displayFeedback()

    def Enable(self):

        def hookCanSaveGame(caller: UObject, function: UFunction, params: FStruct) -> bool:
            if self.readOnly:
                return False
            return True

        def hookTrainingText(caller: UObject, function: UFunction, params: FStruct):
            self.displayFeedback()
            return True

        RegisterHook("WillowGame.WillowPlayerController.CanSaveGame", "HookSaveGame", hookCanSaveGame)
        RegisterHook("WillowGame.WillowHUDGFxMovie.DrawTrainingText", "HookTrainingText", hookTrainingText)
        RegisterHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "HookTrainingText", hookTrainingText)

    def Disable(self):
        RemoveHook("WillowGame.WillowPlayerController.CanSaveGame", "HookSaveGame")
        RemoveHook("WillowGame.WillowHUDGFxMovie.DrawTrainingText", "HookTrainingText")
        RemoveHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "HookTrainingText")

RegisterMod(ReadOnly())