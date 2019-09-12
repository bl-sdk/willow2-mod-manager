from unrealsdk import *


class MapLoader(BL2MOD):
	Name = "Borderlands 2 Map Reloader"
	Description = "Quickly Farm Items in Borderlands 2!"
	Types = [ModTypes.Utility]
	Author = "FromDarkHell"

	def __init__(self):
		# Our rotation etc etc
		self.X = 0
		self.Y = 0
		self.Z = 0
		self.Pitch = 0
		self.Yaw = 0
		self.Roll = 0

		# It might be a good idea to restore our position after a load.
		self.saveLocation = True
		self.loading = False
		self.consistentLocation = False
		self.toggledLocation = False

		# Store some data that we can use to reload the map
		self.currentSelectedDifficulty = 0
		self.currentSelectedOverpowerLevel = 0

		self.DefaultGameInfo = UObject.FindObjectsContaining("WillowCoopGameInfo WillowGame.Default__WillowCoopGameInfo")[0]

	Keybinds = [ 
		["Quickload w/o Saving", "F7"],
		["Quickload w/ Saving", "F8"],
		["Toggle Quickload Save States", "F10"],
		["Consistent Location States", "F5"]
	]

	def reloadCurrentMap(self, skipSave):
		PC = GetEngine().GamePlayers[0].Actor
		if self.toggledLocation:
			if self.consistentLocation:
				locale = PC.Pawn.Location
				self.X = locale.X
				self.Y = locale.Y
				self.Z = locale.Z
				rotate = PC.Rotation
				self.Pitch = rotate.Pitch
				self.Yaw = rotate.Yaw
				self.Roll = rotate.Roll
		else:
			if not self.consistentLocation:
				locale = PC.Pawn.Location
				self.X = locale.X
				self.Y = locale.Y
				self.Z = locale.Z
				rotate = PC.Rotation
				self.Pitch = rotate.Pitch
				self.Yaw = rotate.Yaw
				self.Roll = rotate.Roll

		self.toggledLocation = False
		# Our currently selected difficulty for the main menu
		self.currentSelectedDifficulty = PC.GetCurrentPlaythrough()
		# Get our current save game we'll need it for the OP levels
		wsg = PC.GetCachedSaveGame()
		# Our current OP level if we need it, game is weird
		if wsg.LastOverpowerChoice and wsg.NumOverpowerLevelsUnlocked:
			self.currentSelectedOverpowerLevel = max(min(wsg.LastOverpowerChoice, wsg.NumOverpowerLevelsUnlocked), 0)
		else: 
			self.currentSelectedOverpowerLevel = -1

		# Load Map
		self.loading = True
		# This is the function that BL2 uses for save quits.
		PC.ReturnToTitleScreen(skipSave, False)

	def GameInputPressed(self,  input):
		name = input.Name
		if name == "Quickload w/o Saving" or name == "Quickload w/ Saving":
			self.reloadCurrentMap(name == "Quickload w/o Saving")
		elif name == "Toggle Quickload Save States":
			self.saveLocation = not self.saveLocation
			state = "Location Saving is now {}".format("enabled" if self.saveLocation else "disabled")
			Log(state)
			pc = GetEngine().GamePlayers[0].Actor
			HUDMovie = pc.myHUD.HUDMovie
			# Show a training text for our location state.
			HUDMovie.ClearTrainingText()
			HUDMovie.AddTrainingText(state, "Map Loader", 2.0 * self.DefaultGameInfo.GameSpeed, (), "", False, 0, pc.PlayerReplicationInfo, True, 0, 0)
		elif name == "Consistent Location States":
			self.toggledLocation = True
			self.consistentLocation = not self.consistentLocation
			state = "Consistent Location States is now {}".format("enabled" if self.consistentLocation else "disabled")
			Log(state)
			pc = GetEngine().GamePlayers[0].Actor
			HUDMovie = pc.myHUD.HUDMovie
			# Show a training text for our location state.
			HUDMovie.ClearTrainingText()
			HUDMovie.AddTrainingText(state, "Map Loader", 2.0 * self.DefaultGameInfo.GameSpeed, (), "", False, 0, pc.PlayerReplicationInfo, True, 0, 0)

	def GameInputRebound(self, name, key):
		"""Invoked by the SDK when one of the inputs we have registered for is
		rebound by the user. Use it to save our settings for the key binding."""
		pass

	def Enable(self):

		def map_load_hook(caller: UObject, function: UFunction, params: FStruct):
			if self.saveLocation and self.loading:
				pc = GetEngine().GamePlayers[0].Actor
				HUDMovie = pc.myHUD.HUDMovie
				# PC is sometimes none when the hooked function is called, this means this execution of the hook is running to early.
				# Same thing with the HUDMovie.
				if pc.Pawn is None or HUDMovie is None:
					return True
				# Restore our location.
				locale = pc.Pawn.Location
				locale.X = self.X
				locale.Y = self.Y
				locale.Z = self.Z
				rotate = pc.Rotation
				rotate.Roll = self.Roll
				rotate.Pitch = self.Pitch
				rotate.Yaw = self.Yaw

				HUDMovie.ClearTrainingText()
				HUDMovie.AddTrainingText("Farming Location Restored", "Map Loader", 3.0 * self.DefaultGameInfo.GameSpeed, (), "", False, 0, pc.PlayerReplicationInfo, True, 0, 0)
				# Restore our rotation to the saved values.

			self.loading = False
			return True
		   
		def main_menu_hook(caller: UObject, function: UFunction, params: FStruct):
			try:
				if self.loading:
					PC = GetEngine().GamePlayers[0].Actor
					# We'll need this to reload to the current difficulty.
					gfx = UObject.FindObjectsContaining("FrontendGFxMovie ")[1]
					if gfx is None or PC is None:
						return True
					# This is how the game knows what OP level we're on.
					if self.currentSelectedOverpowerLevel != -1:
						PC.OnSelectOverpowerLevel(PC.GetCachedSaveGame(), self.currentSelectedOverpowerLevel)
						# I don't *think* this does anything, might want to do it just in case. Weird Game.
						gfx.CurrentSelectedOverpowerLevel = self.currentSelectedOverpowerLevel
					Log("[Map Loader] Loading WSG on playthrough %s at OP %s" % (self.currentSelectedDifficulty, self.currentSelectedOverpowerLevel))
					# Here we reload our save, like how the `Continue` button does.
					gfx.LaunchSaveGame(self.currentSelectedDifficulty)
			except: pass
			return True

		# This is how we know that we're in the main menu. Its slightly janky, but it works.
		RegisterHook("WillowGame.FrontendGFxMovie.OnTick", "HookMainMenu", main_menu_hook)
		# This is how we know that we've loaded a new map. Once again, janky.
		RegisterHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "MapHookLoad", map_load_hook)

	def Disable(self):
		RemoveHook("WillowGame.FrontendGFxMovie.OnTick", "HookMainMenu")
		RemoveHook("WillowGame.WillowHUD.CreateWeaponScopeMovie", "MapHookLoad")


RegisterMod(MapLoader())
