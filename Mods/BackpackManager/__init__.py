from unrealsdk import *
from ..ModManager import BL2MOD, RegisterMod
from ..OptionManager import Options

class BackpackManager(BL2MOD):
	Name = "Backpack Manager"
	Description = "Customize the size of your character's backpack on the fly!"
	Types = [ModTypes.Gameplay]
	Author = "FromDarkHell"

	Options = [
		Options.Slider("Backpack", "Change the size of your character's backpack<br>Default is 39", 39,0,200,1)
	]

	backpackSpace = 39

	def Enable(self):
		def HookCreateWeaponScopeMovie(caller: UObject, function: UFunction, params: FStruct) -> bool:
			PC = GetEngine().GamePlayers[0].Actor
			if PC and PC.Pawn:
				pawn = PC.Pawn
				pawn.InvManager.InventorySlotMax_Misc = self.backpackSpace
			return True

		RegisterHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "HookCreateWeaponScopeMovie", HookCreateWeaponScopeMovie)

	def Disable(self):
		RemoveHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "HookCreateWeaponScopeMovie")


	def ModOptionChanged(self, option, newValue):
		if option.Caption == "Backpack":
			self.backpackSpace = int(newValue)
			PC = GetEngine().GamePlayers[0].Actor
			if PC and PC.Pawn:
				pawn = PC.Pawn
				pawn.InvManager.InventorySlotMax_Misc = self.backpackSpace

RegisterMod(BackpackManager())