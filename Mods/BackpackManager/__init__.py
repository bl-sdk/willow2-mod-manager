import unrealsdk
from Mods.ModMenu import EnabledSaveType, Mods, ModTypes, Options, RegisterMod, SDKMod, Hook
from Mods import ModMenu


class BackpackManager(SDKMod):
    Name: str = "Backpack Manager"
    Author = "FromDarkHell"
    Description: str = "Customize the size of your character's backpack on the fly!"
    Version: str = "1.1"

    Types: ModTypes = ModTypes.Gameplay
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    BackpackSize: ModMenu.Options.Slider = Options.Slider(
        "Backpack", "Change the size of your character's backpack<br>Default is 39", 39, 0, 200, 1
    )
    Options = [BackpackSize]

    @Hook("WillowGame.WillowHUD.CreateWeaponScopeMovie")
    def _GameLoad(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
        PC = unrealsdk.GetEngine().GamePlayers[0].Actor
        if PC and PC.Pawn:
            PC.Pawn.InvManager.InventorySlotMax_Misc = _ModInstance.BackpackSize.CurrentValue
        return True

    def Enable(self) -> None:
        super().Enable()

    def Disable(self) -> None:
        ModMenu.RemoveHooks(self)

    def ModOptionChanged(self, option, newValue) -> None:
        if option.Caption == "Backpack":
            PC = unrealsdk.GetEngine().GamePlayers[0].Actor
            if PC and PC.Pawn:
                PC.Pawn.InvManager.InventorySlotMax_Misc = newValue


_ModInstance = BackpackManager()
RegisterMod(_ModInstance)
