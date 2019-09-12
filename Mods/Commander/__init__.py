import unrealsdk
import sys
import os
import math
import json
from fractions import Fraction

from ..ModManager import BL2MOD, RegisterMod


class Commander(BL2MOD):

    Name = "Commander"
    Description = (
        "By mopioid.\n\nPerform various changes to the game using keybindings."
    )

    LocalModDir = os.path.dirname(os.path.realpath(__file__))

    SettingsPath = os.path.join(LocalModDir, "settings.json")
    """The path to the file in which we store our settings."""

    def __init__(self):
        """Attempts to load the user's settings from their settings file."""
        try:
            with open(self.SettingsPath) as settingsFile:
                # Decode the JSON data contained in the settings file.
                settings = json.load(settingsFile)
                # Convert the settings file's list of ignored files to a set for
                # our own usage.
                self.Bindings = settings.get("bindings", dict())
                if type(self.Bindings) is not dict:
                    self.Bindings = dict()

                self.Positions = settings.get("positions", dict())
                if type(self.Positions) is not dict:
                    self.Positions = dict()
        # If this fails, set up empty values for our settings.
        except:
            self.Bindings = dict()
            self.Positions = dict()

        self.GameInputs = {
            "Halve Game Speed": ("LeftBracket", self.HalveGameSpeed),
            "Double Game Speed": ("RightBracket", self.DoubleGameSpeed),
            "Reset Game Speed": ("Backslash", self.ResetGameSpeed),
            "Save Position": ("Period", self.SavePosition),
            "Restore Position": ("Comma", self.RestorePosition),
            "Teleport Forward": ("Up", self.MoveForward),
            "Toggle World Freeze": ("Slash", self.TogglePlayersOnly),
            "Toggle HUD": ("Semicolon", self.ToggleHUD),
            "Toggle Damage Numbers": ("Quote", self.ToggleDamageNumbers),
            "Toggle Third Person": ("Equals", self.ToggleThirdPerson),
            "Quit Without Saving": ("End", self.QuitWithoutSaving),
        }

        self.Keybinds = [[key, value[0]] for key, value in self.GameInputs.items()]

    def SaveSettings(self):
        """Saves the current settings in JSON format to our settings file."""

        # Create a dictionary with our settings.
        settings = {"bindings": self.Bindings, "positions": self.Positions}
        # Save the settings dictionary to our settings file in JSON format.
        with open(self.SettingsPath, "w") as settingsFile:
            json.dump(settings, settingsFile, indent=4)

    def GameInputPressed(self, input):
        self.GameInputs[input.Name][1]()

    def GameInputRebound(self, name, key):
        self.Bindings[name] = key
        self.SaveSettings()

    def GetPlayerController(self):
        """Return the current WillowPlayerController object for the local player."""
        return unrealsdk.GetEngine().GamePlayers[0].Actor

    DefaultGameInfo = unrealsdk.FindObject(
        "WillowCoopGameInfo", "WillowGame.Default__WillowCoopGameInfo"
    )
    """A reference to the WillowCoopGameInfo template object."""
    # We use this for managing game speed, as transient WorldInfo objects pull
    # their TimeDilation from it.

    def Feedback(self, feedback):
        """Presents a "training" message to the user with the given string."""

        # Get the current player controller and the graphics object for its HUD.
        playerController = self.GetPlayerController()
        HUDMovie = playerController.GetHUDMovie()

        # If there is no graphics object, we cannot display feedback.
        if HUDMovie is None:
            return

        # We will be displaying the message for two *real time* seconds.
        duration = 2.0 * self.DefaultGameInfo.GameSpeed
        # Clear any previous message that may be displayed.
        HUDMovie.ClearTrainingText()
        # Present the training message as per the function's signature:
        #     AddTrainingText(string MessageString, string TitleString, float Duration, Color DrawColor, string HUDInitializationFrame, bool PausesGame, float PauseContinueDelay, PlayerReplicationInfo Related_PRI1, optional bool bIsntActuallyATrainingMessage, optional WillowPlayerController.EBackButtonScreen StatusMenuTab, optional bool bMandatory)
        HUDMovie.AddTrainingText(
            feedback,
            "Commander",
            duration,
            (),
            "",
            False,
            0,
            playerController.PlayerReplicationInfo,
            True,
        )

    def ConsoleCommand(self, command):
        """Performs the given string as a console command."""
        playerController = self.GetPlayerController()
        try:
            playerController.ConsoleCommand(command, 0)
        except:
            pass

    def ToggleThirdPerson(self):
        # Assume our local player controller is the first in the engine's list.
        playerController = self.GetPlayerController()
        # Check the state of the current player controller's camera. If it is
        # in third person, we will be switching to first, and vice versa.
        camera = "3rd" if playerController.UsingFirstPersonCamera() else "1st"
        # Perform the "camera" console command using the player controller, with
        # the argument as determined above.
        self.ConsoleCommand("camera " + camera)

    def HalveGameSpeed(self):
        speed = self.DefaultGameInfo.GameSpeed
        if speed > 0.0625:
            speed /= 2
            worldInfo = unrealsdk.GetEngine().GetCurrentWorldInfo()
            worldInfo.TimeDilation = speed
            self.DefaultGameInfo.GameSpeed = speed
        self.Feedback("Game Speed: " + str(Fraction(speed)))

    def DoubleGameSpeed(self):
        speed = self.DefaultGameInfo.GameSpeed
        if speed < 32:
            speed *= 2
            worldInfo = unrealsdk.GetEngine().GetCurrentWorldInfo()
            worldInfo.TimeDilation = speed
            self.DefaultGameInfo.GameSpeed = speed
        self.Feedback("Game Speed: " + str(Fraction(speed)))

    def ResetGameSpeed(self):
        worldInfo = unrealsdk.GetEngine().GetCurrentWorldInfo()
        worldInfo.TimeDilation = 1.0
        self.DefaultGameInfo.GameSpeed = 1.0
        self.Feedback("Game Speed: 1")

    def ToggleHUD(self):
        self.ConsoleCommand("ToggleHUD")

    DamageNumberEmitterObject = unrealsdk.FindObject(
        "ParticleSystem", "FX_CHAR_Damage_Matrix.Particles.Part_Dynamic_Number"
    )
    DamageNumberEmitters = list(DamageNumberEmitterObject.Emitters)
    NoDamageNumberEmitters = [
        None,
        None,
        DamageNumberEmitters[2],
        DamageNumberEmitters[3],
        DamageNumberEmitters[4],
        DamageNumberEmitters[5],
        DamageNumberEmitters[6],
        DamageNumberEmitters[7],
        DamageNumberEmitters[8],
        DamageNumberEmitters[9],
        DamageNumberEmitters[10],
        DamageNumberEmitters[11],
        DamageNumberEmitters[12],
        DamageNumberEmitters[13],
        DamageNumberEmitters[14],
        DamageNumberEmitters[15],
        DamageNumberEmitters[16],
    ]

    def ToggleDamageNumbers(self):
        if self.DamageNumberEmitterObject.Emitters[0] is None:
            self.DamageNumberEmitterObject.Emitters = self.DamageNumberEmitters
            self.Feedback("Damage Numbers: On")
        else:
            self.DamageNumberEmitterObject.Emitters = self.NoDamageNumberEmitters
            self.Feedback("Damage Numbers: Off")

    def GetMapName(self):
        return unrealsdk.GetEngine().GetCurrentWorldInfo().GetMapName(True)

    def GetRotationAndLocation(self):
        # Assume our local player controller is the first in the engine's list.
        playerController = self.GetPlayerController()
        # Our rotation struct is stored in the player controller, while our
        # location struct is stored in its associated pawn object.
        return playerController.Rotation, playerController.Pawn.Location

    def SavePosition(self):
        rotation, location = self.GetRotationAndLocation()
        position = {
            "X": location.X,
            "Y": location.Y,
            "Z": location.Z,
            "Pitch": rotation.Pitch,
            "Yaw": rotation.Yaw,
        }
        self.Positions[self.GetMapName()] = position
        self.SaveSettings()
        self.Feedback("Saved Position")

    def RestorePosition(self):
        mapName = self.GetMapName()
        if mapName in self.Positions:
            position = self.Positions[mapName]

            rotation, location = self.GetRotationAndLocation()

            location.X = position["X"]
            location.Y = position["Y"]
            location.Z = position["Z"]
            rotation.Pitch = position["Pitch"]
            rotation.Yaw = position["Yaw"]

            self.Feedback("Restored Position")
        else:
            self.Feedback("No Position Saved")

    RadiansConversion = 65535.0 / math.pi / 2.0

    def MoveForward(self):
        rotation, location = self.GetRotationAndLocation()

        pitch = rotation.Pitch / Commander.RadiansConversion
        yaw = rotation.Yaw / Commander.RadiansConversion

        location.Z += math.sin(pitch) * 250
        location.X += math.cos(yaw) * math.cos(pitch) * 250
        location.Y += math.sin(yaw) * math.cos(pitch) * 250

    def TogglePlayersOnly(self):
        # Get the current WorldInfo object from the engine.
        worldInfo = unrealsdk.GetEngine().GetCurrentWorldInfo()
        # Get the WorldInfo's current players only state.
        playersOnly = worldInfo.bPlayersOnly

        # Display the state we will be switching to to the user.
        self.Feedback("Players Only: " + ("Off" if playersOnly else "On"))
        # Apply the change.
        worldInfo.bPlayersOnly = not playersOnly

    def QuitWithoutSaving(self):
        self.ConsoleCommand("disconnect")


RegisterMod(Commander())
