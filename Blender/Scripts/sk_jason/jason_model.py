"""SK_Jason – procedural body/head/clothing meshes (T-ART-01, Bot 2). Original, made with bpy only.

Coordinates: metres, Blender Z-up, character faces -Y (Godot +Z, TD-004), left side = +X, T-pose.
All positions are authored for a ~1.80 m figure and scaled uniformly to 1.82 m by build_sk_jason.py.
"""
import math

import bmesh
import bpy
from mathutils import Vector

# ---------------------------------------------------------------- materials
MATERIALS = {  # name: (base colour sRGB-ish linear, roughness, metallic)
    "M_Jason_Skin":    ((0.60, 0.40, 0.30), 0.55, 0.0),
    "M_Jason_Stubble": ((0.34, 0.24, 0.19), 0.80, 0.0),
    "M_Jason_Scar":    ((0.72, 0.44, 0.38), 0.40, 0.0),
    "M_Jason_Hair":    ((0.045, 0.032, 0.024), 0.65, 0.0),
    "M_Jason_Eye":     ((0.80, 0.78, 0.74), 0.20, 0.0),
    "M_Jason_Jacket":  ((0.16, 0.085, 0.045), 0.42, 0.0),   # worn brown leather
    "M_Jason_Henley":  ((0.33, 0.33, 0.32), 0.90, 0.0),     # grey henley
    "M_Jason_Jeans":   ((0.028, 0.036, 0.068), 0.85, 0.0),    # dark jeans
    "M_Jason_Boots":   ((0.10, 0.065, 0.04), 0.60, 0.0),    # work boots
    "M_Jason_Sole":    ((0.03, 0.028, 0.026), 0.75, 0.0),   # soles, buttons
}


def make_materials():
    mats = {}
    for name, (rgb, rough, metal) in MATERIALS.items():
        m = bpy.data.materials.new(name)
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*rgb, 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if name == "M_Jason_Skin" or name == "M_Jason_Scar":
            b.inputs["Subsurface Weight"].default_value = 0.08
        mats[name] = m
    return mats


