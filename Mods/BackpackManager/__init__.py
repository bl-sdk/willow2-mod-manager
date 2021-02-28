import unrealsdk

from Mods.ModMenu import EnabledSaveType, Hook, ModTypes, Options, RegisterMod, SDKMod


class BackpackManager(SDKMod):
    Name: str = "Backpack Manager"
    Author = "FromDarkHell"
    Description: str = "Customize the size of your character's backpack on the fly!"
    Version: str = "1.1"

    Types: ModTypes = ModTypes.Gameplay
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    BackpackSize: Options.Slider = Options.Slider(
        "Backpack", "Change the size of your character's backpack<br>Default is 39", 39, 0, 200, 1
    )
    Options = [BackpackSize]

    @Hook("WillowGame.WillowHUD.CreateWeaponScopeMovie")
    def _GameLoad(self, caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        PC = unrealsdk.GetEngine().GamePlayers[0].Actor
        if PC and PC.Pawn:
            PC.Pawn.InvManager.InventorySlotMax_Misc = self.BackpackSize.CurrentValue
        return True

    def ModOptionChanged(self, option, newValue) -> None:
        if option == self.BackpackSize:
            PC = unrealsdk.GetEngine().GamePlayers[0].Actor
            if PC and PC.Pawn:
                PC.Pawn.InvManager.InventorySlotMax_Misc = newValue


RegisterMod(BackpackManager())
