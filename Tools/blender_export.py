"""
UNDERWORLD - Blender -> Godot pipeline smoke-test exporter.

!!! PIPELINE TEST PLACEHOLDER - NOT FINAL ART !!!
This script procedurally builds a simple labelled test asset
(PT_PipelineTest_Crate), applies transforms, validates it, saves the
.blend source and exports glTF 2.0 binary (.glb) for Godot.

Owner: Bot 1 (bootstrap). Bot 2 owns the production exporter that will
replace/extend this (see TASK_BOARD.md, T-PIPE-01).

Usage (headless):
  /workspace/tools/blender/blender -b --factory-startup \
      --python Tools/blender_export.py -- --repo /workspace/UNDERWORLD

Exit code 0 = success, 1 = validation/export failure.
"""
import argparse
import json
import math
import os
import sys
import traceback

import bpy

ASSET_NAME = "PT_PipelineTest_Crate"
EXPECTED_DIMS = (1.0, 1.0, 1.0)  # metres, Blender X/Y/Z of the crate body


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return p.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0  # 1 Blender unit = 1 metre


def make_material(name, rgba, metallic=0.0, roughness=0.6):
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):  # node materials are always-on in Blender 5.x
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def build_asset():
    root = bpy.data.objects.new(ASSET_NAME, None)  # empty as asset root
    bpy.context.scene.collection.objects.link(root)

    # Crate body: 1 m cube resting on the ground (origin at bottom centre).
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
    body = bpy.context.active_object
    body.name = "SM_" + ASSET_NAME + "_Body"
    bev = body.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.04
    bev.segments = 2
    bpy.ops.object.modifier_apply(modifier=bev.name)
    body.data.materials.append(make_material("M_PT_PlaceholderOrange", (1.0, 0.35, 0.0, 1.0)))

    # Forward marker: cone on Blender -Y (= model front, becomes Godot +Z).
    bpy.ops.mesh.primitive_cone_add(radius1=0.12, depth=0.3, location=(0, -0.65, 0.5),
                                    rotation=(math.radians(90), 0, 0))
    fwd = bpy.context.active_object
    fwd.name = "SM_" + ASSET_NAME + "_FrontMarker"
    fwd.data.materials.append(make_material("M_PT_PlaceholderBlue", (0.05, 0.3, 1.0, 1.0)))

    # Collision proxy: Godot import hint "-colonly" -> StaticBody3D + shape, no mesh.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
    col = bpy.context.active_object
    col.name = "UCX_" + ASSET_NAME + "-colonly"

    for ob in (body, fwd, col):
        ob.data.name = ob.name  # mesh datablock names match object names
        ob.parent = root
        # Every object must have a UV map (primitives ship one); enforce.
        if not ob.data.uv_layers:
            ob.data.uv_layers.new(name="UVMap")

    # Apply all transforms so exported meshes carry clean 1/0/0 transforms.
    bpy.ops.object.select_all(action="DESELECT")
    for ob in (body, fwd, col):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return root, body, fwd, col


def validate(body, fwd, col):
    errors = []
    dims = tuple(round(v, 3) for v in body.dimensions)
    if any(abs(a - b) > 0.01 for a, b in zip(dims, EXPECTED_DIMS)):
        errors.append(f"body dimensions {dims} != expected {EXPECTED_DIMS}")
    for ob in (body, fwd, col):
        if tuple(ob.scale) != (1.0, 1.0, 1.0) or tuple(ob.rotation_euler) != (0.0, 0.0, 0.0):
            errors.append(f"{ob.name}: transforms not applied")
        if not ob.data.uv_layers:
            errors.append(f"{ob.name}: missing UV map")
    for ob in (body, fwd):
        if not ob.data.materials:
            errors.append(f"{ob.name}: no material")
    tris = sum(len(p.vertices) - 2 for ob in (body, fwd) for p in ob.data.polygons)
    return errors, dims, tris


def main():
    args = parse_args()
    repo = os.path.abspath(args.repo)
    out_dir = os.path.join(repo, "Assets", "Test")
    blend_dir = os.path.join(repo, "Blender", "Source", "Test")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(blend_dir, exist_ok=True)
    glb = os.path.join(out_dir, ASSET_NAME + ".glb")
    blend = os.path.join(blend_dir, ASSET_NAME + ".blend")

    reset_scene()
    root, body, fwd, col = build_asset()
    errors, dims, tris = validate(body, fwd, col)
    if errors:
        for e in errors:
            print("[PIPELINE][ERROR]", e)
        return 1

    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.export_scene.gltf(
        filepath=glb,
        export_format="GLB",
        export_yup=True,          # Blender Z-up -> glTF/Godot Y-up
        export_apply=True,        # apply modifiers
        export_materials="EXPORT",
        export_extras=True,
    )
    if not os.path.isfile(glb) or os.path.getsize(glb) < 1000:
        print("[PIPELINE][ERROR] glb missing or too small:", glb)
        return 1

    # Round-trip check: re-import the glb into an empty scene.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
    if len(meshes) != 3:
        print("[PIPELINE][ERROR] round-trip mesh count", meshes)
        return 1

    manifest = {
        "asset": ASSET_NAME,
        "status": "PIPELINE TEST PLACEHOLDER - NOT FINAL ART",
        "source_blend": os.path.relpath(blend, repo),
        "export_glb": os.path.relpath(glb, repo),
        "blender_version": bpy.app.version_string,
        "units": "metres (1 BU = 1 m)",
        "up_axis": "Blender +Z -> glTF/Godot +Y (exporter export_yup)",
        "front": "Blender -Y -> Godot +Z (Vector3.MODEL_FRONT)",
        "body_dimensions_m": dims,
        "triangles_visible": tris,
        "roundtrip_meshes": meshes,
        "glb_bytes": os.path.getsize(glb),
    }
    with open(os.path.join(out_dir, ASSET_NAME + ".manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("[PIPELINE][OK]", json.dumps(manifest))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    os._exit(code)
