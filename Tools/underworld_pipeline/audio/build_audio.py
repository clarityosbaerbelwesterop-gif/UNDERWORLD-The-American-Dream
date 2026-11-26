"""`Tools/uwp build-audio` - render the complete procedural audio library (T-AUD-01).

    python3 -m underworld_pipeline.audio.build_audio [--repo R] [--only PATTERN] [--list] [--spectrograms DIR]

Outputs
  Assets/Audio/<Folder>/<EVENT>[_NN].ogg       Ogg Vorbis, 48 kHz (mono for 3D one-shots, stereo for beds/music/UI)
  Assets/Audio/audio.manifest.json             per-file metadata (duration, peak, RMS, channels, seed, loop, sha256)
  GodotProject/Data/Content/audio.json         runtime event table for the AudioDirector autoload

Every event is deterministic: seed = crc32(event id) + variation index, so a re-render is bit-stable
for the same numpy/scipy versions. Nothing third-party is sampled; licence = project-original.
"""
import argparse
import fnmatch
import hashlib
import json
import math
import os
import sys
import time
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(TOOLS, ".."))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from underworld_pipeline.audio import ambience as A  # noqa: E402
from underworld_pipeline.audio import dsp as D  # noqa: E402
from underworld_pipeline.audio import foley as F  # noqa: E402
from underworld_pipeline.audio import music as M  # noqa: E402
from underworld_pipeline.audio import vehicles as V  # noqa: E402
from underworld_pipeline.audio import weapons as W  # noqa: E402

AUDIO_ROOT = "Assets/Audio"
RUNTIME_TABLE = "GodotProject/Data/Content/audio.json"

# Godot buses (GodotProject/default_bus_layout.tres). 3D = positional (AudioStreamPlayer3D).
BUSES = ["Master", "Music", "SFX", "Weapons", "Vehicles", "Foley", "Ambience", "UI", "VO"]


def ev(eid, folder, fn, bus, n=1, loop=False, is3d=True, vol=0.0, pitch=0.04, unit=8.0, maxd=120.0, stereo=None,
       desc=""):
    return dict(id=eid, folder=folder, fn=fn, bus=bus, n=n, loop=loop, is3d=is3d, volume_db=vol, pitch_jitter=pitch,
                unit_size=unit, max_distance=maxd, stereo=(not is3d) if stereo is None else stereo, desc=desc)


