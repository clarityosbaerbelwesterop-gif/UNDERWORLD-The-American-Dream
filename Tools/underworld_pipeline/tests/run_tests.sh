#!/usr/bin/env bash
# T-PIPE-01 end-to-end test for Tools/underworld_pipeline (owner Bot 2).
#   Tools/underworld_pipeline/tests/run_tests.sh [--no-godot]
# 1. builds test assets procedurally (bpy)        5. Blender re-import check (verify_glb.py)
# 2. runs the exporter (good assets -> exit 0)     6. Godot headless import in a throw-away project
# 3. runs it on a broken asset (-> exit 1 + codes)    (+ LOD post-import script) and node/anim checks
# 4. option/exit-code checks, JSON report checks   7. validate-all / export-all on Blender/Source
# Everything is written to $UWP_TEST_DIR (default /tmp/uwp_test); the repo is not modified.
# Exit 0 + "UWP TESTS: PASS" on success.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
# shellcheck source=/dev/null
. "$REPO/Tests/lib/godot_errors.sh"
UWP="$REPO/Tools/uwp"
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
GODOT="${GODOT:-/workspace/tools/godot}"
T="${UWP_TEST_DIR:-/tmp/uwp_test}"
NO_GODOT=0; [ "${1:-}" = "--no-godot" ] && NO_GODOT=1
FAILS=0
ok()   { echo "[TEST][PASS] $*"; }
bad()  { echo "[TEST][FAIL] $*"; FAILS=$((FAILS+1)); }
expect_rc() { # name expected actual log
  if [ "$3" -eq "$2" ]; then ok "$1 -> exit $3"; else bad "$1 -> exit $3 (expected $2), log $4"; grep -E '^\[UWP\]|Traceback|Error' "$4" | tail -20; fi; }
run_uwp() { local log="$1"; shift; "$UWP" "$@" > "$log" 2>&1; echo $?; }

rm -rf "$T"; mkdir -p "$T/src" "$T/out" "$T/logs"
echo "== [1] build test assets"
"$BLENDER" -b --factory-startup --python-exit-code 1 --python "$HERE/make_test_assets.py" -- --out-dir "$T/src" > "$T/logs/make.log" 2>&1
expect_rc "make_test_assets.py" 0 $? "$T/logs/make.log"

echo "== [2] export good assets"
rc=$(run_uwp "$T/logs/barrel.log" export "$T/src/PT_UWP_Barrel.blend" --category Props --out "$T/out/PT_UWP_Barrel/PT_UWP_Barrel.glb")
expect_rc "export PT_UWP_Barrel (Props: LODs + convex collision + preview)" 0 "$rc" "$T/logs/barrel.log"
rc=$(run_uwp "$T/logs/rig.log" export "$T/src/PT_UWP_RigTest.blend" --category Test --out "$T/out/PT_UWP_RigTest/PT_UWP_RigTest.glb")
expect_rc "export PT_UWP_RigTest (skinned + 2 actions)" 0 "$rc" "$T/logs/rig.log"
rc=$(run_uwp "$T/logs/barrel_nolod.log" export "$T/src/PT_UWP_Barrel.blend" --category Props --no-lod --no-collision --no-preview --out "$T/out/nolod/PT_UWP_Barrel.glb")
expect_rc "export --no-lod --no-collision --no-preview" 0 "$rc" "$T/logs/barrel_nolod.log"
rc=$(run_uwp "$T/logs/barrel_box.log" export "$T/src/PT_UWP_Barrel.blend" --category Props --collision box --lod-ratios 0.3 --no-preview --out "$T/out/box/PT_UWP_Barrel.glb")
expect_rc "export --collision box --lod-ratios 0.3" 0 "$rc" "$T/logs/barrel_box.log"
rc=$(run_uwp "$T/logs/barrel_tri.log" export "$T/src/PT_UWP_Barrel.blend" --category Props --collision trimesh --no-preview --out "$T/out/tri/PT_UWP_Barrel.glb")
expect_rc "export --collision trimesh" 0 "$rc" "$T/logs/barrel_tri.log"

