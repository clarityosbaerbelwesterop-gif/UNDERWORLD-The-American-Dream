#!/usr/bin/env bash
# WPN_Pistol_01 delivery verification (Bot 2, T-ART-05 / REQ-GP02-PISTOL):
#  1. Tools/uwp validate on the .blend (must PASS)
#  2. Blender re-import of the .glb (nodes, sockets, actions, frame ranges, PBR maps)  [verify_wpn_pistol_01_blender.py]
#  3. Godot headless, in a throw-away COPY of GodotProject (repo untouched):
#     a) verify_wpn_pistol_01_godot.gd (nodes, sockets/axes, size, LODs, collision, PBR material, animations)
#     b) REQ §4: Data/Weapons/WPN_Pistol_01.tres scene -> WPN_Pistol_01.glb, then Bot 3's Tests/test_weapon.gd must stay green
# Exit 0 + "WPN_PISTOL_01 VERIFY: PASS" on success.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
BLENDER="${BLENDER:-/workspace/tools/blender/blender}"
GODOT="${GODOT:-/workspace/tools/godot}"
A="$REPO/Assets/Weapons/WPN_Pistol_01"
T="$(mktemp -d /tmp/wpn_pistol_verify.XXXXXX)"
FAILS=0
step() { if [ "$1" -eq 0 ]; then echo "[PISTOL][PASS] $2"; else echo "[PISTOL][FAIL] $2 (rc=$1, log $3)"; FAILS=$((FAILS+1)); fi; }
strip() { sed 's/\x1b\[[0-9;]*m//g'; }

"$REPO/Tools/uwp" validate "$REPO/Blender/Source/Weapons/WPN_Pistol_01/WPN_Pistol_01.blend" > "$T/validate.log" 2>&1
step $? "uwp validate WPN_Pistol_01.blend" "$T/validate.log"; grep -E '^\[UWP\]\[(ERROR|WARN)\]|RESULT' "$T/validate.log"

"$BLENDER" -b --factory-startup --python "$HERE/verify_wpn_pistol_01_blender.py" -- "$A/WPN_Pistol_01.glb" > "$T/blender.log" 2>&1
step $? "Blender re-import" "$T/blender.log"; grep -E '^\[PISTOL-BLENDER\]' "$T/blender.log"

G="$T/GodotProject"
mkdir -p "$G"
tar -C "$REPO/GodotProject" --exclude=.godot --exclude=Assets -cf - . | tar -C "$G" -xf -
cp -r "$REPO/Assets" "$G/Assets"     # real copy instead of the ../Assets symlink (TD-006)
cp "$HERE/verify_wpn_pistol_01_godot.gd" "$G/"
"$GODOT" --headless --path "$G" --import 2>&1 | strip > "$T/godot_import.log"
rc=${PIPESTATUS[0]}
if [ $rc -eq 0 ] && ! grep -qE '^(ERROR|SCRIPT ERROR|USER ERROR):' "$T/godot_import.log"; then step 0 "Godot import (project copy), 0 errors" ""; else step 1 "Godot import" "$T/godot_import.log"; grep -E -A2 '^(ERROR|SCRIPT ERROR|USER ERROR):' "$T/godot_import.log" | head; fi
grep -E '^\[UW-IMPORT\].*Pistol' "$T/godot_import.log"
"$GODOT" --headless --path "$G" --script res://verify_wpn_pistol_01_godot.gd 2>&1 | strip > "$T/godot_verify.log"
rc=${PIPESTATUS[0]}; grep -E '^\[PISTOL-GODOT\]' "$T/godot_verify.log"
grep -qE '^(SCRIPT ERROR|USER ERROR):' "$T/godot_verify.log" && { grep -E -A3 '^(SCRIPT ERROR|USER ERROR):' "$T/godot_verify.log"; rc=1; }
step $rc "Godot asset checks" "$T/godot_verify.log"

# REQ §4: swap the model in the weapon data and run Bot 3's weapon test unchanged
TRES="$G/Data/Weapons/WPN_Pistol_01.tres"
sed -i -E 's#^\[ext_resource type="PackedScene"[^]]*path="res://Scenes/Weapons/PT_Pistol.tscn"[^]]*id="2_model"\]#[ext_resource type="PackedScene" path="res://Assets/Weapons/WPN_Pistol_01/WPN_Pistol_01.glb" id="2_model"]#' "$TRES"
grep -q 'WPN_Pistol_01.glb' "$TRES"; step $? "WeaponData.scene -> WPN_Pistol_01.glb (copy only)" "$TRES"
timeout 600 "$GODOT" --headless --fixed-fps 60 --path "$G" --script res://Tests/test_weapon.gd 2>&1 | strip > "$T/test_weapon.log"
rc=${PIPESTATUS[0]}
grep -E '^\[GPTEST\]' "$T/test_weapon.log" | grep -vE '^\[GPTEST\]\[PASS\]'
echo "   $(grep -c '^\[GPTEST\]\[PASS\]' "$T/test_weapon.log") test_weapon checks passed"
grep -qE '^(SCRIPT ERROR|USER ERROR):' "$T/test_weapon.log" && rc=1
step $rc "Bot 3 test_weapon.gd with WPN_Pistol_01.glb" "$T/test_weapon.log"
echo "logs: $T"
if [ $FAILS -eq 0 ]; then echo "WPN_PISTOL_01 VERIFY: PASS"; exit 0; else echo "WPN_PISTOL_01 VERIFY: FAIL ($FAILS)"; exit 1; fi
