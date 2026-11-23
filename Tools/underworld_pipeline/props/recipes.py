"""Prop recipes (P3 street furniture, P5 items + armor). Real-world dimensions in metres,
front = -Y (TD-004), ground at z = 0. Names, signs and brands are invented for UNDERWORLD.

Each recipe: fn(P) where P is kit.Prop. Registered in RECIPES with its Blender/Source category.
"""
import math

TAU = math.tau


# ============================================================ P3 street furniture (LA)
def road_intersection(P):
    """14 x 14 m intersection tile, kerb-free centre; matches SM_LA_Road_Straight (top z 0.04)."""
    P.box((0, 0, 0.02), (14.0, 14.0, 0.04), "asphalt")
    # stop bars + zebra crosswalks on the four approaches (render-only, 4 mm)
    for k in range(4):
        a = k * TAU / 4
        ca, sa = math.cos(a), math.sin(a)
        for i in range(-4, 5):
            off = i * 0.95
            cx, cy = ca * 5.6 - sa * off, sa * 5.6 + ca * off
            P.box((cx, cy, 0.042), (2.2, 0.5, 0.004) if k % 2 == 0 else (0.5, 2.2, 0.004), "paint_road_white")
        # stop bar on the inbound half of each approach (right-hand traffic)
        sx, sy = ca * 4.15 + sa * 2.4, sa * 4.15 - ca * 2.4
        P.box((sx, sy, 0.042), (0.35, 4.4, 0.004) if k % 2 == 0 else (4.4, 0.35, 0.004), "paint_road_white")
    P.col_slab((14.0, 14.0), 0.04)


def road_crosswalk(P):
    """10 x 14 m straight road with a mid-block zebra crosswalk (same profile as Road_Straight)."""
    P.box((0, 0, 0.02), (10.0, 14.0, 0.04), "asphalt")
    for sx in (-0.11, 0.11):
        P.box((sx, -4.5, 0.043), (0.10, 5.0, 0.004), "paint_road_yellow")
        P.box((sx, 4.5, 0.043), (0.10, 5.0, 0.004), "paint_road_yellow")
    for i in range(-4, 5):
        P.box((i * 0.95, 0, 0.042), (0.5, 3.0, 0.004), "paint_road_white")
    for sx in (-4.3, 4.3):
        P.box((sx, 0, 0.043), (0.12, 13.9, 0.004), "paint_road_white")
    P.col_slab((10.0, 14.0), 0.04)


def traffic_light(P):
    """Mast-arm traffic signal: 5.8 m pole, 4.5 m arm over the lane (-Y), two 3-lens heads."""
    P.cyl((0, 0, 0.15), 0.22, 0.30, "concrete", segs=16)
    P.cyl((0, 0, 2.95), 0.11, 5.6, "metal_galv", segs=14, radius2=0.085)
    P.tube([(0, 0, 5.55), (0, -1.5, 5.62), (0, -3.0, 5.66), (0, -4.5, 5.68)], 0.06, "metal_galv", segs=10)
    P.tube([(0, -0.05, 4.7), (0, -1.4, 5.55)], 0.035, "metal_galv", segs=8)
    for y in (-2.6, -4.3):
        P.box((0, y, 5.22), (0.36, 0.30, 1.05), "paint_yellow", bevel=0.03)
        for k, (z, lens) in enumerate(((5.55, "signal_red"), (5.22, "signal_amber"), (4.89, "signal_green"))):
            P.cyl((0, y - 0.155, z), 0.12, 0.02, lens, segs=16, rot=(math.pi / 2, 0, 0))
            P.cyl((0, y - 0.20, z + 0.07), 0.15, 0.12, "paint_black", segs=12, rot=(math.pi / 2, 0, 0), radius2=0.15, caps=False)
    # pedestrian head on the pole + push button
    P.box((0.0, -0.22, 2.9), (0.34, 0.24, 0.34), "paint_yellow", bevel=0.02)
    P.label((0.0, -0.341, 2.9), (0.28, 0.28), "label:WalkSignal:WAIT|ff7a1a|111111|256x256")
    P.box((0, -0.13, 1.1), (0.10, 0.08, 0.14), "paint_black", bevel=0.01)
    P.col_box((0, 0, 2.9), (0.3, 0.3, 5.8))