# ---------------------------------------------------------------- body (skin modifier graph)
def _body_graph():
    """(nodes, edges): node = (key, (x, y, z), (rx, ry)); right side mirrored from left."""
    N = []

    def n(key, p, r):
        N.append((key, p, r if isinstance(r, tuple) else (r, r)))

    # torso (centre line)
    n("pelvis", (0, 0.005, 0.93), (0.165, 0.112))
    n("waist", (0, 0.000, 1.04), (0.158, 0.104))
    n("belly", (0, -0.002, 1.14), (0.168, 0.112))
    n("chest", (0, -0.006, 1.27), (0.192, 0.126))
    n("uchest", (0, 0.000, 1.39), (0.205, 0.120))
    n("shbase", (0, 0.012, 1.465), (0.165, 0.095))
    n("neck0", (0, 0.015, 1.525), (0.058, 0.058))
    n("neck1", (0, 0.010, 1.625), (0.052, 0.054))
    left = []

    def l(key, p, r):
        left.append((key, p, r if isinstance(r, tuple) else (r, r)))

    # arm (T-pose along +X)
    l("sh", (0.195, 0.012, 1.455), (0.080, 0.074))
    l("uarm", (0.320, 0.012, 1.462), (0.063, 0.060))
    l("elb", (0.450, 0.012, 1.465), (0.050, 0.048))
    l("farm", (0.570, 0.010, 1.465), (0.048, 0.043))
    l("wrist", (0.695, 0.008, 1.465), (0.030, 0.023))
    l("palm", (0.745, -0.004, 1.462), (0.040, 0.017))
    l("knuck", (0.795, -0.004, 1.460), (0.040, 0.014))
    # fingers: y offsets (thumb side = -Y = front)
    fy = {"Index": -0.027, "Middle": -0.008, "Ring": 0.011, "Little": 0.028}
    flen = {"Index": (0.042, 0.026, 0.021), "Middle": (0.046, 0.029, 0.022),
            "Ring": (0.043, 0.027, 0.021), "Little": (0.034, 0.021, 0.018)}
    frad = {"Index": 0.0090, "Middle": 0.0092, "Ring": 0.0087, "Little": 0.0078}
    for f, y in fy.items():
        x = 0.805 if f != "Little" else 0.800
        r = frad[f]
        l(f"{f}0", (x, y, 1.459), r)
        for i, seg in enumerate(flen[f]):
            x += seg
            l(f"{f}{i + 1}", (x, y, 1.459 - 0.002 * (i + 1)), r * (0.95 - 0.07 * i))
    l("Thumb0", (0.735, -0.026, 1.452), 0.012)
    l("Thumb1", (0.760, -0.050, 1.446), 0.0105)
    l("Thumb2", (0.784, -0.066, 1.442), 0.0095)
    l("Thumb3", (0.804, -0.076, 1.439), 0.0085)
    # leg
    l("hip", (0.095, 0.004, 0.885), (0.100, 0.104))
    l("thigh", (0.095, -0.004, 0.72), (0.086, 0.088))
    l("knee", (0.095, -0.010, 0.52), (0.061, 0.062))
    l("calf", (0.095, 0.010, 0.38), (0.061, 0.066))
    l("bootTop", (0.095, 0.000, 0.235), (0.058, 0.062))
    l("ankle", (0.095, 0.000, 0.095), (0.047, 0.052))
    l("ball", (0.095, -0.125, 0.045), (0.050, 0.034))
    l("toe", (0.095, -0.195, 0.042), (0.043, 0.030))
    l("heel", (0.095, 0.045, 0.052), (0.044, 0.040))
    for side, sx in (("L", 1), ("R", -1)):
        for key, (x, y, z), r in left:
            N.append((f"{side}_{key}", (x * sx, y, z), r))
    E = [("pelvis", "waist"), ("waist", "belly"), ("belly", "chest"), ("chest", "uchest"),
         ("uchest", "shbase"), ("shbase", "neck0"), ("neck0", "neck1")]
    for s in ("L", "R"):
        E += [("uchest", f"{s}_sh"), (f"{s}_sh", f"{s}_uarm"), (f"{s}_uarm", f"{s}_elb"),
              (f"{s}_elb", f"{s}_farm"), (f"{s}_farm", f"{s}_wrist"), (f"{s}_wrist", f"{s}_palm"),
              (f"{s}_palm", f"{s}_knuck")]
        for f in fy:
            E += [(f"{s}_knuck", f"{s}_{f}0"), (f"{s}_{f}0", f"{s}_{f}1"), (f"{s}_{f}1", f"{s}_{f}2"),
                  (f"{s}_{f}2", f"{s}_{f}3")]
        E += [(f"{s}_palm", f"{s}_Thumb0"), (f"{s}_Thumb0", f"{s}_Thumb1"), (f"{s}_Thumb1", f"{s}_Thumb2"),
              (f"{s}_Thumb2", f"{s}_Thumb3")]
        E += [("pelvis", f"{s}_hip"), (f"{s}_hip", f"{s}_thigh"), (f"{s}_thigh", f"{s}_knee"),
              (f"{s}_knee", f"{s}_calf"), (f"{s}_calf", f"{s}_bootTop"), (f"{s}_bootTop", f"{s}_ankle"),
              (f"{s}_ankle", f"{s}_ball"), (f"{s}_ball", f"{s}_toe"), (f"{s}_ankle", f"{s}_heel")]
    return N, E


