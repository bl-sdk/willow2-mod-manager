import unrealsdk

from ..ModManager import BL2MOD, RegisterMod

class Grenadoer(BL2MOD):

    Name = "Grenadoer"
    Description = "Cycles your equipped grenade mod through the ones marked as Favorite in your backpack. Configure binding from the Key Bindings settings menu."

    Keybinds = [["Swap Grenade", "B"]]

    def GameInputRebound(self, name, key):
        """Invoked by the SDK when one of the inputs we have registered for is
		rebound by the user. Use it to save our settings for the key binding."""
        pass

    def GameInputPressed(self, input):
        """Invoked by the SDK when one of the inputs we have registered for is
		pressed in-game."""
        if input.Name == "Swap Grenade":
            inventoryManager = (
                unrealsdk.GetEngine().GamePlayers[0].Actor.GetPawnInventoryManager()
            )
            for inventory in inventoryManager.Backpack:
                if (
                    inventory.Class == unrealsdk.FindClass("WillowGrenadeMod")
                    and inventory.Mark == 2
                ):
                    inventoryManager.ReadyBackpackInventory(inventory, 0)
                    break


RegisterMod(Grenadoer())