def hydrant(P):
    """LA-style wet-barrel fire hydrant (0.75 m)."""
    P.lathe([(0.16, 0.0), (0.16, 0.05), (0.12, 0.07), (0.11, 0.10), (0.11, 0.52), (0.13, 0.54),
             (0.13, 0.58), (0.10, 0.61), (0.09, 0.68), (0.05, 0.73), (0.0, 0.75)], "paint_yellow", segs=20)
    for a in (0.0, math.pi, -math.pi / 2):
        ca, sa = math.cos(a), math.sin(a)
        P.cyl((ca * 0.15, sa * 0.15, 0.40), 0.055, 0.10, "paint_yellow", segs=12, rot=(0, math.pi / 2, a) if abs(sa) < 0.5 else (math.pi / 2, 0, 0))
        P.cyl((ca * 0.21, sa * 0.21, 0.40), 0.04, 0.03, "metal_dark", segs=6, rot=(0, math.pi / 2, a) if abs(sa) < 0.5 else (math.pi / 2, 0, 0))
    P.cyl((0, 0, 0.77), 0.025, 0.04, "metal_dark", segs=5)
    for i in range(6):
        a = i * TAU / 6
        P.cyl((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.055), 0.015, 0.03, "metal_dark", segs=6)
    P.col_box((0, 0, 0.38), (0.34, 0.34, 0.76))


def trash_can(P):
    """Perforated steel street bin with dome lid (1.0 m)."""
    P.lathe([(0.27, 0.0), (0.28, 0.02), (0.28, 0.86), (0.29, 0.88), (0.29, 0.90)], "paint_green", segs=24, cap_top=False)
    P.lathe([(0.255, 0.86), (0.255, 0.03)], "metal_dark", segs=24, cap_top=False, cap_bottom=False)  # inner wall
    P.cyl((0, 0, 0.035), 0.255, 0.01, "metal_dark", segs=24)
    for i in range(12):
        a = i * TAU / 12
        P.box((math.cos(a) * 0.285, math.sin(a) * 0.285, 0.45), (0.03, 0.03, 0.78), "paint_green", rot=(0, 0, a))
    P.lathe([(0.30, 0.90), (0.30, 0.93), (0.24, 0.98), (0.14, 1.01), (0.0, 1.02)], "paint_green", segs=24)
    P.box((0, -0.27, 0.94), (0.22, 0.08, 0.06), "metal_dark", bevel=0.01)          # push flap
    P.label((0, -0.302, 0.62), (0.26, 0.10), "label:TrashLabel:CITY OF LA HOLLOW|e8e8e0|1d4a2a|512x192")
    P.col_box((0, 0, 0.51), (0.6, 0.6, 1.02))


def bus_stop(P):
    """Bus shelter 3.6 x 1.5 x 2.5 m: steel frame, glass back, bench, ad panel, route sign."""
    for x in (-1.75, 1.75):
        for y in (0.65, -0.55):
            P.box((x, y, 1.2), (0.08, 0.08, 2.4), "metal_galv", bevel=0.01)
    P.box((0, 0.05, 2.45), (3.7, 1.55, 0.10), "metal_galv", bevel=0.02)                 # roof
    P.box((0, 0.05, 2.52), (3.6, 1.45, 0.04), "corrugated")
    P.box((0, 0.66, 1.3), (3.4, 0.02, 1.9), "glass")                                     # back glass
    P.box((-1.75, 0.05, 1.3), (0.02, 1.1, 1.9), "glass")
    P.box((1.4, 0.64, 1.25), (0.9, 0.12, 1.75), "metal_dark", bevel=0.015)              # ad box
    P.label((1.4, 0.578, 1.25), (0.78, 1.6), "label:AdBusStop:SUNDOWN\\nCOLA\\n\\nTaste the coast.|fff4d6|b5361b|256x512", rot=(0, 0, 0))
    P.box((-0.3, 0.38, 0.45), (2.2, 0.42, 0.05), "wood", bevel=0.01)                     # bench
    for x in (-1.2, 0.6):
        P.box((x, 0.38, 0.22), (0.06, 0.36, 0.44), "metal_dark")
    P.box((-0.3, 0.58, 0.72), (2.2, 0.04, 0.32), "wood", bevel=0.01)
    P.cyl((2.1, -0.55, 1.5), 0.04, 3.0, "metal_galv", segs=10)                          # route pole
    P.box((2.1, -0.58, 2.75), (0.42, 0.04, 0.42), "paint_white", bevel=0.01)
    P.label((2.1, -0.601, 2.75), (0.38, 0.38), "label:RouteSign:CITY LINE\\n14|ffffff|1f4f9c|256x256")
    P.col_box((0, 0.66, 1.25), (3.6, 0.1, 2.5))
    P.col_box((-0.3, 0.4, 0.4), (2.2, 0.5, 0.8))
    P.col_box((0, 0.05, 2.48), (3.7, 1.55, 0.14))


