import bl2sdk
import os
import sys
import json
import re

from ..ModManager import BL2MOD, RegisterMod

class LegacyMod(BL2MOD):

    BinariesDirectory = os.path.dirname(os.path.dirname(sys.executable))
    """The path to the game's Binaries directory; this is the parent directory from
	which we are executed."""

    LocalModDir = os.path.dirname(os.path.realpath(__file__))

    SettingsPath = os.path.join(LocalModDir, "settings.json")
    """The path to the file in which we store our settings."""

    def LoadSettings():
        """Attempts to load the user's settings from their settings file."""
        try:
            with open(LegacyMod.SettingsPath) as settingsFile:
                # Decode the JSON data contained in the settings file.
                settings = json.load(settingsFile)
                # Convert the settings file's list of ignored files to a set for
                # our own usage.
                LegacyMod.IgnoredFiles = set(settings["ignored_files"])
        # If this fails, set up empty values for our settings.
        except:
            LegacyMod.IgnoredFiles = set()

    def SaveSettings():
        """Saves the current settings in JSON format to our settings file."""

        # Create a dictionary with our settings.
        settings = {"ignored_files": list(LegacyMod.IgnoredFiles)}
        # Save the settings dictionary to our settings file in JSON format.
        with open(LegacyMod.SettingsPath, "w") as settingsFile:
            json.dump(settings, settingsFile, indent=4)

    def Populate():
        """Populates the mods menu with legacy mods based on the files in the
		user's Binaries directory."""

        # Create a dictionary to track edits performed by multiple by mods. Keys
        # are "[object] [property]" strings, values are sets containing all
        # the mods which edit said pairs.
        edits = dict()

        # Create a set to track each mod that has at least one conflict, so we
        # may address them after all conflicts have been determined.
        conflictedMods = set()

        # Iterate over each file in the user's Binaries directory.
        for filename in os.listdir(LegacyMod.BinariesDirectory):
            # If the file is in our list of ignored ones, skip to the next.
            if filename in LegacyMod.IgnoredFiles:
                continue

            # We will be either locating or creating a mod object for this file.
            mod = None
            # Iterate over each existing mod in the menu.
            for existingMod in bl2sdk.Mods:
                # If the mod is a legacy mod and has the same file name as our
                # own, we will be using that.
                if type(existingMod) is LegacyMod and existingMod.Filename == filename:
                    mod = existingMod
                    break

            # If we did not locate an object for this file, we create one now.
            if mod == None:
                # If the file is not a file, skip it.
                if not os.path.isfile(
                    os.path.join(LegacyMod.BinariesDirectory, filename)
                ):
                    continue
                # Create the new legacy mod object and add it to the mods menu.
                mod = LegacyMod(filename)
                RegisterMod(mod)

            # Create a set to store a list of any and all mods we determine this
            # mod to conflict with.
            mod.Conflicts = set()

            # Tell the mod to update its list of edits if necessary, then we
            # iterate over each one.
            mod.Update()
            for edit in mod.Edits:
                # If a set has already been create for the given edit, it
                # indicates a conflict between this mod and those in the set.
                if edit in edits:
                    # Add this mod to the set of mods performing the edit.
                    edits[edit].add(mod)
                    # Iterate over each mod currently affected by this conflict.
                    for conflictedMod in edits[edit]:
                        # Add the mods which conflict over this edit to this
                        # mod's overall set of conflicting mods.
                        conflictedMod.Conflicts |= edits[edit]
                        # Add this mod to our running set of mods that have
                        # any conflicts.
                        conflictedMods.add(conflictedMod)
                # If a set has not yet been created for the given edit, there is
                # no conflict (yet), so simply start a set with this mod in it.
                else:
                    edits[edit] = {mod}

        # Iterate over each mod that has at least one conflict.
        for mod in conflictedMods:
            # From the list of conflicts with this mod (minus itself), generate
            # a list of each mods' name.
            conflicts = [
                conflictingMod.Name for conflictingMod in (mod.Conflicts - {mod})
            ]
            # Update the mod's description with a warning message that includes
            # the list of mod names.
            mod.Description += (
                "\n\nWARNING: This may conflict with the following mods: "
                + ", ".join(conflicts)
            )
            # Unset the mod's list of conflicts.
            del mod.Conflicts

    # The default UI options for each legacy mod.
    Status = "Not Executed"
    SettingsInputs = {"Enter": "Execute", "Delete": "Hide Mod", "Insert": "Unhide Mods"}

    UpdatedTime = None
    ExecutedTime = None
    Edits = None

    def __init__(self, filename):
        """Initialize a new legacy mod object with the name of a file in the
		game's Binaries directory."""

        # Store the mod's file name and path.
        self.Filename = filename
        self.Filepath = os.path.join(LegacyMod.BinariesDirectory, filename)

        # Use the base name of the file as the name that will be displayed in
        # the mods menu.
        self.Name, _ = os.path.splitext(filename)

    SetPattern = re.compile(
        r"\s*set\s+(\S+)\s+(\w+)\S*\s+(?:\((.+)\))?\s*", re.IGNORECASE
    )
    """The regular expression used to match set commands. The object name is
	captured in the first group, and is assumed to be all non-whitespace that
	follows any whitespace after the the word "set" at the start of the line.
	The property is captured by the second group, and is assumed to be all word
	characters following any whitespace after the object name (any non-
	whitespace "suffixes" to the property are ignored). The value is ignored,
	unless it is enclosed in parentheses (possibly an array), in which case the
	contents of the parentheses is captured for later interpretation."""
    HotfixPattern = re.compile(r"^[^,]*,([^,]+),(\w+)")
    """The default regular expression used to match hotfix value strings. The
	contents up until the first comma are ignored. The object name is captured
	by the first group, and is assumed to be all characters between the first
	and second commas. The property name is captured by the second group, and is
	assumed to be all word characters after the second comma."""
    PatchHotfixPattern = re.compile(r"^([^,]+),(\w+)")
    """The default regular expression used to match hotfix value strings. The
	object name is captured by the first group, and is assumed to be all
	characters between the first and second commas. The property name is
	captured by the second group, and is assumed to be all word characters after
	the second comma."""
    GearboxHotfixes = [
        ",GD_Balance.WeightingPlayerCount.BugmorphCocoon_PerPlayers_Phase1,ConditionalInitialization.ConditionalExpressionList[4].BaseValueIfTrue.BaseValueConstant,0.700000,.8",
        ",GD_Balance.WeightingPlayerCount.BugmorphCocoon_PerPlayers_Phase2,ConditionalInitialization.ConditionalExpressionList[4].BaseValueIfTrue.BaseValueConstant,0.400000,.5",
        ",GD_Balance.WeightingPlayerCount.BugmorphCocoon_PerPlayers_Phase3,ConditionalInitialization.ConditionalExpressionList[4].BaseValueIfTrue.BaseValueConstant,0.200000,.3",
        ",GD_Balance.WeightingPlayerCount.BugmorphCocoon_PerPlayers_Phase4,ConditionalInitialization.ConditionalExpressionList[4].BaseValueIfTrue.BaseValueConstant,0.100000,.2",
        ",GD_Balance.WeightingPlayerCount.BugmorphCocoon_PerPlayers_Phase5,ConditionalInitialization.ConditionalExpressionList[4].BaseValueIfTrue.BaseValueConstant,0.075000,.1",
        "SouthpawFactory_P,GD_Population_Marauder.Balance.Unique.PawnBalance_Assassin1,DefaultItemPoolList[3].PoolProbability.BaseValueScaleConstant,0.250000,1",
        "SouthpawFactory_P,GD_Population_Nomad.Balance.Unique.PawnBalance_Assassin2,DefaultItemPoolList[4].PoolProbability.BaseValueScaleConstant,0.250000,1",
        "SouthpawFactory_P,GD_Population_Psycho.Balance.Unique.PawnBalance_Assassin3,DefaultItemPoolList[1].PoolProbability.BaseValueScaleConstant,0.250000,1",
        "SouthpawFactory_P,GD_Population_Rat.Balance.Unique.PawnBalance_Assassin4,DefaultItemPoolList[3].PoolProbability.BaseValueScaleConstant,0.250000,1",
        ",GD_Sage_Rare_Scaylion.Population.PawnBalance_Sage_Rare_Scaylion,DefaultItemPoolList[1].PoolProbability.BaseValueScaleConstant,1.000000,100",
        ",GD_Sage_Rare_Drifter.Balance.PawnBalance_Sage_Rare_Drifter,DefaultItemPoolList[0].PoolProbability.BaseValueScaleConstant,1.000000,100",
        ",GD_Sage_Rare_Rhino.Population.PawnBalance_Sage_Rare_Rhino,DefaultItemPoolList[1].PoolProbability.BaseValueScaleConstant,1.000000,100",
        ",GD_Sage_Rare_Skag.Population.PawnBalance_Sage_Rare_Skag,DefaultItemPoolList[1].PoolProbability.BaseValueScaleConstant,1.000000,100",
        ",GD_Sage_Rare_Spore.Population.PawnBalance_Sage_Rare_Spore,DefaultItemPoolList[0].PoolProbability.BaseValueScaleConstant,1.000000,100",
        "GD_Assassin_Streaming,GD_Assassin_Skills.Sniping.Velocity,SkillEffectDefinitions[0].ModifierType,MT_PostAdd,MT_Scale",
        "GD_Tulip_Mechro_Streaming,GD_Tulip_Mechromancer_Skills.LittleBigTrouble.WiresDontTalk,SkillEffectDefinitions,,((AttributeToModify=D_Attributes.DamageTypeModifers.InstigatedShockDamageModifier,bIncludeDuelingTargets=False,bIncludeSelfAsTarget=False,bOnlyEffectTargetsInRange=False,bExcludeNonPlayerCharacters=False,EffectTarget=TARGET_Self,TargetInstanceDataName=,TargetCriteria=CRITERIA_None,ModifierType=MT_Scale,BaseModifierValue=(BaseValueConstant=0.030000,BaseValueAttribute=None,InitializationDefinition=None,BaseValueScaleConstant=1.000000),GradeToStartApplyingEffect=1,PerGradeUpgradeInterval=1,PerGradeUpgrade=(BaseValueConstant=0.030000,BaseValueAttribute=None,InitializationDefinition=None,BaseValueScaleConstant=1.000000),BonusUpgradeList=),(AttributeToModify=D_Attributes.DamageTypeModifers.InstigatedShockStatusDamageModifier,bIncludeDuelingTargets=False,bIncludeSelfAsTarget=False,bOnlyEffectTargetsInRange=False,bExcludeNonPlayerCharacters=False,EffectTarget=TARGET_Self,TargetInstanceDataName=,TargetCriteria=CRITERIA_None,ModifierType=MT_Scale,BaseModifierValue=(BaseValueConstant=0.030000,BaseValueAttribute=None,InitializationDefinition=None,BaseValueScaleConstant=1.000000),GradeToStartApplyingEffect=1,PerGradeUpgradeInterval=1,PerGradeUpgrade=(BaseValueConstant=0.030000,BaseValueAttribute=None,InitializationDefinition=None,BaseValueScaleConstant=1.000000),BonusUpgradeList=))",
        "GD_Siren_Streaming,GD_Siren_Skills.Misc.Init_BlightPhoenix_DamageCalc_Part2,ValueFormula.Level.InitializationDefinition,AttributeInitializationDefinition'GD_Balance_HealthAndDamage.HealthAndDamage.Init_PlayerMeleeDamage',AttributeInitializationDefinition'GD_Balance_HealthAndDamage.HealthAndDamage.Init_PlayerSkillDamage'",
        "GD_Siren_Streaming,GD_Siren_Skills.Misc.Init_BlightPhoenix_DamageCalc_Part2,ValueFormula.Level.BaseValueScaleConstant,1.000000,3.5",
        "GD_Assassin_Streaming,GD_Assassin_Skills.Misc.Att_DeathMark_BonusDamage,BaseValue.BaseValueConstant,0.200000,.8",
        "GD_Itempools.Runnables.Pool_FourAssassins,BalancedItems[1].Probability.InitializationDefinition,None,GD_Balance.Weighting.Weight_1_Common",
        "GD_Shields.Projectiles.Proj_LegendaryBoosterShield:BehaviorProviderDefinition_1.Behavior_Explode_140,BehaviorSequences[0].BehaviorData2[7].Behavior.StatusEffectDamage.BaseValueAttribute,None,D_Attributes.Projectile.ProjectileDamage",
        "GD_Shields.Projectiles.Proj_LegendaryBoosterShield:BehaviorProviderDefinition_1.Behavior_Explode_140,BehaviorSequences[0].BehaviorData2[7].Behavior.StatusEffectDamage.BaseValueScaleConstant,1.000000,.25",
        "GD_Shields.Projectiles.Proj_LegendaryBoosterShield:BehaviorProviderDefinition_1.Behavior_Explode_140,BehaviorSequences[0].BehaviorData2[7].Behavior.StatusEffectChance.BaseValueConstant,1.000000,20",
    ]
    """The list of vanilla Gearbox hotfix values that are expected to be
	included in many mods, and as such should be ignored when considering edits."""

    def Update(self):
        """Updates the mod's description and list of edits that it performs."""

        # Reset our description to provide just the basic legacy mod info.
        self.Description = (
            "Mod file found at: %s\n\nUse BLCMM to edit options for this mod."
            % self.Filepath
        )

        # Get the last modified time of the mod file from the OS.
        modifiedTime = os.path.getmtime(self.Filepath)

        # If we have executed the mod at a time previous to the modification
        # time, update the description to provide the relevant warning.
        if self.ExecutedTime != None and self.ExecutedTime < modifiedTime:
            self.Description += "\n\nWARNING: This mod has been edited since being executed. Relaunching Borderlands 2 is recommended for changes to function."

        # If we have previously updated our values from the file, and it has not
        # been modified since the time we recorded doing so, nothing to do now.
        if self.UpdatedTime != None and self.UpdatedTime >= modifiedTime:
            return

        # Record the file's new modification time as the time we last updated
        # our values from it.
        self.UpdatedTime = modifiedTime

        # Reset the list of game object/property pairs edited by this mod.
        self.Edits = set()

        # Create new lists in which to store the keys and values of hotfixes
        # inserted by this mod (if any).
        hotfixKeys = []
        hotfixValues = []

        # Open the file for reading, and iterate over it line by line.
        with open(self.Filepath, "r") as file:
            for line in file:
                # Attempt to match the line with the set command pattern. If the
                # line does not appear to contain a set command, we skip it.
                setMatch = LegacyMod.SetPattern.fullmatch(line)
                if setMatch == None:
                    continue

                # If the object name in the set command indicates it is one of
                # the hotfix edits, we will be parsing lists of individual
                # object/property edits out of it.
                if setMatch.group(1).startswith("Transient.SparkServiceConfiguration_"):
                    # Given enclosing brackets, the contents of the parentheses
                    # denoting the hotfix's keys and value arrays match JSON
                    # array syntax. Don't judge me.
                    items = json.loads("[%s]" % setMatch.group(3))
                    # Store the parsed hotfix data in the relevant array.
                    if setMatch.group(2).lower() == "keys":
                        hotfixKeys = items
                    elif setMatch.group(2).lower() == "values":
                        hotfixValues = items
                # If this edit wasn't being performed on a hotfix object, simply
                # add it to our edits in the "[object] [property]" format.
                else:
                    self.Edits.add(setMatch.group(1) + " " + setMatch.group(2))

            # Iterate over key/value pairs in the order in which they appear in
            # their respective arrays.
            for key, value in zip(hotfixKeys, hotfixValues):
                # If the value is one of the known vanilla Gearbox hotfixes,
                # ignore it, as it is intended to reoccur across multiple mods.
                if value in LegacyMod.GearboxHotfixes:
                    continue

                # If the hotfix's key indicates that it is a Patch-type hotfix,
                # we will match its value using the relevant pattern; otherwise
                # we use the default one.
                hotfixPattern = (
                    LegacyMod.PatchHotfixPattern
                    if key.startswith("SparkPatchEntry")
                    else LegacyMod.HotfixPattern
                )
                valueMatch = hotfixPattern.match(value)

                # If the pattern did match the hotfix's value, add the edit it
                # describes to our edits in the "[object] [property]" format.
                if valueMatch != None:
                    self.Edits.add(valueMatch.group(1) + " " + valueMatch.group(2))

    def Execute(self):
        """Invoked by the SDK when our mod is enabled from the mods menu."""

        # We will be looking up the object responsible for storing hotfixes.
        micropatch = None
        for service in bl2sdk.FindObject(
            "GearboxAccountData", "Transient.GearboxAccountData_1"
        ).Services:
            # If the service's name is "micropatch" then it is the hotfix
            # object, and we are done.
            if service.ServiceName == "Micropatch":
                micropatch = service
                break

        # Create a dictionary of the existing hotfixes using the hotfix
        # objects's keys and values properties. Since we are interested in
        # unique hotfix values rather than keys, invert the mapping from keys to
        # values for our representation.
        hotfixes = dict(zip(micropatch.Values, micropatch.Keys))

        # Prevent a crash when the `set` console command attempts to update
        # arrays which were previously allocated by the SDK.
        micropatch.Keys = []
        micropatch.Values = []

        # Obtain the current player controller object.
        playerController = bl2sdk.GetEngine().GamePlayers[0].Actor
        try:
            # Use the controller to perform a console command executing the
            # legacy mod file. We wrap this in a `try` statement to suppress the
            # SDK's return value error.
            playerController.ConsoleCommand('exec "' + self.Filename + '"', 0)
        except:
            pass

        # If the executed file contained hotfixes, the hotfix object's
        # properties will now contain their keys and values. Update our
        # dictionary with these, inverting their mapping as described above.
        hotfixes.update(zip(micropatch.Values, micropatch.Keys))

        # Generate new lists from the final hotfix dictionary's keys and values,
        # and apply them to the hotfix object.
        micropatch.Keys = list(hotfixes.values())
        micropatch.Values = list(hotfixes.keys())

        # If we have not previously executed this file, record its last modified
        # time at time of execution, and update its UI to reflect its status.
        if self.ExecutedTime == None:
            self.ExecutedTime = os.path.getmtime(self.Filepath)
            self.Status = "Executed"
            self.SettingsInputs = {"Enter": "Re-execute", "Insert": "Unhide Mods"}

    def SettingsInputPressed(self, name):
        """Called by the SDK when a key we've registered for is pressed."""

        # When the enter key is pressed, we perform the mod's execution.
        if name == "Execute" or name == "Re-execute":
            self.Execute()

        # When the delete key is pressed, we add the mod's file name to our list
        # of ignored files, then remove it from the SDK's mod list.
        elif name == "Hide Mod":
            LegacyMod.IgnoredFiles.add(self.Filename)
            LegacyMod.SaveSettings()
            bl2sdk.Mods.remove(self)

        # When the insert key is pressed, reset our list of ignored files, then
        # re-populate the SDK's mods menu.
        elif name == "Unhide Mods":
            LegacyMod.IgnoredFiles = set()
            LegacyMod.SaveSettings()
            LegacyMod.Populate()


# On launch, load our settings.
LegacyMod.LoadSettings()
# Add a hook to populate the SDK's mod menu each time it is opened.
bl2sdk.ModMenuOpened.append(LegacyMod.Populate)
