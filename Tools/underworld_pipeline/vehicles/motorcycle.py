"""Motorcycle generator (P5, T-VEH-04): VH_Motorcycle_01 - an ORIGINAL 1970s-style standard/cafe
street bike (no real make or model). Parts: Body (frame, tank, seat, engine, exhaust, rear
swingarm, fenders), Fork (steering head + forks + bars + headlight; origin on the steering axis
so it can turn), Wheel_F / Wheel_R (origin on the axle). Sockets: SOCKET_Seat_Driver (rider
H-point), SOCKET_Seat_Passenger, SOCKET_Exit_Left/Right. One convex hull. Blender -Y = front.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

from underworld_pipeline.vehicles import build_vehicle as BV


def _tube(bm, a, b, r, segs=10):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=d.length,
                          matrix=Matrix.Translation((a + b) / 2) @ rot)


def _tagged(bm, fn, idx):
    n0 = len(bm.faces)
    fn()
    bm.faces.ensure_lookup_table()
    for f in list(bm.faces)[n0:]:
        f.material_index = idx


def build_motorcycle(spec, repo_root):
    name = spec["asset_name"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system, sc.unit_settings.scale_length = "METRIC", 1.0
    sc.render.fps = 30
    root = bpy.data.objects.new(name, None)
    sc.collection.objects.link(root)
    m_paint = BV._mat(f"M_{name}_Paint", tuple(spec.get("paint_rgba", (0.45, 0.04, 0.03, 1.0))), roughness=0.25, metallic=0.5, coat=1.0, coat_rough=0.04)
    m_chrome = BV._mat(f"M_{name}_Chrome", (0.82, 0.84, 0.86, 1.0), roughness=0.10, metallic=0.97)
    m_frame = BV._mat(f"M_{name}_Frame", (0.05, 0.05, 0.055, 1.0), roughness=0.4, metallic=0.6)
    m_engine = BV._mat(f"M_{name}_Engine", (0.42, 0.43, 0.45, 1.0), roughness=0.45, metallic=0.85)
    m_seat = BV._mat(f"M_{name}_Seat", (0.03, 0.028, 0.026, 1.0), roughness=0.6)
    m_tire = BV._mat(f"M_{name}_Tire", (0.045, 0.045, 0.048, 1.0), roughness=0.85)
    m_rim = BV._mat(f"M_{name}_Rim", (0.72, 0.74, 0.76, 1.0), roughness=0.2, metallic=0.95)
    m_head = BV._mat(f"M_{name}_Headlight", (0.95, 0.92, 0.82, 1.0), roughness=0.08, metallic=0.2, emit=1.5)
    mats = [m_paint, m_chrome, m_frame, m_engine, m_seat]
    wr = 0.32                                   # 18" wheels with tyre
    yf, yr = -0.72, 0.70                        # axles (wheelbase 1.42 m)
    head = Vector((0, -0.48, 0.98))             # steering head (top)
    bm = bmesh.new()
    # frame: backbone, down tubes, cradle, rear loop  (material 2)
    pts = dict(head=head, head_lo=Vector((0, -0.56, 0.78)), spine=Vector((0, 0.15, 0.86)), seat_r=Vector((0, 0.62, 0.84)),
               cradle_f=Vector((0, -0.38, 0.30)), cradle_r=Vector((0, 0.22, 0.30)), pivot=Vector((0, 0.24, 0.48)))
    def frame():
        for sx in (-0.07, 0.07):
            o = Vector((sx, 0, 0))
            _tube(bm, pts["head"] + o * 0.3, pts["spine"] + o, 0.018)
            _tube(bm, pts["head_lo"] + o * 0.3, pts["cradle_f"] + o, 0.018)
            _tube(bm, pts["cradle_f"] + o, pts["cradle_r"] + o, 0.018)
            _tube(bm, pts["cradle_r"] + o, pts["spine"] + o, 0.018)
            _tube(bm, pts["spine"] + o, pts["seat_r"] + o, 0.016)
            _tube(bm, pts["pivot"] + o * 2.2, Vector((sx * 2.2, yr, wr)), 0.022)       # swingarm
            _tube(bm, pts["seat_r"] + o * 1.6, Vector((sx * 2.2, yr - 0.05, wr + 0.05)), 0.02)  # shock
    _tagged(bm, frame, 2)
    # tank (paint), side covers, fenders
    def paint():
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0,
                                  matrix=Matrix.Translation((0, -0.18, 0.92)) @ Matrix.Diagonal((0.17, 0.30, 0.12, 1.0)))
        BV._add_box(bm, (0, 0.30, 0.68), (0.20, 0.30, 0.22), bevel=0.04, segs=2)                 # side cover / airbox
        BV._add_box(bm, (0, yr + 0.05, wr + 0.36), (0.16, 0.55, 0.03), rot=(math.radians(-12), 0, 0), bevel=0.01, segs=1)
    _tagged(bm, paint, 0)
    def seat():
        BV._add_box(bm, (0, 0.40, 0.93), (0.25, 0.62, 0.09), bevel=0.04, segs=2)
    _tagged(bm, seat, 4)
    def engine():
        BV._add_box(bm, (0, -0.10, 0.50), (0.42, 0.42, 0.30), bevel=0.05, segs=2)                # crankcase
        for i in range(4):                                                                           # finned cylinders
            BV._add_box(bm, (0, -0.16, 0.66 + i * 0.045), (0.36, 0.26, 0.03), bevel=0.0, segs=1)
        BV._add_box(bm, (0, -0.16, 0.86), (0.30, 0.22, 0.07), bevel=0.02, segs=1)                 # head
    _tagged(bm, engine, 3)
    def chrome():
        for sx in (-1, 1):                                                                           # 2-into-2 exhaust
            _tube(bm, (sx * 0.12, -0.28, 0.62), (sx * 0.16, -0.30, 0.30), 0.024)
            _tube(bm, (sx * 0.16, -0.30, 0.30), (sx * 0.20, 0.30, 0.28), 0.024)
            _tube(bm, (sx * 0.20, 0.30, 0.28), (sx * 0.21, 0.82, 0.40), 0.038)
        _tube(bm, (0, 0.95, 0.70), (0, 0.98, 0.62), 0.02)                                          # tail light stalk
    _tagged(bm, chrome, 1)
    body = BV._make_obj(bm, "Body", root, mats[0], subsurf=0)
    for m in mats[1:]:
        body.data.materials.append(m)
    body["uw_allow_uv_overlap"] = 1
    # fork assembly: turns about the steering axis (origin at the steering head)
    fb = bmesh.new()
    rake = math.radians(27)
    axis = Vector((0, -math.sin(rake), -math.cos(rake)))      # down the steering axis
    for sx in (-0.10, 0.10):
        top = head + Vector((sx, 0, 0.06))
        _tube(fb, top, Vector((sx, yf, wr)), 0.022)
    _tube(fb, head + Vector((-0.36, 0.10, 0.16)), head + Vector((0.36, 0.10, 0.16)), 0.012)       # bars
    for sx in (-0.36, 0.36):
        _tube(fb, head + Vector((sx, 0.10, 0.16)), head + Vector((sx * 1.05, 0.14, 0.16)), 0.018)  # grips
    _tube(fb, head + Vector((0, 0, 0.06)), head + Vector((0, 0.10, 0.16)), 0.016)                  # riser
    n0 = len(fb.faces)
    bmesh.ops.create_uvsphere(fb, u_segments=14, v_segments=8, radius=1.0,
                              matrix=Matrix.Translation(head + Vector((0, -0.14, -0.06))) @ Matrix.Diagonal((0.09, 0.07, 0.09, 1.0)))
    n1 = len(fb.faces)
    BV._add_box(fb, (0, yf - 0.02, wr + 0.30), (0.14, 0.42, 0.025), rot=(math.radians(14), 0, 0), bevel=0.01, segs=1)  # front fender
    fb.faces.ensure_lookup_table()
    for i, f in enumerate(fb.faces):              # slots: 0 chrome tubes, 1 headlight lens, 2 paint fender
        f.material_index = 0 if i < n0 else (1 if i < n1 else 2)
    fork = BV._make_obj(fb, "Fork", root, m_chrome, origin_world=tuple(head))
    fork.data.materials.append(m_head)
    fork.data.materials.append(m_paint)
    fork["uw_allow_uv_overlap"] = 1
    _ = axis
    for wname, y in (("Wheel_F", yf), ("Wheel_R", yr)):
        BV._build_wheel(wname, root, (0.0, y, wr), wr, 0.11 if wname == "Wheel_F" else 0.14, m_tire, m_rim)
    bc = bmesh.new()
    BV._add_box(bc, (0, 0.0, 0.62), (0.50, 2.05, 1.10), bevel=0.0, segs=1)
    res = bmesh.ops.convex_hull(bc, input=bc.verts)
    hull = set(f for f in res["geom"] if isinstance(f, bmesh.types.BMFace))
    bmesh.ops.delete(bc, geom=[f for f in bc.faces if f not in hull], context="FACES_ONLY")
    mc = bpy.data.meshes.new(f"UCX_{name}-convcolonly")
    bc.to_mesh(mc)
    bc.free()
    oc = bpy.data.objects.new(f"UCX_{name}-convcolonly", mc)
    sc.collection.objects.link(oc)
    oc.parent = root
    for sname, loc in (("SOCKET_Seat_Driver", (0, 0.32, 0.98)), ("SOCKET_Seat_Passenger", (0, 0.62, 1.00)),
                       ("SOCKET_Exit_Left", (0.75, 0.2, 0.0)), ("SOCKET_Exit_Right", (-0.75, 0.2, 0.0)),
                       ("SOCKET_Headlight_L", tuple(head + Vector((0, -0.22, -0.06))))):
        s = bpy.data.objects.new(sname, None)
        s.empty_display_type, s.empty_display_size = "ARROWS", 0.15
        sc.collection.objects.link(s)
        s.parent, s.location = root, loc
    root["uw_kind"] = "motorcycle"
    root["uw_wheel_radius_m"] = wr
    root["uw_wheelbase_m"] = yr - yf
    p = os.path.join(repo_root, "Blender", "Source", "Vehicles", name, f"{name}.blend")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=p, compress=True)
    print(f"[VEHICLE] built {name} (motorcycle, wheelbase {yr - yf:.2f} m) -> {os.path.relpath(p, repo_root)}")
    return p