def fence_chainlink(P):
    """3 m chain-link module: posts, top rail, mesh as two-sided card (alpha-free diamond texture
    is a P2 trim item; here the mesh uses galvanized wire strands)."""
    for x in (-1.5, 1.5):
        P.cyl((x, 0, 1.0), 0.03, 2.0, "metal_galv", segs=10)
        P.cyl((x, 0, 2.01), 0.036, 0.03, "metal_galv", segs=10)
    P.tube([(-1.5, 0, 1.95), (1.5, 0, 1.95)], 0.02, "metal_galv", segs=8)
    P.tube([(-1.5, 0, 0.08), (1.5, 0, 0.08)], 0.008, "metal_galv", segs=4)
    # diamond wire mesh: diagonal strands (12 per direction)
    n = 12
    for i in range(n + 1):
        x0 = -1.5 + 3.0 * i / n
        for d in (1, -1):
            run = min(1.87, (1.5 - x0) if d > 0 else (x0 + 1.5))
            if run > 0.05:
                P.tube([(x0, 0, 0.08), (x0 + d * run, 0, 0.08 + run)], 0.0035, "metal_galv", segs=3, closed_ends=False)
    P.col_box((0, 0, 1.0), (3.0, 0.08, 2.0))


def dumpster(P):
    """Commercial front-load dumpster 1.9 x 1.1 x 1.25 m with lids and fork pockets."""
    P.box((0, 0.08, 0.66), (1.9, 1.05, 1.15), "metal_green", bevel=0.03)
    P.box((0, -0.43, 0.42), (1.9, 0.12, 0.70), "metal_green", bevel=0.02, rot=(-0.22, 0, 0))   # sloped front
    for y in (-0.38, 0.30):
        P.box((0, y, 1.27), (1.92, 0.62, 0.035), "plastic_black", bevel=0.01, rot=(0.06, 0, 0))   # lids
    for x in (-0.97, 0.97):
        P.box((x, 0.0, 0.95), (0.08, 0.32, 0.16), "metal_dark", bevel=0.01)                      # fork pockets
    for x in (-0.75, 0.75):
        for y in (-0.35, 0.5):
            P.cyl((x, y, 0.06), 0.06, 0.04, "rubber", segs=12, rot=(0, math.pi / 2, 0))
    P.label((0, -0.505, 0.95), (0.70, 0.18), "label:DumpsterLabel:HOLLOW WASTE CO.|f2f2ea|2a3a2a|512x128", rot=(-0.22 + 0.0, 0, 0))
    P.col_box((0, 0.05, 0.64), (1.95, 1.15, 1.28))


def phone_booth(P):
    """Open payphone stand (1.0 x 0.6 x 2.1 m), steel hood and handset."""
    P.box((0, 0.2, 1.05), (0.10, 0.10, 2.1), "metal_galv", bevel=0.01)
    P.box((0, 0.05, 1.95), (0.9, 0.55, 0.20), "metal_galv", bevel=0.02)
    P.label((0, -0.226, 1.95), (0.84, 0.16), "label:PhoneSign:PAYPHONE|ffffff|1c3f7a|512x96")
    P.box((0, 0.10, 1.35), (0.30, 0.16, 0.48), "metal_dark", bevel=0.02)
    P.box((0, 0.015, 1.40), (0.14, 0.01, 0.18), "chrome")                                    # keypad plate
    P.box((-0.11, 0.0, 1.38), (0.05, 0.05, 0.22), "plastic_black", bevel=0.01)              # handset
    P.tube([(-0.11, 0.02, 1.27), (-0.10, -0.02, 1.15), (-0.05, 0.0, 1.10), (0.0, 0.02, 1.15)], 0.006, "plastic_black", segs=4)
    P.box((0, 0.05, 1.05), (0.5, 0.25, 0.03), "metal_galv")                                  # shelf
    P.col_box((0, 0.15, 1.05), (0.9, 0.5, 2.1))