echo "== [3] negative cases"
rc=$(run_uwp "$T/logs/broken.log" export "$T/src/PT_UWP_Broken.blend" --category Props --out "$T/out/PT_UWP_Broken/PT_UWP_Broken.glb")
expect_rc "export PT_UWP_Broken (must fail validation)" 1 "$rc" "$T/logs/broken.log"
[ ! -f "$T/out/PT_UWP_Broken/PT_UWP_Broken.glb" ] && ok "no .glb written for failed asset" || bad "broken asset was exported"
rc=$(run_uwp "$T/logs/humanoid.log" validate "$T/src/PT_UWP_RigTest.blend" --category Characters --budget-key Test --report "$T/out/humanoid.json")
expect_rc "validate RigTest as Characters (non-humanoid bones)" 1 "$rc" "$T/logs/humanoid.log"
rc=$(run_uwp "$T/logs/hum_ok.log" export "$T/src/PT_UWP_Humanoid.blend" --category Characters --budget-key Test --no-preview --out "$T/out/PT_UWP_Humanoid/PT_UWP_Humanoid.glb")
expect_rc "export PT_UWP_Humanoid (Characters, humanoid bones, faces -Y)" 0 "$rc" "$T/logs/hum_ok.log"
rc=$(run_uwp "$T/logs/hum_back.log" validate "$T/src/PT_UWP_HumanoidBack.blend" --category Characters --budget-key Test --report "$T/out/hum_back.json")
expect_rc "validate PT_UWP_HumanoidBack (faces +Y, must fail FRONT_AXIS)" 1 "$rc" "$T/logs/hum_back.log"
rc=$(run_uwp "$T/logs/strict.log" validate "$REPO/Blender/Source/Test/PT_PipelineTest_Crate.blend" --strict --report "$T/out/strict.json")
expect_rc "validate --strict (warnings become errors)" 1 "$rc" "$T/logs/strict.log"
rc=$(run_uwp "$T/logs/missing.log" export "$T/src/Nope.blend" --category Props --out "$T/out/x.glb")
expect_rc "missing input file" 4 "$rc" "$T/logs/missing.log"
rc=$(run_uwp "$T/logs/nocat.log" validate "$T/src/PT_UWP_Barrel.blend" --report "$T/out/nocat.json")
expect_rc "no category outside Blender/Source" 4 "$rc" "$T/logs/nocat.log"
rc=$(run_uwp "$T/logs/badarg.log" export)
expect_rc "bad CLI args" 4 "$rc" "$T/logs/badarg.log"

echo "== [4] JSON report / manifest checks"
python3 - "$T" <<'PY'
import json, os, sys
T = sys.argv[1]; fails = 0
def check(c, m):
    global fails
    print(("[TEST][PASS] " if c else "[TEST][FAIL] ") + m); fails += 0 if c else 1