def build_body(subsurf=2):
    nodes, edges = _body_graph()
    idx = {k: i for i, (k, _, _) in enumerate(nodes)}
    me = bpy.data.meshes.new("SK_Jason_Body")
    me.from_pydata([p for _, p, _ in nodes], [(idx[a], idx[b]) for a, b in edges], [])
    ob = bpy.data.objects.new("SK_Jason_Body", me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.3
    sv = me.skin_vertices[0].data
    for i, (k, _, r) in enumerate(nodes):
        f = 1.0 if any(t in k for t in ("Index", "Middle", "Ring", "Little", "Thumb", "neck")) else 1.12
        sv[i].radius = (r[0] * f, r[1] * f)
    sv[idx["pelvis"]].use_root = True
    ss = ob.modifiers.new("Subsurf", "SUBSURF")
    ss.levels = ss.render_levels = subsurf
    _apply_all(ob)
    _flatten_soles(ob)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    loose = [v for v in bm.verts if not v.link_edges]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def _apply_all(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = new
    bpy.data.meshes.remove(old)
    new.name = ob.name


def _flatten_soles(ob):
    """Flat boot soles with the lowest point exactly at z = 0."""
    vs = ob.data.vertices
    s = 0.02
    for v in vs:
        if v.co.z < s:
            v.co.z = s - (s - v.co.z) * 0.2
    m = min(v.co.z for v in vs)
    for v in vs:
        if v.co.z < 0.12:
            v.co.z -= m * (1 - v.co.z / 0.12) if m > 0 else m * (1 - max(0.0, v.co.z) / 0.12)
    m = min(v.co.z for v in vs)
    for v in vs:
        if v.co.z < m + 1e-4:
            v.co.z = 0.0
        elif v.co.z < 0.12:
            v.co.z -= m * (1 - v.co.z / 0.12)


# ---------------------------------------------------------------- head
HEAD_C = Vector((0.0, -0.012, 1.700))


def _gauss(d, s):
    return math.exp(-(d * d) / (2 * s * s))


def build_head():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=56, v_segments=40, radius=1.0, calc_uvs=True)
    for v in bm.verts:
        x, y, z = v.co
        # base ellipsoid: width 0.150, depth 0.200, height 0.235
        rx, ry, rz = 0.077, 0.100, 0.118
        # narrower jaw / chin, fuller cranium
        if z < 0:
            t = -z
            rx *= 1 - 0.20 * t ** 1.6
            ry *= 1 - 0.12 * t ** 2
        else:
            rx *= 1 + 0.04 * z
        p = Vector((x * rx, y * ry, z * rz))
        front = max(0.0, -y)
        # nose (front, centre, lower-middle)
        nz = z * rz + 0.010
        p.y -= 0.026 * _gauss(x * rx, 0.011 + 0.006 * max(0.0, -nz) / 0.03) * _gauss(nz, 0.020) * front
        p.y -= 0.006 * _gauss(x * rx, 0.007) * _gauss(z * rz + 0.028, 0.005) * front   # nose tip
        # fuller, more vertical forehead
        p.y -= 0.010 * _gauss(z * rz - 0.055, 0.03) * front
        # brow ridge
        p.y -= 0.007 * _gauss(z * rz - 0.030, 0.010) * front
        # eye sockets
        for sx in (1, -1):
            p.y += 0.011 * _gauss(x * rx - 0.032 * sx, 0.012) * _gauss(z * rz - 0.012, 0.009) * front
        # cheekbones
        for sx in (1, -1):
            p.x += 0.006 * sx * _gauss(x * rx - 0.055 * sx, 0.02) * _gauss(z * rz + 0.005, 0.02)
        # chin
        p.y -= 0.010 * _gauss(x * rx, 0.018) * _gauss(z * rz + 0.095, 0.018) * front
        # mouth line slight indent
        p.y += 0.002 * _gauss(x * rx, 0.02) * _gauss(z * rz + 0.050, 0.004) * front
        v.co = p + HEAD_C
    # ears
    for sx in (1, -1):
        ear = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=1.0)
        for v in ear["verts"]:
            x, y, z = v.co
            v.co = Vector((x * 0.012 + 0.077 * sx, y * 0.022 + 0.008, z * 0.032 + 1.695))
    me = bpy.data.meshes.new("SK_Jason_Head")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SK_Jason_Head", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_hair(head):
    """Short hair shell: scalp faces of the head offset outward."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.normal_update()
    keep = set()
    for f in bm.faces:
        c = f.calc_center_median() - HEAD_C
        if abs(c.x) > 0.07 and c.z < 0.06:   # skip ears / sides below temple
            if c.z < 0.02:
                continue
        front = -c.y
        line = 0.062 - 0.075 * max(0.0, -front / 0.1)  # hairline high at front, low at back
        if front > 0.05:
            line = 0.068
        if c.z > line and (c.length > 0.06):
            keep.add(f)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
    for v in bm.verts:
        d = (v.co - HEAD_C)
        v.co = v.co + v.normal * (0.005 + 0.007 * max(0.0, d.z / 0.118))
    me = bpy.data.meshes.new("SK_Jason_Hair")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SK_Jason_Hair", me)
    bpy.context.scene.collection.objects.link(ob)
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.004
    sol.offset = -1
    _apply_all(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def build_eyes():
    bm = bmesh.new()
    for sx in (1, -1):
        r = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.0115, calc_uvs=True)
        for v in r["verts"]:
            v.co += Vector((0.032 * sx, -0.094, 1.712))
    me = bpy.data.meshes.new("SK_Jason_Eyes")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SK_Jason_Eyes", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_collar():
    """Leather jacket stand/fold collar: open ring around the neck base, open at the front."""
    bm = bmesh.new()
    n = 28
    rings = [(1.505, 0.078, 0.070, 0.0), (1.555, 0.080, 0.072, 0.0), (1.585, 0.092, 0.084, 0.010)]
    grid = []
    for (z, rx, ry, out) in rings:
        row = []
        for i in range(n + 1):
            a = math.radians(-70 + (320 * i / n))       # gap at the front (-Y = angle -90)
            x = math.cos(a) * (rx + out)
            y = math.sin(a) * (ry + out) + 0.012
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for r in range(len(grid) - 1):
        for i in range(n):
            bm.faces.new((grid[r][i], grid[r][i + 1], grid[r + 1][i + 1], grid[r + 1][i]))
    me = bpy.data.meshes.new("SK_Jason_Collar")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SK_Jason_Collar", me)
    bpy.context.scene.collection.objects.link(ob)
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.006
    ss = ob.modifiers.new("Subsurf", "SUBSURF")
    ss.levels = 1
    _apply_all(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def build_buttons():
    bm = bmesh.new()
    for z in (1.43, 1.395, 1.36):
        r = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.0055, calc_uvs=True)
        for v in r["verts"]:
            v.co = Vector((v.co.x, v.co.y * 0.4, v.co.z)) + Vector((0.0, -0.121 + (1.43 - z) * 0.05, z))
    me = bpy.data.meshes.new("SK_Jason_Buttons")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("SK_Jason_Buttons", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- material regions
def assign_body_materials(ob, mats):
    order = ["M_Jason_Skin", "M_Jason_Jacket", "M_Jason_Henley", "M_Jason_Jeans", "M_Jason_Boots", "M_Jason_Sole"]
    for m in order:
        ob.data.materials.append(mats[m])
    ix = {m: i for i, m in enumerate(order)}
    for p in ob.data.polygons:
        c = p.center
        ax = abs(c.x)
        if c.z < 0.012:
            m = "M_Jason_Sole"
        elif c.z < 0.245 and ax < 0.2:
            m = "M_Jason_Boots"
        elif c.z < 0.87 and ax < 0.25:
            m = "M_Jason_Jeans"
        elif ax > 0.69:                          # hands
            m = "M_Jason_Skin"
        elif c.z > 1.53 and ax < 0.075:          # neck
            m = "M_Jason_Skin"
        elif c.y < -0.06 and ax < 0.022 + (c.z - 1.12) * 0.07 and 1.12 < c.z < 1.505:
            m = "M_Jason_Henley"                 # open jacket front shows the henley
        elif c.z > 1.47 and ax < 0.075 and c.y < -0.02:
            m = "M_Jason_Henley"                 # henley neckline
        else:
            m = "M_Jason_Jacket"
        p.material_index = ix[m]


def assign_head_materials(ob, mats):
    order = ["M_Jason_Skin", "M_Jason_Stubble", "M_Jason_Scar", "M_Jason_Hair"]
    for m in order:
        ob.data.materials.append(mats[m])
    for p in ob.data.polygons:
        c = p.center - HEAD_C
        front = -c.y
        ax = abs(c.x)
        if c.length > 0.2 or ax > 0.083:        # ears
            continue
        # stubble: jaw line + chin + moustache, not the lips
        jaw = c.z < -0.048 + 0.25 * max(0.0, ax - 0.03) and c.z < -0.02 and front > -0.045
        tache = front > 0.07 and ax < 0.026 and -0.046 < c.z < -0.030
        lips = front > 0.07 and ax < 0.020 and -0.058 < c.z < -0.046
        brow = front > 0.06 and 0.012 < ax < 0.052 and 0.028 - 0.06 * (ax - 0.012) < c.z < 0.037 - 0.05 * (ax - 0.012)
        if lips:
            p.material_index = 2
        elif jaw or tache:
            p.material_index = 1
        elif brow:
            p.material_index = 3
        # scar over the LEFT eyebrow (character's left = +X): short diagonal cut through the brow
        sx, sz = c.x - 0.034, c.z - 0.036
        if front > 0.05 and abs(sx - 0.3 * sz) < 0.0032 and abs(sz) < 0.017:
            p.material_index = 2


def assign_eye_materials(ob, mats):
    ob.data.materials.append(mats["M_Jason_Eye"])
    ob.data.materials.append(mats["M_Jason_Hair"])      # iris/pupil = dark brown
    for p in ob.data.polygons:
        local_y = p.center.y + 0.094
        if local_y < -0.0085:
            p.material_index = 1


def smart_uv(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")


def build_all():
    mats = make_materials()
    body = build_body()
    head = build_head()
    hair = build_hair(head)
    eyes = build_eyes()
    collar = build_collar()
    buttons = build_buttons()
    assign_body_materials(body, mats)
    assign_head_materials(head, mats)
    hair.data.materials.append(mats["M_Jason_Hair"])
    assign_eye_materials(eyes, mats)
    collar.data.materials.append(mats["M_Jason_Jacket"])
    buttons.data.materials.append(mats["M_Jason_Sole"])
    # tilt the whole head (head, hair, eyes) chin-down a little around the neck top: natural profile
    from mathutils import Matrix
    piv = Vector((0.0, 0.012, 1.625))
    tilt = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(7), 4, "X") @ Matrix.Translation(-piv)
    for ob in (head, hair, eyes):
        ob.data.transform(tilt)
    for ob in (body, head, hair, eyes, collar, buttons):
        smart_uv(ob)
    return {"body": body, "head": head, "hair": hair, "eyes": eyes, "collar": collar, "buttons": buttons}