def newspaper_box(P):
    """Coin-op newspaper vending box (0.5 x 0.45 x 1.05 m on a pedestal)."""
    P.box((0, 0, 0.18), (0.10, 0.10, 0.36), "metal_dark")
    P.box((0, 0, 0.66), (0.50, 0.45, 0.62), "metal_blue", bevel=0.02)
    P.box((0, -0.225, 0.72), (0.40, 0.01, 0.28), "glass")
    P.label((0, -0.2265, 0.92), (0.42, 0.08), "label:PaperLabel:THE HOLLOW HERALD|ffffff|0f2c5c|512x96")
    P.box((0, -0.235, 0.53), (0.16, 0.02, 0.05), "chrome")                                  # handle
    P.box((0.17, -0.235, 0.88), (0.06, 0.02, 0.10), "chrome")                               # coin slot
    P.box((0, 0, 1.0), (0.52, 0.47, 0.04), "metal_blue", bevel=0.01)
    P.col_box((0, 0, 0.51), (0.52, 0.47, 1.02))


def parking_meter(P):
    """Single-space parking meter (1.45 m)."""
    P.cyl((0, 0, 0.55), 0.035, 1.1, "metal_galv", segs=10)
    P.box((0, 0, 1.22), (0.18, 0.12, 0.26), "metal_dark", bevel=0.03)
    P.sphere((0, 0, 1.36), 0.09, "chrome", segs=12, rings=6, scale=(1, 0.65, 0.6), hemi=True)
    P.box((0, -0.061, 1.25), (0.11, 0.005, 0.07), "glass")
    P.label((0, -0.0605, 1.15), (0.12, 0.05), "label:MeterLabel:2 HR|f4f4f4|222222|256x96")
    P.col_box((0, 0, 0.72), (0.2, 0.14, 1.45))


def street_sign(P):
    """Corner street-name sign (3.2 m pole, two crossed blades, fictional street names)."""
    P.cyl((0, 0, 1.6), 0.03, 3.2, "metal_galv", segs=10)
    P.box((0.45, 0, 3.05), (0.9, 0.02, 0.2), "paint_green", bevel=0.005)
    P.label((0.45, -0.011, 3.05), (0.88, 0.18), "label:SignCalloway:CALLOWAY AV|ffffff|0b5d2e|512x112")
    P.label((0.45, 0.011, 3.05), (0.88, 0.18), "label:SignCallowayB:CALLOWAY AV|ffffff|0b5d2e|512x112", rot=(0, 0, math.pi))
    P.box((0, 0.45, 2.82), (0.02, 0.9, 0.2), "paint_green", bevel=0.005)
    P.label((-0.011, 0.45, 2.82), (0.88, 0.18), "label:SignHollow:E HOLLOW BLVD|ffffff|0b5d2e|512x112", rot=(0, 0, -math.pi / 2))
    P.label((0.011, 0.45, 2.82), (0.88, 0.18), "label:SignHollowB:E HOLLOW BLVD|ffffff|0b5d2e|512x112", rot=(0, 0, math.pi / 2))
    P.box((0, -0.02, 2.2), (0.45, 0.02, 0.6), "paint_white", bevel=0.005)
    P.label((0, -0.031, 2.2), (0.42, 0.56), "label:NoParking:NO\\nPARKING\\n7AM-9AM|c0151a|f4f4f0|256x384")
    P.col_box((0, 0, 1.6), (0.08, 0.08, 3.2))


def billboard(P):
    """Roadside billboard 6 x 3 m on a steel column (9 m), catwalk and lamps."""
    P.cyl((0, 0.4, 3.5), 0.25, 7.0, "metal_galv", segs=16)
    P.box((0, 0.4, 7.2), (6.4, 0.5, 0.25), "metal_dark")
    P.box((0, 0.15, 8.6), (6.2, 0.2, 3.2), "metal_dark", bevel=0.03)
    P.label((0, 0.045, 8.6), (6.0, 3.0), "label:BillboardAd:SUNDOWN COLA\\nTaste the coast.|fff4d6|b5361b|1024x512")
    P.box((0, -0.25, 7.0), (6.2, 0.6, 0.05), "metal_galv")                              # catwalk
    P.tube([(-3.1, -0.55, 7.0), (-3.1, -0.55, 7.9), (3.1, -0.55, 7.9), (3.1, -0.55, 7.0)], 0.02, "metal_galv", segs=6)
    for x in (-2.0, 0.0, 2.0):
        P.tube([(x, 0.1, 7.1), (x, -0.6, 7.25)], 0.025, "metal_dark", segs=6)
        P.box((x, -0.65, 7.25), (0.4, 0.2, 0.1), "metal_dark", bevel=0.01)
        P.box((x, -0.65, 7.195), (0.34, 0.16, 0.01), "light_panel")
    P.col_box((0, 0.4, 3.5), (0.55, 0.55, 7.0))
    P.col_box((0, 0.15, 8.6), (6.2, 0.3, 3.2))