J = lambda p: json.load(open(os.path.join(T, p)))
b = J("out/PT_UWP_Barrel/PT_UWP_Barrel.validation.json")
check(b["result"] == "PASS" and b["exit_code"] == 0, "barrel report result PASS / exit_code 0")
m = J("out/PT_UWP_Barrel/PT_UWP_Barrel.manifest.json")
check(m["triangles"]["lod0"] <= m["triangles"]["budget"] == 5000, f"barrel LOD0 tris {m['triangles']['lod0']} <= Props budget")
t = m["triangles"]["per_lod_total"]
check(t["LOD0"] > t["LOD1"] > t["LOD2"] > 0, f"barrel LOD tri totals decrease {t}")
check(abs(m["aabb_godot"]["min"][1]) < 0.01 and abs(m["aabb_godot"]["size"][1] - 0.94) < 0.01, f"barrel Godot AABB {m['aabb_godot']}")
check([c["name"] for c in m["collision"]["generated"]] == ["UCX_PT_UWP_Barrel-convcolonly"], "barrel convex collision generated")
check(m["textures"] and m["textures"][0]["size"] == [256, 256] and m["textures"][0]["packed"], "barrel texture recorded (256², packed)")
check("SM_PT_UWP_Barrel_Body" in m.get("texel_density", {}), "barrel texel density recorded in manifest")
check("SM_PT_UWP_Barrel_Body" in m.get("uv_overlap", {}) and m["uv_overlap"]["SM_PT_UWP_Barrel_Body"]["overlap_fraction"] < 0.05, "barrel UV overlap < 5%")
check("SOCKET_Top" in m["sockets"], "barrel socket recorded")
check(os.path.getsize(os.path.join(T, "out/PT_UWP_Barrel/PT_UWP_Barrel_preview.png")) > 5000, "barrel preview PNG rendered")
r = J("out/PT_UWP_RigTest/PT_UWP_RigTest.manifest.json")
an = {a["name"]: a for a in r["animations"]}
check(set(an) == {"A_PT_UWP_RigTest_Bend", "A_PT_UWP_RigTest_Twist"}, f"rig animations {sorted(an)}")
check(an["A_PT_UWP_RigTest_Bend"]["loop"] and not an["A_PT_UWP_RigTest_Twist"]["loop"], "rig loop flags (Bend cyclic, Twist not)")
check(r["armatures"]["Armature"]["bones"] == ["Base", "Mid", "Tip"], "rig bones in manifest")
check(r["sockets"]["SOCKET_Tip"]["parent_bone"] == "Tip", "bone socket recorded")
rv = J("out/PT_UWP_RigTest/PT_UWP_RigTest.validation.json")
check(rv["steps"]["verify"]["glb"]["skins"][0]["joints"] == 3, "rig glb has a 3-joint skin")
br = J("out/PT_UWP_Broken/PT_UWP_Broken.validation.json")
codes = {i["code"] for i in br["issues"] if i["severity"] == "error"}
want = {"ROOT_MISSING", "NAME_OBJECT", "TRANSFORM_SCALE", "NO_UVS", "NO_MATERIAL", "LOOSE_GEOMETRY", "TRI_BUDGET",
        "ORIGIN_GROUND", "NAME_MATERIAL", "TEXTURE_SIZE", "BONE_INFLUENCES", "WEIGHT_UNNORMALIZED", "UV_OVERLAP",
        "NAME_ACTION", "NAME_ACTION_LOOP"}
check(want <= codes, f"broken report error codes ⊇ expected (missing: {sorted(want - codes)})")
check(br["result"] == "VALIDATION_FAILED" and br["exit_code"] == 1, "broken report result VALIDATION_FAILED / 1")
h = J("out/humanoid.json")
check(any(i["code"] == "HUMANOID_BONES" for i in h["issues"]), "Characters validation reports HUMANOID_BONES")
hb = J("out/hum_back.json")
check({i["code"] for i in hb["issues"] if i["severity"] == "error"} == {"FRONT_AXIS"}, "backwards humanoid fails only with FRONT_AXIS")
hm = J("out/PT_UWP_Humanoid/PT_UWP_Humanoid.manifest.json")
check(len(hm["armatures"]["Armature"]["bones"]) == 22 and hm["collision"]["mode"] == "none", "humanoid: 22 profile bones, no collision for Characters")
s = J("out/strict.json")
check(s["exit_code"] == 1 and any(i["code"] == "ORIGIN_CENTRE" and i["severity"] == "error" for i in s["issues"]), "--strict promoted ORIGIN_CENTRE warning to error")
n = J("out/nolod/PT_UWP_Barrel.manifest.json")
check(n["lods"] == "skipped (--no-lod)" or n["lods"] == [] or not any("_LOD" in x for x in n["nodes"]), "--no-lod: no LOD nodes")
check(not any(x.startswith("UCX_") for x in n["nodes"]), "--no-collision: no UCX nodes")
bx = J("out/box/PT_UWP_Barrel.manifest.json")
check(bx["collision"]["generated"][0]["vertices"] == 8 and "LOD1" in bx["triangles"]["per_lod_total"] and "LOD2" not in bx["triangles"]["per_lod_total"], "--collision box (8 verts) + single LOD ratio")
tr = J("out/tri/PT_UWP_Barrel.manifest.json")
check(all(c["name"].endswith("-colonly") for c in tr["collision"]["generated"]) and len(tr["collision"]["generated"]) == 2, "--collision trimesh: one -colonly per mesh")
sys.exit(1 if fails else 0)
PY
[ $? -eq 0 ] || FAILS=$((FAILS+1))

