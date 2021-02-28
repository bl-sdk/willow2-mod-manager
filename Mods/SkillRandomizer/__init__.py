import unrealsdk
from unrealsdk import *
import sys
import random
import json
import os

from ..ModManager import BL2MOD, RegisterMod
from Mods.ModMenu import Game, Hook


class CrossSkillRandomizer(BL2MOD):
    Name: str = "Cross Class Skill Randomizer ({})"
    Description: str = "Randomize all the skills!"
    Version: str = "1.2"
    Author: str = "Abahbob"
    SupportedGames = Game.BL2
    LocalModDir: str = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, seed=None):
        self.Seed = seed
        if seed:
            self.Name = self.Name.format(self.Seed)
        else:
            self.Name = self.Name.format("New Seed")

    def RecordSeed(self) -> None:
        with open(self.LocalModDir + "\\log.json", "r+") as f:
            history = json.loads(f.read())
            if self.Seed in history:
                return
            history.append(self.Seed)
            f.seek(0)
            f.write(json.dumps(history))
            f.truncate()
            self.Name = "Cross Class Skill Randomizer ({})".format(self.Seed)
            NewRando = CrossSkillRandomizer()
            unrealsdk.Mods.insert(0, NewRando)

    @Hook("WillowGame.PlayerSkillTree.Initialize")
    def InjectSkills(self, caller: UObject, function: UFunction, params: FStruct) -> bool:
        if not self.Seed:
            self.Seed = random.randrange(sys.maxsize)
            unrealsdk.Log("Randomizing with seed '{}'".format(self.Seed))
            self.RNG = random.Random(self.Seed)
            self.RecordSeed()
        else:
            self.RNG = random.Random(self.Seed)
        self.RandomizeTree(params.SkillTreeDef)
        return True

    def PreloadPackages(self) -> None:
        packages = [
            "GD_Assassin_Streaming_SF",
            "GD_Mercenary_Streaming_SF",
            "GD_Siren_Streaming_SF",
            "GD_Lilac_Psycho_Streaming_SF",
            "GD_Tulip_Mechro_Streaming_SF",
            "GD_Soldier_Streaming_SF",
        ]

        for package in packages:
            unrealsdk.LoadPackage(package)

    def RandomizeTree(self, SkillTreeDef) -> None:
        # SkillTreeDef.Root = GD_<Class>_Skills.SkillTree.Branch_ActionSkill_<ActionSkill>
        CurrentClass = SkillTreeDef.Root.Outer.Outer.GetName().split("_")[-2]
        self.ValidSkills = self.ClassSkills[CurrentClass].copy()
        self.ValidSkills += self.GlobalSkills
        for Branch in SkillTreeDef.Root.Children:
            self.RandomizeBranch(Branch)

    def RandomizeBranch(self, SkillTreeBranchDef) -> None:
        self.PreloadPackages()
        TierCountOdds = [95, 40, 80, 30, 80, 40]
        HasBloodlust = False
        HasHellborn = False
        for Tier in range(6):
            Pity = True
            TierLayout = [False, False, False]
            MaxPoints = 0
            NewSkills = []
            for Skill in range(3):
                if self.RNG.randint(0, 100) < TierCountOdds[Tier] or Skill == 2 and Pity:
                    if Skill == 2 and Pity:
                        Skill = self.RNG.randint(0, 2)
                    Pity = False
                    TierLayout[Skill] = True
                    SkillDefNum = self.RNG.randint(0, len(self.ValidSkills) - 1)
                    SkillDefName = self.ValidSkills.pop(SkillDefNum)
                    SkillDef = unrealsdk.FindObject("SkillDefinition", SkillDefName)
                    MaxPoints += SkillDef.MaxGrade
                    NewSkills.append(SkillDef)
                    HasHellborn = HasHellborn or "Hellborn" in SkillDef.GetFullName()
                    if not HasBloodlust and SkillDef.GetName() in [
                        "BloodfilledGuns",
                        "BloodyTwitch",
                    ]:
                        HasBloodlust = True
                        self.ValidSkills += self.BloodlustSkills
                    if SkillDef.GetName() == "Anarchy":
                        self.ValidSkills += self.AnarchySkills
            if HasBloodlust:
                NewSkills.append(unrealsdk.FindObject("SkillDefinition", "GD_Lilac_Skills_Bloodlust.Skills._Bloodlust"))
            if HasHellborn:
                NewSkills.append(
                    unrealsdk.FindObject(
                        "SkillDefinition",
                        "GD_Lilac_Skills_Hellborn.Skills.FireStatusDetector",
                    )
                )
                NewSkills.append(
                    unrealsdk.FindObject(
                        "SkillDefinition",
                        "GD_Lilac_Skills_Hellborn.Skills.AppliedStatusEffectListener",
                    )
                )
            SkillTreeBranchDef.Layout.Tiers[Tier].bCellIsOccupied = TierLayout
            SkillTreeBranchDef.Tiers[Tier].Skills = NewSkills
            SkillTreeBranchDef.Tiers[Tier].PointsToUnlockNextTier = min(MaxPoints, 5)

    ClassSkills = {
        "Soldier": [
            "GD_Soldier_Skills.Guerrilla.DoubleUp",
            "GD_Soldier_Skills.Guerrilla.LaserSight",
            "GD_Soldier_Skills.Guerrilla.ScorchedEarth",
            "GD_Soldier_Skills.Guerrilla.Sentry",
            "GD_Soldier_Skills.Gunpowder.Battlefront",
            "GD_Soldier_Skills.Gunpowder.LongBowTurret",
            "GD_Soldier_Skills.Gunpowder.Nuke",
            "GD_Soldier_Skills.Survival.Gemini",
            "GD_Soldier_Skills.Survival.Mag-Lock",
            "GD_Soldier_Skills.Survival.PhalanxShield",
        ],
        "Assassin": [
            "GD_Assassin_Skills.Bloodshed.Execute",
            "GD_Assassin_Skills.Bloodshed.Grim",
            "GD_Assassin_Skills.Bloodshed.ManyMustFall",
            "GD_Assassin_Skills.Cunning.DeathBlossom",
            "GD_Assassin_Skills.Cunning.Innervate",
            "GD_Assassin_Skills.Cunning.Unforseen",
        ],
        "Siren": [
            "GD_Siren_Skills.Cataclysm.ChainReaction",
            "GD_Siren_Skills.Cataclysm.Helios",
            "GD_Siren_Skills.Cataclysm.Ruin",
            "GD_Siren_Skills.Harmony.Elated",
            "GD_Siren_Skills.Harmony.Res",
            "GD_Siren_Skills.Harmony.SweetRelease",
            "GD_Siren_Skills.Harmony.Wreck",
            "GD_Siren_Skills.Motion.Converge",
            "GD_Siren_Skills.Motion.Quicken",
            "GD_Siren_Skills.Motion.SubSequence",
            "GD_Siren_Skills.Motion.Suspension",
            "GD_Siren_Skills.Motion.ThoughtLock",
        ],
        "Mercenary": [
            "GD_Mercenary_Skills.Brawn.AintGotTimeToBleed",
            "GD_Mercenary_Skills.Brawn.BusThatCantSlowDown",
            "GD_Mercenary_Skills.Brawn.ComeAtMeBro",
            "GD_Mercenary_Skills.Brawn.FistfulOfHurt",
            "GD_Mercenary_Skills.Gun_Lust.DivergentLikness",
            "GD_Mercenary_Skills.Gun_Lust.DownNotOut",
            "GD_Mercenary_Skills.Gun_Lust.KeepItPipingHot",
            "GD_Mercenary_Skills.Rampage.DoubleYourFun",
            "GD_Mercenary_Skills.Rampage.GetSome",
            "GD_Mercenary_Skills.Rampage.ImReadyAlready",
            "GD_Mercenary_Skills.Rampage.KeepFiring",
            "GD_Mercenary_Skills.Rampage.LastLonger",
            "GD_Mercenary_Skills.Rampage.SteadyAsSheGoes",
            "GD_Mercenary_Skills.Rampage.YippeeKiYay",
        ],
        "Lilac": [
            "GD_Lilac_Skills_Bloodlust.Skills.BloodTrance",
            "GD_Lilac_Skills_Bloodlust.Skills.BuzzAxeBombadier",
            "GD_Lilac_Skills_Bloodlust.Skills.TasteOfBlood",
            "GD_Lilac_Skills_Hellborn.Skills.HellfireHalitosis",
            "GD_Lilac_Skills_Mania.Skills.FuelTheRampage",
            "GD_Lilac_Skills_Mania.Skills.LightTheFuse",
            "GD_Lilac_Skills_Mania.Skills.ReleaseTheBeast",
        ],
        "Mechromancer": [
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.20PercentCooler",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.BuckUp",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.ExplosiveClap",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.MadeOfSternerStuff",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.PotentAsAPony",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.SharingIsCaring",
            "GD_Tulip_Mechromancer_Skills.BestFriendsForever.UpshotRobot",
            "GD_Tulip_Mechromancer_Skills.EmbraceChaos.AnnoyedAndroid",
            "GD_Tulip_Mechromancer_Skills.EmbraceChaos.RobotRampage",
            "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.MakeItSparkle",
            "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.OneTwoBoom",
            "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.StrengthOfFiveGorillas",
            "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.TheStare",
        ],
    }

    AnarchySkills = [
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.PreshrunkCyberpunk",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.Discord",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.TypecastIconoclast",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.RationalAnarchist",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.WithClaws",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.BloodSoakedShields",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.DeathFromAbove",
    ]

    BloodlustSkills = [
        "GD_Lilac_Skills_Bloodlust.Skills.BloodOverdrive",
        "GD_Lilac_Skills_Bloodlust.Skills.BloodyRevival",
        "GD_Lilac_Skills_Bloodlust.Skills.BloodBath",
        "GD_Lilac_Skills_Bloodlust.Skills.FuelTheBlood",
        "GD_Lilac_Skills_Bloodlust.Skills.BoilingBlood",
        "GD_Lilac_Skills_Bloodlust.Skills.NervousBlood",
        "GD_Lilac_Skills_Bloodlust.Skills.Bloodsplosion",
    ]

    GlobalSkills = [
        "GD_Assassin_Skills.Bloodshed.Backstab",
        "GD_Assassin_Skills.Bloodshed.BeLikeWater",
        "GD_Assassin_Skills.Bloodshed.Followthrough",
        "GD_Assassin_Skills.Bloodshed.IronHand",
        "GD_Assassin_Skills.Bloodshed.KillingBlow",
        "GD_Assassin_Skills.Bloodshed.LikeTheWind",
        "GD_Assassin_Skills.Bloodshed.Resurgence",
        "GD_Assassin_Skills.Cunning.Ambush",
        "GD_Assassin_Skills.Cunning.CounterStrike",
        "GD_Assassin_Skills.Cunning.DeathMark",
        "GD_Assassin_Skills.Cunning.FastHands",
        "GD_Assassin_Skills.Cunning.Fearless",
        "GD_Assassin_Skills.Cunning.RisingShot",
        "GD_Assassin_Skills.Cunning.TwoFang",
        "GD_Assassin_Skills.Sniping.AtOneWithTheGun",
        "GD_Assassin_Skills.Sniping.Bore",
        "GD_Assassin_Skills.Sniping.CriticalAscention",
        "GD_Assassin_Skills.Sniping.HeadShot",
        "GD_Assassin_Skills.Sniping.KillConfirmed",
        "GD_Assassin_Skills.Sniping.Killer",
        "GD_Assassin_Skills.Sniping.OneShotOneKill",
        "GD_Assassin_Skills.Sniping.Optics",
        "GD_Assassin_Skills.Sniping.Precision",
        "GD_Assassin_Skills.Sniping.Velocity",
        "GD_Lilac_Skills_Bloodlust.Skills.BloodfilledGuns",
        "GD_Lilac_Skills_Bloodlust.Skills.BloodyTwitch",
        "GD_Lilac_Skills_Hellborn.Skills.BurnBabyBurn",
        "GD_Lilac_Skills_Hellborn.Skills.DelusionalDamage",
        "GD_Lilac_Skills_Hellborn.Skills.ElementalElation",
        "GD_Lilac_Skills_Hellborn.Skills.ElementalEmpathy",
        "GD_Lilac_Skills_Hellborn.Skills.FireFiend",
        "GD_Lilac_Skills_Hellborn.Skills.FlameFlare",
        "GD_Lilac_Skills_Hellborn.Skills.FuelTheFire",
        "GD_Lilac_Skills_Hellborn.Skills.NumbedNerves",
        "GD_Lilac_Skills_Hellborn.Skills.PainIsPower",
        "GD_Lilac_Skills_Hellborn.Skills.RavingRetribution",
        "GD_Lilac_Skills_Mania.Skills.EmbraceThePain",
        "GD_Lilac_Skills_Mania.Skills.EmptyRage",
        "GD_Lilac_Skills_Mania.Skills.FeedTheMeat",
        "GD_Lilac_Skills_Mania.Skills.PullThePin",
        "GD_Lilac_Skills_Mania.Skills.RedeemTheSoul",
        "GD_Lilac_Skills_Mania.Skills.SaltTheWound",
        "GD_Lilac_Skills_Mania.Skills.SilenceTheVoices",
        "GD_Lilac_Skills_Mania.Skills.StripTheFlesh",
        "GD_Lilac_Skills_Mania.Skills.ThrillOfTheKill",
        "GD_Mercenary_Skills.Brawn.Asbestos",
        "GD_Mercenary_Skills.Brawn.Diehard",
        "GD_Mercenary_Skills.Brawn.ImTheJuggernaut",
        "GD_Mercenary_Skills.Brawn.Incite",
        "GD_Mercenary_Skills.Brawn.JustGotReal",
        "GD_Mercenary_Skills.Brawn.OutOfBubblegum",
        "GD_Mercenary_Skills.Brawn.SexualTyrannosaurus",
        "GD_Mercenary_Skills.Gun_Lust.AllIneedIsOne",
        "GD_Mercenary_Skills.Gun_Lust.AutoLoader",
        "GD_Mercenary_Skills.Gun_Lust.ImYourHuckleberry",
        "GD_Mercenary_Skills.Gun_Lust.LayWaste",
        "GD_Mercenary_Skills.Gun_Lust.LockedandLoaded",
        "GD_Mercenary_Skills.Gun_Lust.MoneyShot",
        "GD_Mercenary_Skills.Gun_Lust.NoKillLikeOverkill",
        "GD_Mercenary_Skills.Gun_Lust.QuickDraw",
        "GD_Mercenary_Skills.Rampage.5Shotsor6",
        "GD_Mercenary_Skills.Rampage.AllInTheReflexes",
        "GD_Mercenary_Skills.Rampage.FilledtotheBrim",
        "GD_Mercenary_Skills.Rampage.Inconceivable",
        "GD_Siren_Skills.Cataclysm.Backdraft",
        "GD_Siren_Skills.Cataclysm.BlightPhoenix",
        "GD_Siren_Skills.Cataclysm.CloudKill",
        "GD_Siren_Skills.Cataclysm.Flicker",
        "GD_Siren_Skills.Cataclysm.Foresight",
        "GD_Siren_Skills.Cataclysm.Immolate",
        "GD_Siren_Skills.Cataclysm.Reaper",
        "GD_Siren_Skills.Harmony.LifeTap",
        "GD_Siren_Skills.Harmony.MindsEye",
        "GD_Siren_Skills.Harmony.Recompense",
        "GD_Siren_Skills.Harmony.Restoration",
        "GD_Siren_Skills.Harmony.Scorn",
        "GD_Siren_Skills.Harmony.Sustenance",
        "GD_Siren_Skills.Motion.Accelerate",
        "GD_Siren_Skills.Motion.Fleet",
        "GD_Siren_Skills.Motion.Inertia",
        "GD_Siren_Skills.Motion.KineticReflection",
        "GD_Siren_Skills.Motion.Ward",
        "GD_Soldier_Skills.Guerrilla.Able",
        "GD_Soldier_Skills.Guerrilla.CrisisManagement",
        "GD_Soldier_Skills.Guerrilla.Grenadier",
        "GD_Soldier_Skills.Guerrilla.Onslaught",
        "GD_Soldier_Skills.Guerrilla.Ready",
        "GD_Soldier_Skills.Guerrilla.Willing",
        "GD_Soldier_Skills.Gunpowder.DoOrDie",
        "GD_Soldier_Skills.Gunpowder.DutyCalls",
        "GD_Soldier_Skills.Gunpowder.Expertise",
        "GD_Soldier_Skills.Gunpowder.Impact",
        "GD_Soldier_Skills.Gunpowder.MetalStorm",
        "GD_Soldier_Skills.Gunpowder.Overload",
        "GD_Soldier_Skills.Gunpowder.Ranger",
        "GD_Soldier_Skills.Gunpowder.Steady",
        "GD_Soldier_Skills.Survival.Forbearance",
        "GD_Soldier_Skills.Survival.Grit",
        "GD_Soldier_Skills.Survival.HealthY",
        "GD_Soldier_Skills.Survival.LastDitchEffort",
        "GD_Soldier_Skills.Survival.Preparation",
        "GD_Soldier_Skills.Survival.Pressure",
        "GD_Soldier_Skills.Survival.QuickCharge",
        "GD_Tulip_Mechromancer_Skills.BestFriendsForever.CloseEnough",
        "GD_Tulip_Mechromancer_Skills.BestFriendsForever.CookingUpTrouble",
        "GD_Tulip_Mechromancer_Skills.BestFriendsForever.FancyMathematics",
        "GD_Tulip_Mechromancer_Skills.BestFriendsForever.TheBetterHalf",
        "GD_Tulip_Mechromancer_Skills.BestFriendsForever.UnstoppableForce",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.Anarchy",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.SmallerLighterFaster",
        "GD_Tulip_Mechromancer_Skills.EmbraceChaos.TheNthDegree",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.ElectricalBurn",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.EvilEnchantress",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.InterspersedOutburst",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.MorePep",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.Myelin",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.ShockAndAAAGGGHHH",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.ShockStorm",
        "GD_Tulip_Mechromancer_Skills.LittleBigTrouble.WiresDontTalk",
    ]


rando = CrossSkillRandomizer()

RegisterMod(rando)

if os.path.isfile(rando.LocalModDir + "\\log.json"):
    with open(rando.LocalModDir + "\\log.json", "r") as f:
        seeds = json.loads(f.read())
        for seed in seeds:
            RegisterMod(CrossSkillRandomizer(seed))
else:
    with open(rando.LocalModDir + "\\log.json", "w") as f:
        f.write("[]")