def bush(P):
    """Shrub cluster ~1.6 m: stacked double-sided leaf cards around a woody core (no alpha needed
    at street distance; P6 replaces it with the vegetation generator's alpha cards)."""
    P.cyl((0, 0, 0.2), 0.05, 0.4, "wood_creosote", segs=6)
    k = 0
    for ring, (r, z, n) in enumerate(((0.55, 0.45, 7), (0.45, 0.85, 6), (0.25, 1.2, 4))):
        for i in range(n):
            a = i * TAU / n + ring * 0.4
            P.sphere((math.cos(a) * r, math.sin(a) * r, z), 0.42 - 0.06 * ring, "foliage", segs=8, rings=5,
                     scale=(1.0, 1.0, 0.8))
            k += 1
    P.sphere((0, 0, 1.25), 0.35, "foliage", segs=8, rings=5)
    P.col_box((0, 0, 0.75), (1.6, 1.6, 1.5))


def power_pole(P):
    """Wooden utility pole 10.5 m, crossarm, insulators, transformer can, cable stubs."""
    P.cyl((0, 0, 5.25), 0.16, 10.5, "wood_creosote", segs=12, radius2=0.12)
    P.box((0, 0, 9.6), (2.4, 0.12, 0.12), "wood_creosote", bevel=0.01)
    for x in (-1.05, -0.35, 0.35, 1.05):
        P.cyl((x, 0, 9.75), 0.04, 0.18, "plastic_grey", segs=8)
        P.tube([(x, -1.5, 9.62), (x, 0, 9.82), (x, 1.5, 9.62)], 0.012, "plastic_black", segs=4)
    P.tube([(-0.9, 0, 9.55), (0, 0, 8.8), (0.9, 0, 9.55)], 0.025, "metal_galv", segs=6)    # braces
    P.cyl((0.0, -0.32, 7.9), 0.22, 0.9, "metal_galv", segs=14)                             # transformer
    P.box((0.0, -0.16, 7.9), (0.12, 0.14, 0.12), "metal_galv")
    P.cyl((0.0, -0.32, 8.37), 0.22, 0.04, "metal_galv", segs=14, radius2=0.18)
    P.box((0, -0.17, 2.4), (0.14, 0.02, 0.2), "paint_yellow")
    P.label((0, -0.181, 2.4), (0.12, 0.18), "label:PoleTag:LAH\\n4471|111111|e6c014|128x192")
    P.col_box((0, 0, 5.25), (0.34, 0.34, 10.5))


# ============================================================ P5 items
def cash_bundle(P):
    """Banded stack of bills (0.156 x 0.066 x 0.03 m) - stylised, no real currency design."""
    P.box((0, 0, 0.015), (0.156, 0.066, 0.03), "label:CashFace:10 000|cfe0c0|3e6b3a|512x256", bevel=0.001, uv="fit")
    P.box((0, 0, 0.015), (0.036, 0.068, 0.032), "label:CashBand:$10 000|5a3a10|e8d6a0|256x128", bevel=0.0008, uv="fit")
    P.col_box((0, 0, 0.015), (0.156, 0.066, 0.03))


def phone(P):
    """Burner smartphone 0.072 x 0.0085 x 0.15 m, standing on its short edge for pick-ups."""
    P.box((0, 0, 0.075), (0.072, 0.0085, 0.15), "plastic_black", bevel=0.004)
    P.box((0, -0.0044, 0.077), (0.064, 0.001, 0.13), "screen")
    P.cyl((0.02, 0.0046, 0.13), 0.006, 0.002, "glass", segs=10, rot=(math.pi / 2, 0, 0))
    P.col_box((0, 0, 0.075), (0.072, 0.009, 0.15))