echo "== [4b] pure-numpy unit checks (no Blender)"
# procedural_assets.py needs numpy only (no bpy). The system python3 here has no numpy, the
# Blender-bundled interpreter does, so prefer that one.
NUMPY_PY="${NUMPY_PY:-}"
if [ -z "$NUMPY_PY" ]; then
  for c in /workspace/tools/blender/*/python/bin/python3* /usr/local/venv/bin/python python3; do
    [ -x "$c" ] || continue
    "$c" -c "import numpy" 2>/dev/null && { NUMPY_PY="$c"; break; }
  done
fi
[ -n "$NUMPY_PY" ] || { bad "no python with numpy found for unit checks"; NUMPY_PY=python3; }
"$NUMPY_PY" - "$REPO" <<'PYUNIT'
import os, sys, numpy as np
repo = sys.argv[1]
here = os.path.join(repo, "Tools", "underworld_pipeline", "characters")
sys.path.insert(0, os.path.join(repo, "Tools", "underworld_pipeline"))
sys.path.insert(0, here)
import importlib.util
spec = importlib.util.spec_from_file_location("proc", os.path.join(here, "procedural_assets.py"))
proc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proc)

fails = 0
def check(cond, what):
    global fails
    print(("[TEST][PASS] " if cond else "[TEST][FAIL] ") + what)
    if not cond:
        fails += 1

# Skin-space lip mask (SK_NPC_Sam landmarks, metres). Regression: np.clip(t, 0, 1) saturates at 1,
# so a clipped parameter turned every point above the lip into a full-strength mask and the whole
# face was painted in lip colour.
MZ, UP, LO = 1.6552, 1.6662, 1.6477
m = lambda x, z: float(proc.lip_mask(np.array([x]), np.array([z]), MZ, UP, LO)[0])
check(0.95 <= m(0.008, MZ) <= 1.0, "lip_mask: full strength at the opening")
check(m(0.008, UP + 0.002) == 0.0, "lip_mask: zero above the upper vermilion border")
check(m(0.008, LO - 0.002) == 0.0, "lip_mask: zero below the lower vermilion border")
check(m(0.0, 1.69) == 0.0 and m(0.0, 1.61) == 0.0, "lip_mask: zero on forehead and chin")
# cos(pi/2) is 6e-17, not exactly 0, so "outside" needs a tolerance - a real value there
# would be >= 0.1, not 1e-9.
check(m(0.05, MZ) <= 1e-6 and m(0.05, 1.6600) <= 1e-6, "lip_mask: zero outside the mouth width")
check(0.0 < m(0.008, (MZ + UP) * 0.5) < 1.0, "lip_mask: partial on the upper lip body")
Z, X = np.meshgrid(np.linspace(1.60, 1.71, 300), np.linspace(-0.06, 0.06, 300), indexing="ij")
grid = proc.lip_mask(X, Z, MZ, UP, LO)
check(not np.isnan(grid).any(), "lip_mask: NaN-free over the whole face box")
# Texture-resolution float32 regression: cos(pi/2 * 1.0) is -1e-17 in float32, and a negative base
# to a fractional power is NaN - which silently turned ~90 % of the skin maps black.
Zf, Xf = np.meshgrid(np.linspace(1.60, 1.71, 1024, dtype=np.float32),
                     np.linspace(-0.06, 0.06, 1024, dtype=np.float32), indexing="ij")
gf = proc.lip_mask(Xf, Zf, np.float32(MZ), np.float32(UP), np.float32(LO))
check(int(np.isnan(gf).sum()) == 0, "lip_mask: NaN-free in float32 at texture resolution")
check(0.01 < float((gf > 0.05).mean()) < 0.12, "lip_mask: float32 coverage unchanged (2-12%)")
check(0.01 < float((grid > 0.05).mean()) < 0.12, "lip_mask: covers the lips only (2-12% of the face box)")
sys.exit(1 if fails else 0)
PYUNIT
[ $? -eq 0 ] || FAILS=$((FAILS+1))

echo "== [5] Blender re-import verification"
cat > "$T/expect_blender.json" <<JSON
{"assets": [
 {"glb": "$T/out/PT_UWP_Barrel/PT_UWP_Barrel.glb",
  "objects": ["PT_UWP_Barrel", "SM_PT_UWP_Barrel_Body", "SM_PT_UWP_Barrel_Lid", "SOCKET_Top", "UCX_PT_UWP_Barrel-convcolonly"],
  "lod_children": {"SM_PT_UWP_Barrel_Body": ["SM_PT_UWP_Barrel_Body_LOD1", "SM_PT_UWP_Barrel_Body_LOD2"],
                   "SM_PT_UWP_Barrel_Lid": ["SM_PT_UWP_Barrel_Lid_LOD1", "SM_PT_UWP_Barrel_Lid_LOD2"]}},
 {"glb": "$T/out/nolod/PT_UWP_Barrel.glb", "objects": ["SM_PT_UWP_Barrel_Body"],
  "absent": ["SM_PT_UWP_Barrel_Body_LOD1", "UCX_PT_UWP_Barrel-convcolonly"]},
 {"glb": "$T/out/PT_UWP_RigTest/PT_UWP_RigTest.glb",
  "objects": ["PT_UWP_RigTest", "Armature", "SK_PT_UWP_RigTest_Tube", "SOCKET_Tip", "UCX_PT_UWP_RigTest-convcolonly"],
  "armature_bones": ["Base", "Mid", "Tip"], "actions": ["A_PT_UWP_RigTest_Bend", "A_PT_UWP_RigTest_Twist"],
  "animated_bone": ["A_PT_UWP_RigTest_Bend", "Tip", 16]}
]}
JSON
"$BLENDER" -b --factory-startup --python-exit-code 1 --python "$HERE/verify_glb.py" -- --expect "$T/expect_blender.json" > "$T/logs/verify_blender.log" 2>&1
rc=$?; grep -E '^\[VERIFY\]' "$T/logs/verify_blender.log"
expect_rc "verify_glb.py" 0 $rc "$T/logs/verify_blender.log"

echo "== [7] validate-all / export-all on Blender/Source"
rc=$(run_uwp "$T/logs/validate_all.log" validate-all --report "$T/out/validate_all.json")
expect_rc "validate-all (repo Blender/Source)" 0 "$rc" "$T/logs/validate_all.log"
rc=$(run_uwp "$T/logs/export_all.log" export-all --no-preview --out-root "$T/out/all" --report "$T/out/export_all.json")
expect_rc "export-all --no-preview --out-root (repo Blender/Source)" 0 "$rc" "$T/logs/export_all.log"
grep -E '^\[UWP\] (Blender|skip|RESULT)' "$T/logs/validate_all.log" "$T/logs/export_all.log"

if [ $NO_GODOT -eq 0 ] && [ -x "$GODOT" ]; then
  echo "== [6] Godot headless import (throw-away project $T/godot)"
  G="$T/godot"; mkdir -p "$G/assets"
  printf 'config_version=5\n\n[application]\n\nconfig/name="uwp_test"\n' > "$G/project.godot"
  cp "$REPO/Tools/underworld_pipeline/godot/uw_lod_post_import.gd" "$HERE/godot_verify.gd" "$G/"
  cp "$T/out/PT_UWP_Barrel/PT_UWP_Barrel.glb" "$T/out/PT_UWP_RigTest/PT_UWP_RigTest.glb" "$G/assets/"
  cp "$T/out/all/Test/PT_PipelineTest_Crate.glb" "$T/out/PT_UWP_Humanoid/PT_UWP_Humanoid.glb" "$G/assets/"
  # pre-seed .import files so the very first import runs the LOD post-import script
  for f in "$G"/assets/*.glb; do
    printf '[remap]\n\nimporter="scene"\ntype="PackedScene"\n\n[params]\n\nimport_script/path="res://uw_lod_post_import.gd"\n' > "$f.import"
  done
  "$GODOT" --headless --path "$G" --import > "$T/logs/godot_import1.log" 2>&1
  rc=$?
  n=$(grep -c '^\[UWP-GODOT\]' "$T/logs/godot_import1.log")
  [ "$n" -eq 4 ] && ok "LOD post-import script ran for 4 .glb files" || bad "LOD post-import script ran $n times (expected 4)"
  grep -E '^\[UWP-GODOT\]' "$T/logs/godot_import1.log"
  ierrs="$(godot_log_errors "$T/logs/godot_import1.log")"
  if [ $rc -ne 0 ] || [ -n "$ierrs" ]; then
    bad "Godot import (rc=$rc)"; echo "$ierrs" | head -20
  else ok "Godot import, no errors"; fi
  cat > "$G/expect.json" <<'JSON'
{"assets": [
 {"path": "res://assets/PT_UWP_Barrel.glb",
  "nodes": {"SM_PT_UWP_Barrel_Body": "MeshInstance3D", "SM_PT_UWP_Barrel_Body_LOD1": "MeshInstance3D", "SM_PT_UWP_Barrel_Body_LOD2": "MeshInstance3D",
            "SM_PT_UWP_Barrel_Lid": "MeshInstance3D", "SM_PT_UWP_Barrel_Lid_LOD2": "MeshInstance3D", "SOCKET_Top": "Node3D"},
  "lod_ranges": {"SM_PT_UWP_Barrel_Body": [0, 15], "SM_PT_UWP_Barrel_Body_LOD1": [15, 40], "SM_PT_UWP_Barrel_Body_LOD2": [40, 100]},
  "collision": {"UCX_PT_UWP_Barrel": "ConvexPolygonShape3D"}, "aabb_min_y": 0.0},
 {"path": "res://assets/PT_UWP_RigTest.glb",
  "nodes": {"Skeleton3D": "Skeleton3D", "SK_PT_UWP_RigTest_Tube": "MeshInstance3D", "SOCKET_Tip": "Node3D"},
  "collision": {"UCX_PT_UWP_RigTest": "ConvexPolygonShape3D"}, "bones": ["Base", "Mid", "Tip"],
  "animations": {"A_PT_UWP_RigTest_Bend": 1.0, "A_PT_UWP_RigTest_Twist": 0.5},
  "animate": ["A_PT_UWP_RigTest_Bend", "Mid", 0.5], "aabb_min_y": 0.0},
 {"path": "res://assets/PT_PipelineTest_Crate.glb",
  "nodes": {"SM_PT_PipelineTest_Crate_Body": "MeshInstance3D", "SM_PT_PipelineTest_Crate_Body_LOD1": "MeshInstance3D"},
  "lod_ranges": {"SM_PT_PipelineTest_Crate_Body_LOD2": [50, 150]},
  "collision": {"UCX_PT_PipelineTest_Crate": "ConcavePolygonShape3D"}, "aabb_min_y": 0.0},
 {"path": "res://assets/PT_UWP_Humanoid.glb", "nodes": {"Skeleton3D": "Skeleton3D"},
  "front_bone": "LeftToes", "left_bone": "LeftHand", "bone_count": 22, "aabb_min_y": 0.0}
]}
JSON
  "$GODOT" --headless --path "$G" --script res://godot_verify.gd -- "$G/expect.json" > "$T/logs/godot_verify.log" 2>&1
  rc=$?; grep -E '^\[GODOT\]' "$T/logs/godot_verify.log"
  expect_rc "godot_verify.gd" 0 $rc "$T/logs/godot_verify.log"
  if grep -qE '^(SCRIPT ERROR|USER ERROR):' "$T/logs/godot_verify.log"; then bad "Godot verify script errors"; grep -E -A3 '^(SCRIPT ERROR|USER ERROR):' "$T/logs/godot_verify.log"; fi
else
  echo "== [6] Godot check skipped"
fi

echo "== [7] review-sheet (system Python / Pillow, no Blender)"
T="$T" python3 -c "
from PIL import Image, ImageDraw
import os
t = os.environ['T']
def mk(path, color, text):
    im = Image.new('RGB', (200, 160), color)
    ImageDraw.Draw(im).text((10, 70), text, fill=(255, 255, 255))
    im.save(path)
mk(t + '/ref_sheet.png', (20, 80, 160), 'REF')
mk(t + '/ren_a.png', (160, 40, 40), 'REN-A')
mk(t + '/ren_b.png', (40, 140, 60), 'REN-B')
"
"$REPO/Tools/uwp" review-sheet PT_UWP_Sheet \
  --ref "$T/ref_sheet.png" \
  --renders "$T/ren_a.png" "$T/ren_b.png" \
  --out "$T/out/review_sheet.png" \
  --title PT_UWP_Sheet > "$T/logs/review_sheet.log" 2>&1
rc=$?
expect_rc "uwp review-sheet PT_UWP_Sheet" 0 "$rc" "$T/logs/review_sheet.log"
if [ -f "$T/out/review_sheet.png" ]; then ok "review-sheet PNG written"; else bad "review-sheet PNG missing"; fi

echo "logs: $T/logs"
if [ $FAILS -eq 0 ]; then echo "UWP TESTS: PASS"; exit 0; else echo "UWP TESTS: FAIL ($FAILS)"; exit 1; fi
