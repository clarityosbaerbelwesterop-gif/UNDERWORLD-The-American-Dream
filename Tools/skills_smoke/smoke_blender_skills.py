"""Smoke test: apply procedures from arjun988/blender-skills (qa-review/validation-checklist,
lod-pipeline, collision-proxy, godot-export, uv-workflow) headless via bpy to an existing
UNDERWORLD asset. Read-only on the asset; writes only to --out. Run:
  blender -b --factory-startup --python-exit-code 1 --python smoke_blender_skills.py -- <asset.glb> <outdir>
"""
import sys, os, json, math
import bpy, bmesh
from mathutils import Vector

asset, out = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=asset)
ALL = [o for o in bpy.context.scene.objects if o.type == "MESH"]
# glTF importer adds a helper "Icosphere" (empty display shape); UWP bakes LODn/UCX into the GLB already.
meshes = [o for o in ALL if o.name != "Icosphere" and "_LOD" not in o.name and not o.name.startswith("UCX_")]
R = {"existing_lod_or_ucx_objects": sorted(o.name for o in ALL if "_LOD" in o.name or o.name.startswith("UCX_"))}
R.update(dict(skipped_importer_helper=any(o.name == "Icosphere" for o in ALL)))
R.update({"asset": asset, "blender": bpy.app.version_string, "objects": len(meshes)})

def tris(o):
    me = o.data; me.calc_loop_triangles(); return len(me.loop_triangles)

# ---- A. qa-review / validation-checklist ---------------------------------
qa = {"per_object": [], "materials": sorted({s.material.name for o in meshes for s in o.material_slots if s.material})}
for o in meshes:
    bm = bmesh.new(); bm.from_mesh(o.data)
    raw_dup = len(bm.verts) - len({tuple(round(c, 5) for c in v.co) for v in bm.verts})
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    loose_v = sum(1 for v in bm.verts if not v.link_edges)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    dup = raw_dup
    uv = bool(o.data.uv_layers)
    dims = o.dimensions
    qa["per_object"].append(dict(name=o.name, tris=tris(o), ngons=ngons, loose_verts=loose_v,
        nonmanifold_edges_after_weld=nonman, split_verts_from_gltf_normals=dup, has_uv=uv, dims=[round(d, 3) for d in dims],
        sm_prefix=o.name.startswith("SM_")))
    bm.free()
qa["total_tris"] = sum(p["tris"] for p in qa["per_object"])
bb = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]  # world-space (glTF import = Z-up Blender space)
qa["bbox_size_m"] = [round(max(v[i] for v in bb) - min(v[i] for v in bb), 3) for i in range(3)]
R["A_validation_checklist"] = qa

# ---- B. lod-pipeline: Decimate 50/25 % (skill table 40-60 / 15-30) --------
lod = []
for o in meshes:
    row = {"object": o.name, "lod0": tris(o)}
    for lvl, ratio in ((1, 0.5), (2, 0.25)):
        dup = o.copy(); dup.data = o.data.copy(); dup.name = f"{o.name}_LOD{lvl}"
        bpy.context.scene.collection.objects.link(dup)
        m = dup.modifiers.new("Decimate", "DECIMATE"); m.ratio = ratio
        dg = bpy.context.evaluated_depsgraph_get(); ev = dup.evaluated_get(dg)
        me = ev.to_mesh(); me.calc_loop_triangles(); row[f"lod{lvl}"] = len(me.loop_triangles); ev.to_mesh_clear()
        row[f"lod{lvl}_slots_equal"] = len(dup.material_slots) == len(o.material_slots)
        bpy.data.objects.remove(dup)
    lod.append(row)
R["B_lod_pipeline"] = lod

# ---- C. collision-proxy: convex hull per part, COL_ collection ------------
col = bpy.data.collections.new("COL_Collision_Asset"); bpy.context.scene.collection.children.link(col)
hulls = []
for o in meshes:
    bm = bmesh.new(); bm.from_mesh(o.data)
    res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    interior = res["geom_interior"]
    bmesh.ops.delete(bm, geom=res["geom_unused"] + interior, context="VERTS")
    nv = len(bm.verts)
    hulls.append({"object": o.name, "src_verts": len(o.data.vertices), "hull_verts": nv, "hull_faces": len(bm.faces),
                  "within_uwp_convex_max_64": nv <= 64})
    bm.free()
R["C_collision_proxy"] = hulls

# ---- D. godot-export settings: GLB, +Y up, modifiers applied -> re-import ---
outglb = os.path.join(out, "roundtrip.glb")
bpy.ops.export_scene.gltf(filepath=outglb, export_format="GLB", export_yup=True, export_apply=True,
                          use_selection=False, export_animations=True)
size = os.path.getsize(outglb)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=outglb)
m2 = [o for o in bpy.context.scene.objects if o.type == "MESH"]
R["D_godot_export"] = {"bytes": size, "meshes_after": len(m2), "tris_after": sum(tris(o) for o in m2)}

# ---- E. uv-workflow: UV coverage / texel density estimate -----------------
uvr = []
for o in [x for x in m2 if x.name != 'Icosphere' and '_LOD' not in x.name and not x.name.startswith('UCX_')]:
    if not o.data.uv_layers: uvr.append({"object": o.name, "uv": False}); continue
    uvl = o.data.uv_layers.active.data; me = o.data
    a3 = a2 = 0.0
    for p in me.polygons:
        a3 += p.area
        pts = [uvl[i].uv for i in p.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i+1) % len(pts)].y - pts[(i+1) % len(pts)].x * pts[i].y for i in range(len(pts)))) / 2
    uvr.append({"object": o.name, "uv": True, "uv_area_0_1": round(a2, 4),
                "texel_density_px_per_m_at_1024": round(math.sqrt(a2 / a3) * 1024, 1) if a3 > 0 and a2 > 0 else None})
R["E_uv_workflow"] = uvr
json.dump(R, open(os.path.join(out, "smoke_result.json"), "w"), indent=1)
print("SMOKE_DONE", json.dumps({k: (v if k in ("asset","objects","blender") else "ok") for k, v in R.items()}))