def gold_bar(P):
    """1 kg-class trapezoid bar 0.25 x 0.07 x 0.045 m."""
    import bmesh as _bm
    before = set(P.bm.faces)
    b = [(-0.125, -0.035, 0), (0.125, -0.035, 0), (0.125, 0.035, 0), (-0.125, 0.035, 0)]
    t = [(-0.11, -0.025, 0.045), (0.11, -0.025, 0.045), (0.11, 0.025, 0.045), (-0.11, 0.025, 0.045)]
    vb = [P.bm.verts.new(p) for p in b]
    vt = [P.bm.verts.new(p) for p in t]
    P.bm.faces.new(vb[::-1])
    P.bm.faces.new(vt)
    for i in range(4):
        j = (i + 1) % 4
        P.bm.faces.new((vb[i], vb[j], vt[j], vt[i]))
    new = [f for f in P.bm.faces if f not in before]
    edges = list({e for f in new for e in f.edges})
    _bm.ops.bevel(P.bm, geom=edges, offset=0.003, segments=2, affect="EDGES", clamp_overlap=True)
    P._tag([f for f in P.bm.faces if f not in before], "gold", smooth=False)
    P.box((0, 0, 0.0452), (0.12, 0.03, 0.0008), "label:GoldStamp:999.9  1 KG|5a3d05|e3b24a|256x64", uv="fit")
    P.col_box((0, 0, 0.0225), (0.25, 0.07, 0.045))


def drug_brick(P):
    """Tape-wrapped contraband brick 0.30 x 0.20 x 0.07 m (stylised package, no markings)."""
    P.box((0, 0, 0.035), (0.30, 0.20, 0.07), "paper_brown", bevel=0.012)
    for x in (-0.09, 0.0, 0.09):
        P.box((x, 0, 0.035), (0.05, 0.204, 0.074), "tape_tan", bevel=0.01)
    P.box((0, 0, 0.035), (0.306, 0.05, 0.078), "tape_tan", bevel=0.01)     # crosses OVER the bands
    P.col_box((0, 0, 0.035), (0.30, 0.20, 0.07))


def duffel(P):
    """Canvas duffel bag 0.65 m long (lying), straps, zip, end caps."""
    mk = P.mark()
    P.lathe([(0.0, -0.33), (0.10, -0.33), (0.16, -0.31), (0.175, -0.25), (0.18, 0.0), (0.175, 0.25),
             (0.16, 0.31), (0.10, 0.33), (0.0, 0.33)], "canvas", segs=16, center=(0, 0, 0))
    # rotate the lathe to lie along X: do it via vertex transform of the new faces
    import mathutils
    rot = mathutils.Matrix.Rotation(math.pi / 2, 4, "Y")

    def lie(co):
        co = rot @ co
        return mathutils.Vector((co.x, co.y * 0.9, co.z * 0.85 + 0.15))
    P.transform_since(mk, lie)
    for x in (-0.18, 0.18):
        P.tube([(x, -0.16, 0.18), (x, -0.12, 0.33), (x, 0.0, 0.40), (x, 0.12, 0.33), (x, 0.16, 0.18)], 0.012, "leather", segs=6)
    P.tube([(-0.3, 0.0, 0.305), (0.3, 0.0, 0.305)], 0.006, "metal_dark", segs=4)
    P.col_box((0, 0, 0.15), (0.66, 0.3, 0.3))


def barrel(P):
    """55-gallon steel drum (0.58 m dia, 0.88 m) with rolling hoops and bungs."""
    prof = [(0.28, 0.0), (0.29, 0.01), (0.29, 0.02), (0.282, 0.03), (0.282, 0.27), (0.292, 0.29), (0.282, 0.31),
            (0.282, 0.57), (0.292, 0.59), (0.282, 0.61), (0.282, 0.85), (0.29, 0.86), (0.29, 0.875), (0.28, 0.88)]
    P.lathe(prof, "metal_rust", segs=24, cap_top=False)
    P.cyl((0, 0, 0.865), 0.27, 0.01, "metal_rust", segs=24)
    P.cyl((0.16, 0, 0.875), 0.03, 0.012, "metal_dark", segs=8)
    P.cyl((-0.17, 0.05, 0.875), 0.018, 0.012, "metal_dark", segs=8)
    P.col_box((0, 0, 0.44), (0.58, 0.58, 0.88))


def pallet(P):
    """EUR pallet 1.2 x 0.8 x 0.144 m: 5 top boards, 3 stringer boards, 9 blocks, 3 bottom boards."""
    for x, w in ((-0.5375, 0.145), (-0.27, 0.10), (0.0, 0.145), (0.27, 0.10), (0.5375, 0.145)):
        P.box((x, 0, 0.133), (w, 0.8, 0.022), "wood_worn", bevel=0.003)
    for y, wy in ((-0.3275, 0.145), (0.0, 0.145), (0.3275, 0.145)):
        P.box((0, y, 0.111), (1.2, wy, 0.022), "wood_worn", bevel=0.003)
        for x, wx in ((-0.5275, 0.145), (0.0, 0.145), (0.5275, 0.145)):
            P.box((x, y, 0.0585), (wx, wy, 0.078), "wood_worn", bevel=0.004)
        P.box((0, y, 0.0098), (1.2, wy, 0.0195), "wood_worn", bevel=0.003)
    P.col_box((0, 0, 0.072), (1.2, 0.8, 0.144))


