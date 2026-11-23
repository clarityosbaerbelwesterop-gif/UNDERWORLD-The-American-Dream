"""LOD + collision generation (in-memory only; the source .blend is never saved)."""
import bmesh
import bpy
from mathutils import Matrix

from . import scene as S


def _bake_copy(ob, name, extra_mod=None):
    """Copy ob with its modifiers (+ optional extra) baked into a new mesh."""
    tmp = ob.copy()
    tmp.data = ob.data.copy()
    S.link_like(tmp, ob)
    if extra_mod:
        extra_mod(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = tmp.data
    tmp.modifiers.clear()
    tmp.data = me
    bpy.data.meshes.remove(old)
    tmp.name = name
    me.name = name
    return tmp


def _tris(me):
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def generate_lods(ctx, ratios, distances):
    """LOD1..n as children of each static visible mesh, named <Name>_LOD<n>.

    LOD0 keeps its original name (Bot 3 / smoke tests address nodes by name).
    Each LOD node carries glTF extras uw_lod / uw_visibility_range ([begin, end] m)
    so Godot (post-import script Tools/underworld_pipeline/godot/uw_lod_post_import.gd)
    can set GeometryInstance3D.visibility_range_*.
    """
    sc = bpy.context.scene
    min_tris = ctx.cfg.get("lod_min_triangles") or 0
    made = []
    if not ratios:
        ctx.issues.info("LOD_NONE", f"no LOD ratios configured for {ctx.category}")
        return made
    for ob in S.visible_meshes(sc):
        base, hint = S.split_hint(ob.name)
        if S.is_skinned(ob):
            ctx.issues.info("LOD_SKIP_SKINNED", "skinned mesh: no baked LODs (Godot generates mesh LODs on import)", ob.name)
            continue
        if ob.get("uw_no_lod") or any(S.lod_level(c.name) > 0 for c in ob.children):
            ctx.issues.info("LOD_SKIP", "uw_no_lod set or hand-made LODs present", ob.name)
            continue
        dg = bpy.context.evaluated_depsgraph_get()
        base_tris = S.evaluated_mesh_stats(ob, dg, geometry=False)["triangles"]
        if base_tris < min_tris:
            ctx.issues.info("LOD_SKIP_SMALL", f"{base_tris} tris < lod_min_triangles {min_tris}", ob.name)
            continue
        ob["uw_lod"] = 0
        if distances:
            ob["uw_visibility_range"] = [0.0, float(distances[0])]
        levels = [{"name": ob.name, "level": 0, "triangles": base_tris}]
        for i, r in enumerate(ratios, start=1):
            def add_dec(t, r=r):
                m = t.modifiers.new("UW_Decimate", "DECIMATE")
                m.decimate_type = "COLLAPSE"
                m.ratio = r
                m.use_collapse_triangulate = True
            lod_name = f"{base}_LOD{i}"
            lod = _bake_copy(ob, lod_name, add_dec)
            lod.parent = ob
            lod.matrix_parent_inverse = Matrix.Identity(4)
            lod.matrix_basis = Matrix.Identity(4)
            for k in list(lod.keys()):
                del lod[k]
            lod["uw_lod"] = i
            if distances and len(distances) > i:
                lod["uw_visibility_range"] = [float(distances[i - 1]), float(distances[i])]
            t = _tris(lod.data)
            levels.append({"name": lod_name, "level": i, "ratio": r, "triangles": t})
        made.append({"object": ob.name, "levels": levels})
        print(f"[UWP] LODs {ob.name}: " + ", ".join(f"LOD{l['level']}={l['triangles']}" for l in levels))
    return made


def _hull_object(name, points, root, max_verts, issues):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    bmesh.ops.delete(bm, geom=list(set(res["geom_interior"]) | set(res["geom_unused"])), context="VERTS")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if len(me.vertices) > max_verts:
        m = ob.modifiers.new("UW_Decimate", "DECIMATE")
        m.ratio = max(0.02, max_verts / len(me.vertices))
        dg = bpy.context.evaluated_depsgraph_get()
        dec = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        ob.modifiers.clear()
        pts = [v.co.copy() for v in dec.vertices]
        bpy.data.meshes.remove(dec)
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(p)
        res = bmesh.ops.convex_hull(bm, input=bm.verts)
        bmesh.ops.delete(bm, geom=list(set(res["geom_interior"]) | set(res["geom_unused"])), context="VERTS")
        bm.to_mesh(me)
        bm.free()
    _parent_world(ob, root)
    return ob


def _parent_world(ob, root):
    if root is not None:
        ob.parent = root
        ob.matrix_parent_inverse = root.matrix_world.inverted()


def _world_points(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        pts.extend(ev.matrix_world @ v.co for v in me.vertices)
        ev.to_mesh_clear()
    return pts


def generate_collision(ctx, mode):
    """mode: box | convex | trimesh | none. Skipped when authored collision exists."""
    sc = bpy.context.scene
    name = ctx.asset_name
    root = sc.objects.get(name)
    existing = [o.name for o in sc.objects if S.is_collision(o)]
    if mode == "none":
        return {"mode": "none", "generated": [], "existing": existing}
    if existing and not ctx.opts.force_collision:
        ctx.issues.info("COLLISION_AUTHORED", f"authored collision kept, nothing generated: {existing}")
        return {"mode": "authored", "generated": [], "existing": existing}
    srcs = S.visible_meshes(sc)
    if not srcs:
        ctx.issues.warn("COLLISION_NO_SOURCE", "no visible meshes to build collision from")
        return {"mode": mode, "generated": [], "existing": existing}
    # Hull-type proxies (box/convex) may use the lowest LOD (fewer points, same hull).
    # A TRIMESH proxy must come from LOD0: decimation closes openings - the M01 garage's
    # LOD2-derived collision sealed the roll-up door shut (B-PT-02, T-BUILD-02).
    low = []
    for ob in srcs:
        lods = sorted((c for c in ob.children if S.lod_level(c.name) > 0), key=lambda c: S.lod_level(c.name))
        low.append(lods[-1] if (lods and mode != "trimesh") else ob)
    with S.rest_pose(sc):
        pts = _world_points(low)
    made = []
    if mode == "box":
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        ob = _hull_object(f"UCX_{name}-convcolonly", corners, root, 8, ctx.issues)
        made.append(ob)
    elif mode == "convex":
        ob = _hull_object(f"UCX_{name}-convcolonly", pts, root, ctx.cfg.get("convex_max_vertices") or 64, ctx.issues)
        made.append(ob)
    elif mode == "trimesh":
        for i, src in enumerate(low):
            base = S.split_hint(src.name)[0]
            ob = _bake_copy(src, f"UCX_{base}-colonly")
            for k in list(ob.keys()):
                del ob[k]
            mw = src.matrix_world.copy()
            ob.data.materials.clear()
            ob.parent = None
            ob.matrix_world = mw
            # bake world transform into the mesh, then parent to root
            ob.data.transform(ob.matrix_world)
            ob.matrix_world = Matrix.Identity(4)
            _parent_world(ob, root)
            made.append(ob)
    else:
        raise ValueError(f"unknown collision mode {mode}")
    out = []
    for ob in made:
        ob.data.name = ob.name
        out.append({"name": ob.name, "vertices": len(ob.data.vertices), "triangles": _tris(ob.data)})
        print(f"[UWP] collision {ob.name}: {len(ob.data.vertices)} verts")
    return {"mode": mode, "generated": out, "existing": existing}


def check_collision_micro_lips(ctx, max_lip_m=0.02, min_lip_m=0.0005):
    """T-BUILD-02 bug B-PT-01: a near-vertical collision face lower than the character
    controller's step threshold (2 cm, PlayerController.step_min_height) is a "micro-lip": the
    cylinder (TD-011) snags on it and stops dead. The road kit's 4 mm paint stripes inside the
    trimesh collision did exactly that. Walkable collision must be coplanar or a real step.
    Returns a list of {object, height_m, at} findings; each one is reported as an error."""
    import bmesh
    findings = []
    sc = bpy.context.scene
    for ob in sc.objects:
        if not S.is_collision(ob):
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.transform(ob.matrix_world)
        bm.normal_update()
        for f in bm.faces:
            if f.calc_area() < 1e-8 or abs(f.normal.z) > 0.2:
                continue                      # floor/ceiling-like faces are fine
            zs = [v.co.z for v in f.verts]
            h = max(zs) - min(zs)
            if min_lip_m < h < max_lip_m:
                c = f.calc_center_median()
                findings.append({"object": ob.name, "height_m": round(h, 4),
                                 "at": [round(c.x, 3), round(c.y, 3), round(c.z, 3)]})
        bm.free()
    for fd in findings[:8]:
        ctx.issues.error("COLLISION_MICRO_LIP",
                         f"{fd['height_m'] * 1000:.1f} mm vertical collision face at {fd['at']} snags the player "
                         f"(walkable collision must be coplanar or >= {max_lip_m * 100:.0f} cm; author a flat UCX_ proxy)",
                         fd["object"])
    if len(findings) > 8:
        ctx.issues.error("COLLISION_MICRO_LIP", f"... {len(findings) - 8} more micro-lip faces", findings[8]["object"])
    return findings