def build_registry():
    R = []
    # ---------------------------------------------------------------- weapons
    for w in W.WEAPONS:
        R.append(ev(f"SFX_WPN_{w}_Fire", "Weapons", (lambda rng, v, w=w: W.gunshot_close(rng, w, v)), "Weapons", n=4,
                    vol=0.0, pitch=0.035, unit=14.0, maxd=180.0, desc=f"{w} shot, close perspective"))
        R.append(ev(f"SFX_WPN_{w}_Tail", "Weapons", (lambda rng, v, w=w: W.gunshot_tail(rng, w, v)), "Weapons", n=2,
                    vol=-6.0, pitch=0.03, unit=45.0, maxd=600.0, stereo=True, desc=f"{w} environmental tail / distant layer"))
    handling = [
        ("SFX_WPN_DryFire", W.dry_fire, 2), ("SFX_WPN_MagOut_Pistol", W.mag_out, 2),
        ("SFX_WPN_MagIn_Pistol", W.mag_in, 2), ("SFX_WPN_SlideRack", W.slide_rack, 2),
        ("SFX_WPN_MagOut_Rifle", lambda r, v: W.mag_out(r, v, True), 2),
        ("SFX_WPN_MagIn_Rifle", lambda r, v: W.mag_in(r, v, True), 2), ("SFX_WPN_BoltAction", W.bolt_action, 2),
        ("SFX_WPN_Shotgun_Pump", W.shotgun_pump, 2), ("SFX_WPN_Shotgun_ShellLoad", W.shell_load, 3),
        ("SFX_WPN_Revolver_Cylinder", W.revolver_cylinder, 2), ("SFX_WPN_ShellCasing", W.shell_casing, 6),
        ("SFX_WPN_Equip", W.equip, 3),
    ]
    for eid, fn, n in handling:
        R.append(ev(eid, "Weapons/Handling", fn, "Weapons", n=n, vol=-4.0, unit=3.0, maxd=25.0))
    # melee + throwables
    R.append(ev("SFX_MEL_Swing", "Melee", lambda r, v: W.whoosh(r, v), "Weapons", n=4, vol=-3.0, unit=3.0, maxd=20.0))
    R.append(ev("SFX_MEL_Swing_Heavy", "Melee", lambda r, v: W.whoosh(r, v, True), "Weapons", n=3, vol=-2.0, unit=3.0, maxd=20.0))
    R.append(ev("SFX_MEL_Punch", "Melee", W.punch, "Weapons", n=4, unit=4.0, maxd=30.0))
    R.append(ev("SFX_MEL_Bat_Hit", "Melee", W.bat_hit, "Weapons", n=3, unit=5.0, maxd=40.0))
    R.append(ev("SFX_MEL_Knife_Hit", "Melee", W.knife_hit, "Weapons", n=3, unit=3.0, maxd=25.0))
    R.append(ev("SFX_WPN_Grenade_Pin", "Weapons/Throwables", W.grenade_pin, "Weapons", n=1, vol=-4.0, unit=3.0, maxd=20.0))
    R.append(ev("SFX_WPN_Grenade_Bounce", "Weapons/Throwables", W.grenade_bounce, "Weapons", n=3, vol=-4.0, unit=4.0, maxd=30.0))
    R.append(ev("SFX_WPN_Molotov_Break", "Weapons/Throwables", W.molotov_break, "Weapons", n=2, unit=10.0, maxd=90.0))
    # ---------------------------------------------------------------- impacts / bullets
    for s in ("Concrete", "Metal", "Glass", "Wood", "Flesh", "Dirt", "Water"):
        R.append(ev(f"SFX_IMP_{s}", "Impacts", (lambda r, v, s=s: W.impact(r, s, v)), "SFX", n=4, vol=-2.0,
                    pitch=0.08, unit=5.0, maxd=60.0))
    R.append(ev("SFX_IMP_Ricochet", "Impacts", W.ricochet, "SFX", n=4, vol=-4.0, unit=6.0, maxd=70.0))
    R.append(ev("SFX_BUL_Flyby", "Impacts", W.bullet_flyby, "SFX", n=3, vol=-3.0, unit=3.0, maxd=20.0, stereo=False))
    # ---------------------------------------------------------------- explosions / destruction / fx
    R.append(ev("SFX_EXP_Grenade", "Explosions", lambda r, v: W.explosion(r, v, 0.7), "SFX", n=2, unit=30.0, maxd=700.0, stereo=True))
    R.append(ev("SFX_EXP_Large", "Explosions", lambda r, v: W.explosion(r, v, 1.0), "SFX", n=2, unit=40.0, maxd=900.0, stereo=True))
    R.append(ev("SFX_EXP_Vehicle", "Explosions", lambda r, v: W.explosion(r, v, 1.25), "SFX", n=2, unit=40.0, maxd=900.0, stereo=True))
    R.append(ev("SFX_GLASS_Shatter", "Destruction", lambda r, v: W.glass_shatter(r, v), "SFX", n=3, unit=8.0, maxd=80.0))
    R.append(ev("SFX_GLASS_Shatter_Large", "Destruction", lambda r, v: W.glass_shatter(r, v, True), "SFX", n=2, unit=10.0, maxd=100.0))
    R.append(ev("SFX_FIRE_Loop", "FX", lambda r, v: A.fire_loop(r, 8.0), "SFX", loop=True, unit=6.0, maxd=50.0, stereo=True))
    R.append(ev("SFX_FIRE_Loop_Large", "FX", lambda r, v: A.fire_loop(r, 8.0, True), "SFX", loop=True, unit=10.0, maxd=90.0, stereo=True))
    R.append(ev("SFX_STEAM_Loop", "FX", lambda r, v: A.steam_loop(r, 6.0), "SFX", loop=True, unit=3.0, maxd=30.0, stereo=True))
    R.append(ev("SFX_SPARKS_Loop", "FX", lambda r, v: A.sparks_loop(r, 5.0), "SFX", loop=True, unit=3.0, maxd=30.0, stereo=True))
    # ---------------------------------------------------------------- foley
    for s in F.SURFACES:
        R.append(ev(f"SFX_FS_{s}_Walk", "Foley/Footsteps", (lambda r, v, s=s: F.footstep(r, s, v, False)), "Foley", n=6,
                    vol=-6.0, pitch=0.06, unit=2.0, maxd=25.0))
        R.append(ev(f"SFX_FS_{s}_Run", "Foley/Footsteps", (lambda r, v, s=s: F.footstep(r, s, v, True)), "Foley", n=6,
                    vol=-4.0, pitch=0.06, unit=2.5, maxd=30.0))
    R.append(ev("SFX_FOL_Jump", "Foley", F.jump, "Foley", n=3, vol=-4.0, unit=2.0, maxd=20.0))
    R.append(ev("SFX_FOL_Land", "Foley", F.land, "Foley", n=3, vol=-3.0, unit=2.5, maxd=25.0))
    R.append(ev("SFX_FOL_Land_Heavy", "Foley", lambda r, v: F.land(r, v, True), "Foley", n=2, vol=-1.0, unit=3.0, maxd=30.0))
    R.append(ev("SFX_FOL_Cloth", "Foley", F.cloth, "Foley", n=5, vol=-8.0, unit=1.5, maxd=10.0))
    R.append(ev("SFX_FOL_BodyFall", "Foley", F.body_fall, "Foley", n=3, unit=4.0, maxd=35.0))
    R.append(ev("SFX_FOL_Pickup_Cash", "Foley", lambda r, v: F.pickup_item(r, v, "cash"), "Foley", n=2, vol=-3.0, unit=2.0, maxd=12.0))
    R.append(ev("SFX_FOL_Pickup_Item", "Foley", lambda r, v: F.pickup_item(r, v, "item"), "Foley", n=2, vol=-3.0, unit=2.0, maxd=12.0))
    # ---------------------------------------------------------------- vehicles
    for kind in V.ENGINES:
        for layer in ("Idle", "Low", "High"):
            R.append(ev(f"SFX_VEH_{kind}_Engine_{layer}", "Vehicles/Engines", (lambda r, v, k=kind, l=layer: V.engine_layer(r, k, l)),
                        "Vehicles", loop=True, pitch=0.0, unit=8.0, maxd=150.0))
        R.append(ev(f"SFX_VEH_{kind}_Start", "Vehicles/Engines", (lambda r, v, k=kind: V.engine_start(r, k)), "Vehicles",
                    pitch=0.02, unit=6.0, maxd=60.0))
        R.append(ev(f"SFX_VEH_{kind}_Stop", "Vehicles/Engines", (lambda r, v, k=kind: V.engine_stop(r, k)), "Vehicles",
                    pitch=0.02, unit=6.0, maxd=60.0))
    for layer in ("Idle", "Low", "High"):
        R.append(ev(f"SFX_VEH_Prop_Engine_{layer}", "Vehicles/Engines", (lambda r, v, l=layer: V.propeller(r, l)), "Vehicles",
                    loop=True, pitch=0.0, unit=18.0, maxd=600.0))
    R.append(ev("SFX_VEH_Tire_Skid", "Vehicles", lambda r, v: V.tire_skid(r), "Vehicles", loop=True, pitch=0.0, unit=8.0, maxd=90.0))
    R.append(ev("SFX_VEH_Road_Roll", "Vehicles", lambda r, v: V.road_roll(r), "Vehicles", loop=True, pitch=0.0, unit=5.0, maxd=50.0))
    R.append(ev("SFX_VEH_Crash_Light", "Vehicles", lambda r, v: V.crash(r, v), "Vehicles", n=3, unit=12.0, maxd=120.0))
    R.append(ev("SFX_VEH_Crash_Heavy", "Vehicles", lambda r, v: V.crash(r, v, True), "Vehicles", n=3, unit=18.0, maxd=200.0))
    R.append(ev("SFX_VEH_Door_Open", "Vehicles", lambda r, v: V.door(r, v, True), "Vehicles", n=2, unit=3.0, maxd=25.0))
    R.append(ev("SFX_VEH_Door_Close", "Vehicles", lambda r, v: V.door(r, v, False), "Vehicles", n=3, unit=4.0, maxd=35.0))
    R.append(ev("SFX_VEH_Horn", "Vehicles", lambda r, v: V.horn(r, 1.0), "Vehicles", loop=True, pitch=0.0, unit=15.0, maxd=200.0))
    R.append(ev("SFX_VEH_Horn_Honk", "Vehicles", V.horn_honk, "Vehicles", n=2, pitch=0.02, unit=15.0, maxd=200.0))
    R.append(ev("SFX_VEH_Siren_Wail", "Vehicles/Sirens", lambda r, v: V.siren(r, "Wail"), "Vehicles", loop=True, pitch=0.0, unit=25.0, maxd=500.0))
    R.append(ev("SFX_VEH_Siren_Yelp", "Vehicles/Sirens", lambda r, v: V.siren(r, "Yelp"), "Vehicles", loop=True, pitch=0.0, unit=25.0, maxd=500.0))
    R.append(ev("SFX_VEH_Siren_HiLo", "Vehicles/Sirens", lambda r, v: V.siren(r, "HiLo"), "Vehicles", loop=True, pitch=0.0, unit=25.0, maxd=500.0))
    R.append(ev("SFX_VEH_Helicopter_Loop", "Vehicles", lambda r, v: V.helicopter_loop(r), "Vehicles", loop=True, pitch=0.0, unit=40.0, maxd=1200.0, stereo=True))
    # ---------------------------------------------------------------- ambience (2D beds)
    R.append(ev("AMB_LA_Street_Day", "Ambience", lambda r, v: A.street_bed(r, 40.0, "LA", False), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_LA_Street_Night", "Ambience", lambda r, v: A.street_bed(r, 40.0, "LA", True), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_NY_Street_Day", "Ambience", lambda r, v: A.street_bed(r, 40.0, "NY", False), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_NY_Street_Night", "Ambience", lambda r, v: A.street_bed(r, 40.0, "NY", True), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_Rain_Light", "Ambience", lambda r, v: A.rain(r, 24.0), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_Rain_Heavy", "Ambience", lambda r, v: A.rain(r, 24.0, True), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_Wind", "Ambience", lambda r, v: A.wind(r, 24.0), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_Interior_Garage", "Ambience", lambda r, v: A.interior_garage(r, 20.0), "Ambience", loop=True, is3d=False, pitch=0.0))
    R.append(ev("AMB_OS_Car_Pass", "Ambience/OneShots", lambda r, v: A.car_pass(r), "Ambience", n=3, is3d=False, pitch=0.05, vol=-8.0))
    R.append(ev("AMB_OS_Distant_Siren", "Ambience/OneShots", lambda r, v: A.distant_siren(r), "Ambience", n=2, is3d=False, vol=-4.0))
    R.append(ev("AMB_OS_Distant_Horn", "Ambience/OneShots", lambda r, v: A.distant_horn(r), "Ambience", n=3, is3d=False, vol=-4.0))
    R.append(ev("AMB_OS_Dog_Bark", "Ambience/OneShots", lambda r, v: A.dog_bark(r), "Ambience", n=2, is3d=False, vol=-6.0))
    # ---------------------------------------------------------------- music
    R.append(ev("MUS_M01_Tension", "Music", lambda r, v: M.cue_tension(r), "Music", loop=True, is3d=False, pitch=0.0, vol=-4.0))
    R.append(ev("MUS_M01_Combat", "Music", lambda r, v: M.cue_combat(r), "Music", loop=True, is3d=False, pitch=0.0, vol=-4.0))
    R.append(ev("MUS_Menu_Theme", "Music", lambda r, v: M.cue_menu(r), "Music", loop=True, is3d=False, pitch=0.0, vol=-4.0))
    R.append(ev("MUS_Stinger_MissionPassed", "Music", lambda r, v: M.stinger_passed(r), "Music", is3d=False, pitch=0.0, vol=-2.0))
    R.append(ev("MUS_Stinger_MissionFailed", "Music", lambda r, v: M.stinger_failed(r), "Music", is3d=False, pitch=0.0, vol=-2.0))
    # ---------------------------------------------------------------- UI
    ui = [("UI_Click", M.ui_click, 2), ("UI_Hover", M.ui_hover, 1), ("UI_Back", M.ui_back, 1),
          ("UI_Objective_New", M.ui_objective_new, 1), ("UI_Objective_Complete", M.ui_objective_complete, 1),
          ("UI_Checkpoint", M.ui_checkpoint, 1), ("UI_Cash", M.ui_cash, 1), ("UI_Hitmarker", M.ui_hitmarker, 2),
          ("UI_Killmarker", M.ui_killmarker, 1), ("UI_Phone_Notify", M.ui_phone_notify, 1), ("UI_Wanted", M.ui_wanted, 1)]
    for eid, fn, n in ui:
        R.append(ev(eid, "UI", fn, "UI", n=n, is3d=False, pitch=0.0))
    R.append(ev("UI_Phone_Ring", "UI", lambda r, v: M.ui_phone_ring(r), "UI", loop=True, is3d=False, pitch=0.0))
    return R


# Gameplay -> event bindings consumed by the AudioDirector (data, not code).
BINDINGS = {
    "weapons": {
        "WPN_Pistol_01":   {"fire": "SFX_WPN_Pistol_Fire", "tail": "SFX_WPN_Pistol_Tail", "casing": True,
                            "reload": [[0.19, "SFX_WPN_MagOut_Pistol"], [0.62, "SFX_WPN_MagIn_Pistol"], [0.83, "SFX_WPN_SlideRack"]]},
        "WPN_Revolver_01": {"fire": "SFX_WPN_Revolver_Fire", "tail": "SFX_WPN_Revolver_Tail", "casing": False,
                            "reload": [[0.08, "SFX_WPN_Revolver_Cylinder"], [0.35, "SFX_WPN_ShellCasing"], [0.85, "SFX_WPN_Revolver_Cylinder"]]},
        "WPN_SMG_01":      {"fire": "SFX_WPN_SMG_Fire", "tail": "SFX_WPN_SMG_Tail", "casing": True,
                            "reload": [[0.2, "SFX_WPN_MagOut_Rifle"], [0.6, "SFX_WPN_MagIn_Rifle"], [0.85, "SFX_WPN_SlideRack"]]},
        "WPN_Shotgun_01":  {"fire": "SFX_WPN_Shotgun_Fire", "tail": "SFX_WPN_Shotgun_Tail", "casing": False, "pump_after_shot": "SFX_WPN_Shotgun_Pump",
                            "reload": [[0.12, "SFX_WPN_Shotgun_ShellLoad"], [0.3, "SFX_WPN_Shotgun_ShellLoad"], [0.48, "SFX_WPN_Shotgun_ShellLoad"],
                                       [0.66, "SFX_WPN_Shotgun_ShellLoad"], [0.88, "SFX_WPN_Shotgun_Pump"]]},
        "WPN_Rifle_01":    {"fire": "SFX_WPN_Rifle_Fire", "tail": "SFX_WPN_Rifle_Tail", "casing": True,
                            "reload": [[0.2, "SFX_WPN_MagOut_Rifle"], [0.58, "SFX_WPN_MagIn_Rifle"], [0.84, "SFX_WPN_SlideRack"]]},
        "WPN_Sniper_01":   {"fire": "SFX_WPN_Sniper_Fire", "tail": "SFX_WPN_Sniper_Tail", "casing": False, "pump_after_shot": "SFX_WPN_BoltAction",
                            "reload": [[0.1, "SFX_WPN_BoltAction"], [0.3, "SFX_WPN_MagOut_Rifle"], [0.65, "SFX_WPN_MagIn_Rifle"], [0.88, "SFX_WPN_BoltAction"]]},
        "WPN_Knife_01":    {"fire": "SFX_MEL_Swing", "hit": "SFX_MEL_Knife_Hit"},
        "WPN_Bat_01":      {"fire": "SFX_MEL_Swing_Heavy", "hit": "SFX_MEL_Bat_Hit"},
        "WPN_Grenade_01":  {"fire": "SFX_WPN_Grenade_Pin", "explode": "SFX_EXP_Grenade"},
        "WPN_Molotov_01":  {"fire": "SFX_MEL_Swing", "explode": "SFX_WPN_Molotov_Break"},
        "_default":        {"fire": "SFX_WPN_Pistol_Fire", "tail": "SFX_WPN_Pistol_Tail", "casing": True,
                            "reload": [[0.19, "SFX_WPN_MagOut_Pistol"], [0.62, "SFX_WPN_MagIn_Pistol"], [0.83, "SFX_WPN_SlideRack"]]},
    },
    "dry_fire": "SFX_WPN_DryFire",
    "casing": "SFX_WPN_ShellCasing",
    # FX scene id -> sound (every effect gets its sound automatically when it spawns)
    "fx": {
        "FX_Impact_Concrete": "SFX_IMP_Concrete", "FX_Impact_Metal": "SFX_IMP_Metal", "FX_Impact_Glass": "SFX_IMP_Glass",
        "FX_Impact_Wood": "SFX_IMP_Wood", "FX_Blood": "SFX_IMP_Flesh", "FX_Impact_Dirt": "SFX_IMP_Dirt",
        "FX_Impact_Water": "SFX_IMP_Water", "FX_Explosion": "SFX_EXP_Large", "FX_Explosion_Vehicle": "SFX_EXP_Vehicle",
        "FX_Explosion_Grenade": "SFX_EXP_Grenade", "FX_GlassShatter": "SFX_GLASS_Shatter_Large",
        "FX_Fire": "SFX_FIRE_Loop", "FX_Fire_Vehicle": "SFX_FIRE_Loop_Large", "FX_Steam_NY": "SFX_STEAM_Loop",
        "FX_Sparks": "SFX_SPARKS_Loop", "FX_Molotov": "SFX_WPN_Molotov_Break",
    },
    "ricochet_chance": 0.18,
    "footsteps": {
        "default_surface": "Concrete",
        "groups": {"surface_metal": "Metal", "surface_wood": "Wood", "surface_glass": "Concrete", "surface_grass": "Grass",
                   "surface_gravel": "Gravel", "surface_water": "Water", "surface_asphalt": "Asphalt", "surface_dirt": "Gravel"},
        "stride_walk_m": 0.72, "stride_run_m": 1.15, "run_speed_mps": 2.6,
    },
    "vehicles": {
        "engine_sets": {"VH_Sedan_01": "Sedan", "VH_Police_01": "Sedan", "VH_Taxi_NY_01": "Sedan", "VH_Muscle_01": "Muscle",
                        "VH_Pickup_01": "Truck", "VH_Van_01": "Truck", "VH_Motorcycle_01": "Moto", "VH_Plane_Small_01": "Prop",
                        "_default": "Sedan"},
        "siren": {"VH_Police_01": "SFX_VEH_Siren_Wail"},
        "crash_heavy_mps": 9.0, "crash_light_mps": 3.0,
        # RPM each engine layer was rendered at -> playback pitch = current rpm / layer rpm
        "layer_rpm": dict({k: {l: float(r) for l, r in e["rpm"].items()} for k, e in V.ENGINES.items()},
                          Prop={l: float(r) for l, r in V.PROP_RPM.items()}),
    },
    "ambience": {"LA": "AMB_LA_Street_Day", "LA_night": "AMB_LA_Street_Night", "NY": "AMB_NY_Street_Day",
                 "NY_night": "AMB_NY_Street_Night", "rain": "AMB_Rain_Light", "interior": "AMB_Interior_Garage",
                 "oneshots": ["AMB_OS_Car_Pass", "AMB_OS_Distant_Horn", "AMB_OS_Distant_Siren", "AMB_OS_Dog_Bark"],
                 "oneshot_interval_s": [9.0, 26.0]},
    "music": {"explore": "MUS_M01_Tension", "combat": "MUS_M01_Combat", "menu": "MUS_Menu_Theme",
              "passed": "MUS_Stinger_MissionPassed", "failed": "MUS_Stinger_MissionFailed",
              "combat_hold_s": 9.0, "crossfade_s": 2.5},
    "ui": {"objective_new": "UI_Objective_New", "objective_complete": "UI_Objective_Complete", "checkpoint": "UI_Checkpoint",
           "cash": "UI_Cash", "hitmarker": "UI_Hitmarker", "killmarker": "UI_Killmarker", "phone_ring": "UI_Phone_Ring",
           "phone_notify": "UI_Phone_Notify", "click": "UI_Click", "hover": "UI_Hover", "back": "UI_Back"},
    "character": {"jump": "SFX_FOL_Jump", "land": "SFX_FOL_Land", "land_heavy": "SFX_FOL_Land_Heavy", "land_heavy_mps": 7.0,
                  "body_fall": "SFX_FOL_BodyFall", "pickup": "SFX_FOL_Pickup_Item"},
}


def rel_path(e, v):
    name = e["id"] if e["n"] == 1 else f"{e['id']}_{v + 1:02d}"
    return f"{AUDIO_ROOT}/{e['folder']}/{name}.ogg"


def seed_for(eid, v):
    return (zlib.crc32(eid.encode()) + 7919 * v) & 0xFFFFFFFF


def write_ogg(path, data, ceiling_db=-0.8):
    """Encode Ogg Vorbis and verify the *decoded* peak: lossy coding overshoots on dense transients
    (fire crackle: +3.7 dB), so re-scale and re-encode until the decoded file is below the ceiling."""
    import soundfile as sf
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.clip(data, -1.0, 1.0)
    for _ in range(4):
        sf.write(path, x.astype(np.float32), D.SR, format="OGG", subtype="VORBIS")
        y, _sr = sf.read(path, always_2d=False)
        pk = D.peak_dbfs(y)
        if pk <= ceiling_db + 0.05:
            break
        x = x * 10 ** ((ceiling_db - 0.3 - pk) / 20.0)
    return x


def spectrogram_png(path, data, title):
    from PIL import Image, ImageDraw
    x = data.mean(axis=1) if data.ndim == 2 else data
    nfft, hop = 1024, 256
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    frames = 1 + (len(x) - nfft) // hop
    win = np.hanning(nfft)
    S = np.array([np.abs(np.fft.rfft(x[i * hop:i * hop + nfft] * win)) for i in range(frames)]).T
    S = 20 * np.log10(S + 1e-9)
    S = np.clip((S - (S.max() - 80.0)) / 80.0, 0, 1)  # 80 dB window below the loudest bin
    # log-frequency rows
    rows = 256
    f = np.fft.rfftfreq(nfft, 1 / D.SR)
    targets = np.geomspace(30, 20000, rows)
    idx = np.searchsorted(f, targets).clip(0, len(f) - 1)
    img = (S[idx][::-1] * 255).astype(np.uint8)
    w = min(frames, 1200)
    im = Image.fromarray(img).resize((w, rows))
    # "inferno"-like ramp: black -> purple -> orange -> pale yellow
    lut_r = [int(255 * min(1.0, 1.6 * (i / 255) ** 0.8)) for i in range(256)]
    lut_g = [int(255 * max(0.0, (i / 255 - 0.35) / 0.65) ** 1.2) for i in range(256)]
    lut_b = [int(255 * (0.5 * math.sin(math.pi * min(1.0, i / 170)) + max(0.0, (i / 255 - 0.85) * 3))) for i in range(256)]
    rgb = Image.merge("RGB", (im.point(lut_r), im.point(lut_g), im.point(lut_b)))
    canvas = Image.new("RGB", (w, rows + 70), (12, 12, 16))
    canvas.paste(rgb, (0, 70))
    dr = ImageDraw.Draw(canvas)
    dr.text((6, 4), title, fill=(230, 230, 230))
    env = np.abs(x)
    step = max(1, len(env) // w)
    env = env[:step * w].reshape(w, -1).max(axis=1) if len(env) >= w else env
    for i, e in enumerate(env[:w]):
        h = int(e * 44)
        dr.line([(i, 48 - h), (i, 48 + h)], fill=(120, 200, 255))
    canvas.save(path)


def render(event, v):
    rng = np.random.default_rng(seed_for(event["id"], v))
    x = event["fn"](rng, v)
    x = np.asarray(x, dtype=np.float64)
    if event["stereo"] and x.ndim == 1:
        x = D.to_stereo(x, 0.4)
    if not event["stereo"] and x.ndim == 2:
        x = x.mean(axis=1)
    if not np.all(np.isfinite(x)):
        raise RuntimeError(f"{event['id']}_{v}: non-finite samples")
    # DC: loops get their mean removed (keeps the seam), one-shots a 15 Hz high-pass
    if event["loop"]:
        x = x - x.mean(axis=0)
    else:
        x = D.hp(x, 15.0)
    # safety: nothing renders hotter than -1 dBFS (write_ogg also checks the decoded peak)
    if D.peak_dbfs(x) > -1.0:
        x = D.normalize(x, -1.0)
    return x


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--only", default="*", help="fnmatch pattern on event ids")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--spectrograms", default="", help="also write spectrogram PNGs into this dir (review)")
    ap.add_argument("--table-only", action="store_true", help="only rewrite the runtime table (no rendering)")
    a = ap.parse_args(argv)
    reg = build_registry()
    ids = [e["id"] for e in reg]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit(f"duplicate event ids: {sorted(dup)}")
    if a.list:
        for e in reg:
            print(f"{e['id']:36s} {e['bus']:9s} n={e['n']} loop={e['loop']} 3d={e['is3d']}")
        print(f"{len(reg)} events, {sum(e['n'] for e in reg)} files")
        return 0
    root = os.path.join(a.repo, AUDIO_ROOT)
    man_path = os.path.join(root, "audio.manifest.json")
    manifest = {"files": {}}
    if os.path.isfile(man_path):
        with open(man_path) as fh:
            manifest = json.load(fh)
    t0 = time.time()
    done = 0
    if not a.table_only:
        for e in reg:
            if not fnmatch.fnmatch(e["id"], a.only):
                continue
            for v in range(e["n"]):
                rel = rel_path(e, v)
                name = os.path.basename(rel)[:-4]
                x = render(e, v)
                x = write_ogg(os.path.join(a.repo, rel), x)
                with open(os.path.join(a.repo, rel), "rb") as fh:
                    sha = hashlib.sha256(fh.read()).hexdigest()
                if a.spectrograms:
                    os.makedirs(a.spectrograms, exist_ok=True)
                    spectrogram_png(os.path.join(a.spectrograms, name + ".png"), x, f"{name}  {len(x) / D.SR:.2f}s")
                manifest["files"][rel] = {
                    "event": e["id"], "variation": v, "sha256": sha, "seed": seed_for(e["id"], v), "duration_s": round(len(x) / D.SR, 4),
                    "channels": 2 if x.ndim == 2 else 1, "sample_rate": D.SR, "loop": e["loop"],
                    "peak_dbfs": round(D.peak_dbfs(x), 2), "rms_dbfs": round(D.rms_db(x), 2),
                }
                done += 1
                print(f"[AUDIO] {rel:70s} {len(x) / D.SR:6.2f}s peak {D.peak_dbfs(x):6.1f} dBFS", flush=True)
    # prune entries whose files vanished
    manifest["files"] = {k: v for k, v in manifest["files"].items() if os.path.isfile(os.path.join(a.repo, k))}
    manifest.update({"asset": "Audio library", "generator": "Tools/uwp build-audio (underworld_pipeline/audio)",
                     "license": "Project-original (procedurally synthesized, no third-party samples)",
                     "sample_rate": D.SR, "format": "Ogg Vorbis"})
    os.makedirs(root, exist_ok=True)
    with open(man_path, "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    # runtime table - derived from the registry only (never from render results), so it is
    # byte-identical on every machine and a CI re-render does not touch the tracked file.
    events = {}
    for e in reg:
        files = [rel_path(e, v) for v in range(e["n"])]
        events[e["id"]] = {
            "files": ["res://" + f for f in files], "bus": e["bus"], "loop": e["loop"], "positional": e["is3d"],
            "volume_db": e["volume_db"], "pitch_jitter": e["pitch_jitter"], "unit_size": e["unit_size"],
            "max_distance": e["max_distance"],
        }
    table = {"_doc": "GENERATED by Tools/uwp build-audio - do not edit by hand. Event table for "
                     "Scripts/audio/audio_director.gd (T-AUD-01). Bindings map gameplay signals to events.",
             "version": 1, "buses": BUSES, "events": events, "bindings": BINDINGS}
    tpath = os.path.join(a.repo, RUNTIME_TABLE)
    os.makedirs(os.path.dirname(tpath), exist_ok=True)
    with open(tpath, "w") as fh:
        json.dump(table, fh, indent=1, sort_keys=True)
        fh.write("\n")
    missing = [f for e in events.values() for f in e["files"] if not os.path.isfile(os.path.join(a.repo, f[6:]))]
    print(f"[AUDIO] rendered {done} files in {time.time() - t0:.1f}s; table {RUNTIME_TABLE}: "
          f"{len(events)} events, {sum(len(e['files']) for e in events.values())} files, {len(missing)} not on disk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