def toolbox(P):
    """Steel cantilever toolbox 0.5 x 0.22 x 0.24 m."""
    P.box((0, 0, 0.10), (0.5, 0.22, 0.20), "paint_red", bevel=0.008)
    P.box((0, 0, 0.215), (0.51, 0.23, 0.03), "paint_red", bevel=0.006)
    P.tube([(-0.12, 0, 0.23), (-0.12, 0, 0.29), (0.12, 0, 0.29), (0.12, 0, 0.23)], 0.008, "plastic_black", segs=6)
    for x in (-0.2, 0.2):
        P.box((x, -0.114, 0.19), (0.04, 0.012, 0.03), "chrome", bevel=0.002)
    P.col_box((0, 0, 0.12), (0.5, 0.22, 0.24))


def workbench(P):
    """Garage workbench 2.0 x 0.75 x 0.9 m: butcher-block top, steel frame, shelf, vise."""
    P.box((0, 0, 0.88), (2.0, 0.75, 0.05), "wood", bevel=0.006)
    for x in (-0.94, 0.94):
        for y in (-0.33, 0.33):
            P.box((x, y, 0.43), (0.05, 0.05, 0.86), "metal_dark", bevel=0.004)
    P.box((0, 0, 0.18), (1.9, 0.65, 0.03), "plywood")
    for y in (-0.33, 0.33):
        P.box((0, y, 0.78), (1.88, 0.04, 0.06), "metal_dark")
    P.box((0, 0.36, 1.25), (2.0, 0.03, 0.7), "plywood")                       # pegboard
    P.box((0.7, -0.33, 0.96), (0.2, 0.12, 0.10), "paint_blue", bevel=0.01)   # vise
    P.tube([(0.7, -0.40, 0.96), (0.7, -0.48, 0.96)], 0.008, "chrome", segs=6)
    P.col_box((0, 0, 0.45), (2.0, 0.75, 0.9))


# ============================================================ P5 armor (pickup + wearable reference)
def _vest(P, plate_mat, depth_front, extra):
    """Front + back panels (neck scoop), cummerbund round the waist, shoulder straps: the arm
    openings stay open, so it reads as a vest and fits the 53-bone torso (chest ~0.41 m wide)."""
    rx, ry_f, ry_b = 0.205, depth_front, 0.135
    a_f0, a_f1 = math.radians(-160), math.radians(-20)       # front panel arc (-Y side)
    a_b0, a_b1 = math.radians(25), math.radians(155)
    P.shell_arc(a_f0, a_f1, rx, ry_f, 0.0, 0.44, 0.016, plate_mat, segs=12, top_dip=0.07)
    P.shell_arc(a_b0, a_b1, rx, ry_b, 0.0, 0.47, 0.016, plate_mat, segs=12, top_dip=0.03)
    for a0, a1 in ((math.radians(-25), math.radians(30)), (math.radians(150), math.radians(205))):   # cummerbund
        P.shell_arc(a0, a1, rx + 0.004, ry_b + 0.004, 0.03, 0.22, 0.012, "ballistic", segs=6, ry_front=ry_f + 0.004)
    for x in (-0.1, 0.1):                                                        # shoulder straps
        P.tube([(x, -ry_f + 0.02, 0.36), (x, -ry_f * 0.6, 0.52), (x, 0.0, 0.565), (x, ry_b * 0.6, 0.52), (x, ry_b - 0.01, 0.42)], 0.02, "ballistic", segs=6)
    extra(P)
    P.col_box((0, 0, 0.29), (0.44, 0.34, 0.58))


def vest_light(P):
    """Concealable soft armor vest (absorb 0.35, 50 points in combat.json)."""
    _vest(P, "ballistic", 0.15, lambda P: P.label((0, -0.152, 0.33), (0.16, 0.05), "label:VestTag:LEVEL IIIA|d8d8d0|1a1a1a|256x80"))


def vest_heavy(P):
    """Plate carrier with front/back plates, pouches and collar (absorb 0.55, 120 points)."""
    def extra(P):
        P.box((0, -0.175, 0.27), (0.27, 0.035, 0.33), "plastic_olive", bevel=0.012)      # front plate bag
        P.box((0, 0.155, 0.27), (0.27, 0.03, 0.33), "plastic_olive", bevel=0.012)
        for x in (-0.09, 0.0, 0.09):                                                       # mag pouches
            P.box((x, -0.205, 0.17), (0.08, 0.04, 0.14), "canvas", bevel=0.008)
            P.box((x, -0.209, 0.245), (0.082, 0.045, 0.02), "canvas", bevel=0.004)
        P.box((0.14, -0.195, 0.33), (0.07, 0.04, 0.10), "canvas", bevel=0.008)            # radio pouch
        P.tube([(-0.15, -0.05, 0.47), (-0.08, -0.16, 0.50), (0.08, -0.16, 0.50), (0.15, -0.05, 0.47)], 0.03, "ballistic", segs=6)
        P.label((0, -0.193, 0.38), (0.18, 0.05), "label:CarrierTag:LEVEL IV|d8d8d0|2a2f22|256x80")
    _vest(P, "ballistic", 0.16, extra)


def helmet(P):
    """Ballistic helmet (high cut), rails, NVG shroud, pads, chinstrap. Pickup + head attachment."""
    P.sphere((0, 0, 0.0), 0.125, "plastic_olive", segs=20, rings=10, scale=(1.0, 1.12, 0.92), hemi=True)
    import mathutils
    mk = P.mark()
    P.lathe([(0.122, -0.004), (0.13, 0.0), (0.13, 0.012), (0.122, 0.016), (0.122, -0.004)], "rubber", segs=20,
            cap_top=False, cap_bottom=False)
    P.transform_since(mk, lambda co: mathutils.Vector((co.x, co.y * 1.12, co.z)))     # match the shell's ellipse
    for side in (-1, 1):
        P.box((side * 0.123, 0.0, 0.035), (0.012, 0.11, 0.022), "plastic_black", bevel=0.003)     # ARC rails
    P.box((0, -0.135, 0.06), (0.04, 0.012, 0.03), "plastic_black", bevel=0.003)                  # NVG shroud
    P.tube([(-0.11, 0.02, 0.0), (-0.09, 0.0, -0.09), (0.0, -0.03, -0.12), (0.09, 0.0, -0.09), (0.11, 0.02, 0.0)], 0.006, "ballistic", segs=4)
    P.col_box((0, 0, 0.04), (0.26, 0.29, 0.16))


# ============================================================ registry
# id: (recipe, Blender/Source category)
RECIPES = {
    "SM_LA_Road_Intersection": (road_intersection, "Environment/LA"),
    "SM_LA_Road_Crosswalk": (road_crosswalk, "Environment/LA"),
    "SM_LA_TrafficLight": (traffic_light, "Environment/LA"),
    "SM_LA_Hydrant": (hydrant, "Environment/LA"),
    "SM_LA_TrashCan": (trash_can, "Environment/LA"),
    "SM_LA_BusStop": (bus_stop, "Environment/LA"),
    "SM_LA_Fence_Chainlink": (fence_chainlink, "Environment/LA"),
    "SM_LA_Dumpster": (dumpster, "Environment/LA"),
    "SM_LA_PhoneBooth": (phone_booth, "Environment/LA"),
    "SM_LA_NewspaperBox": (newspaper_box, "Environment/LA"),
    "SM_LA_ParkingMeter": (parking_meter, "Environment/LA"),
    "SM_LA_StreetSign": (street_sign, "Environment/LA"),
    "SM_LA_Billboard": (billboard, "Environment/LA"),
    "SM_LA_Bush": (bush, "Environment/LA"),
    "SM_LA_PowerPole": (power_pole, "Environment/LA"),
    "SM_Prop_CashBundle": (cash_bundle, "Props"),
    "SM_Prop_Phone": (phone, "Props"),
    "SM_Prop_GoldBar": (gold_bar, "Props"),
    "SM_Prop_DrugBrick": (drug_brick, "Props"),
    "SM_Prop_Duffel": (duffel, "Props"),
    "SM_Prop_Barrel": (barrel, "Props"),
    "SM_Prop_Pallet": (pallet, "Props"),
    "SM_Prop_Toolbox": (toolbox, "Props"),
    "SM_Prop_Workbench": (workbench, "Props"),
    "SM_Prop_Vest_Light": (vest_light, "Props"),
    "SM_Prop_Vest_Heavy": (vest_heavy, "Props"),
    "SM_Prop_Helmet_Tactical": (helmet, "Props"),
}
