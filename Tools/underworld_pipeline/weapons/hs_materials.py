"""Bake-source (high-poly) materials for hard-surface weapons.

Each material exposes labelled nodes ALBEDO / ROUGH / METAL / AO that the baker routes into an Emission
shader (selected-to-active EMIT bakes), plus a Principled BSDF with bump for the tangent-space normal bake
(Cycles bakes the shading normal, so stippling/micro texture from bump nodes ends up in the normal map).
Edge wear = convex-curvature mask from the Cycles Bevel node: 1 - dot(bevelled normal, true normal),
broken up with noise so it reads as holster/handling wear, not an outline.
Finishes (spec "finishes"): black-nitride / blued steel for slide + barrel, glass-filled polymer for the frame
with a stippled grip zone (object-space mask, see stipple_zone).
"""
import bpy


def _n(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def _maprange(nt, src, a, b, to_min=0.0, to_max=1.0, smooth=True):
    m = _n(nt, "ShaderNodeMapRange", interpolation_type="SMOOTHSTEP" if smooth else "LINEAR", clamp=True)
    m.inputs["From Min"].default_value = a
    m.inputs["From Max"].default_value = b
    m.inputs["To Min"].default_value = to_min
    m.inputs["To Max"].default_value = to_max
    nt.links.new(src, m.inputs["Value"])
    return m.outputs["Result"]


def _mul(nt, a, b):
    m = _n(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    for i, s in enumerate((a, b)):
        if isinstance(s, (int, float)):
            m.inputs[i].default_value = s
        else:
            nt.links.new(s, m.inputs[i])
    return m.outputs[0]


def make(name, base, rough, metal, wear_col=None, wear_rough=None, wear_metal=None, wear_gain=40.0,
         grain=0.06, micro=None, stipple=None, ao_dist=0.010):
    """micro: dict(scale, strength) fine noise bump; stipple: dict(scale, strength, zone=(zmin,zmax,ymin), rough, base)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    L = nt.links.new
    out = _n(nt, "ShaderNodeOutputMaterial")
    bs = _n(nt, "ShaderNodeBsdfPrincipled")
    L(bs.outputs[0], out.inputs[0])
    geo = _n(nt, "ShaderNodeNewGeometry")
    tc = _n(nt, "ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    # ---- edge wear (convex curvature)
    bev = _n(nt, "ShaderNodeBevel", samples=16)
    bev.inputs["Radius"].default_value = 0.0007
    dot = _n(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    L(bev.outputs[0], dot.inputs[0])
    L(geo.outputs["Normal"], dot.inputs[1])
    inv = _n(nt, "ShaderNodeMath", operation="SUBTRACT")
    inv.inputs[0].default_value = 1.0
    L(dot.outputs["Value"], inv.inputs[1])
    curv = _maprange(nt, inv.outputs[0], 0.04, 0.04 + 6.0 / wear_gain, smooth=False)
    nz = _n(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 700.0
    nz.inputs["Detail"].default_value = 6.0
    L(obj, nz.inputs["Vector"])
    wear = _mul(nt, curv, _maprange(nt, nz.outputs["Fac"], 0.42, 0.62))
    # ---- fine grain variation
    gn = _n(nt, "ShaderNodeTexNoise")
    gn.inputs["Scale"].default_value = 2200.0
    gn.inputs["Detail"].default_value = 3.0
    L(obj, gn.inputs["Vector"])
    gmul = _maprange(nt, gn.outputs["Fac"], 0.3, 0.7, 1.0 - grain, 1.0 + grain, smooth=False)
    # stipple zone mask (object space; parts are modelled in final coordinates)
    zone = None
    if stipple:
        sep = _n(nt, "ShaderNodeSeparateXYZ")
        L(obj, sep.inputs[0])
        zmin, zmax, ymin = stipple["zone"]
        zone = _mul(nt, _maprange(nt, sep.outputs["Z"], zmin, zmin + 0.0018),
                    _maprange(nt, sep.outputs["Z"], zmax, zmax - 0.0018))
        zone = _mul(nt, zone, _maprange(nt, sep.outputs["Y"], ymin, ymin + 0.0015))
    # ---- albedo
    basec = _n(nt, "ShaderNodeVectorMath", operation="SCALE")
    basec.inputs[0].default_value = base
    L(gmul, basec.inputs["Scale"])
    alb_src = basec.outputs[0]
    if zone is not None:
        zmix = _n(nt, "ShaderNodeMix", data_type="RGBA")
        L(zone, zmix.inputs["Factor"])
        L(alb_src, zmix.inputs[6])
        zmix.inputs[7].default_value = (*stipple.get("base", base), 1.0)
        alb_src = zmix.outputs[2]
    alb = _n(nt, "ShaderNodeMix", data_type="RGBA", label="ALBEDO")
    L(wear, alb.inputs["Factor"])
    L(alb_src, alb.inputs[6])
    alb.inputs[7].default_value = (*(wear_col or base), 1.0)
    # ---- roughness
    rbase = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
    rbase.inputs[0].default_value = rough
    L(gmul, rbase.inputs[1])
    r_src = rbase.outputs[0]
    if zone is not None:
        rz = _n(nt, "ShaderNodeMix", data_type="FLOAT")
        L(zone, rz.inputs["Factor"])
        L(r_src, rz.inputs[2])
        rz.inputs[3].default_value = stipple.get("rough", rough)
        r_src = rz.outputs[0]
    rgh = _n(nt, "ShaderNodeMix", data_type="FLOAT", label="ROUGH")
    L(wear, rgh.inputs["Factor"])
    L(r_src, rgh.inputs[2])
    rgh.inputs[3].default_value = wear_rough if wear_rough is not None else rough
    met = _n(nt, "ShaderNodeMix", data_type="FLOAT", label="METAL")
    L(wear, met.inputs["Factor"])
    met.inputs[2].default_value = metal
    met.inputs[3].default_value = wear_metal if wear_metal is not None else metal
    L(alb.outputs[2], bs.inputs["Base Color"])
    L(rgh.outputs[0], bs.inputs["Roughness"])
    L(met.outputs[0], bs.inputs["Metallic"])
    # ---- normal detail: micro noise + stipple (voronoi dimples) chained
    nrm = None
    if micro:
        tx = _n(nt, "ShaderNodeTexNoise")
        tx.inputs["Scale"].default_value = micro["scale"]
        tx.inputs["Detail"].default_value = 8.0
        L(obj, tx.inputs["Vector"])
        bp = _n(nt, "ShaderNodeBump")
        bp.inputs["Strength"].default_value = micro["strength"]
        bp.inputs["Distance"].default_value = micro.get("distance", 0.0001)
        L(tx.outputs["Fac"], bp.inputs["Height"])
        nrm = bp.outputs["Normal"]
    if stipple:
        vo = _n(nt, "ShaderNodeTexVoronoi", feature="F1", distance="EUCLIDEAN")
        vo.inputs["Scale"].default_value = stipple["scale"]
        vo.inputs["Randomness"].default_value = 0.35
        L(obj, vo.inputs["Vector"])
        # rounded pyramids: clamp the distance so cell centres read as raised domes
        hgt = _maprange(nt, vo.outputs["Distance"], 0.0, 0.62, 1.0, 0.0)
        bp = _n(nt, "ShaderNodeBump")
        bp.inputs["Distance"].default_value = stipple.get("distance", 0.00035)
        L(_mul(nt, zone, stipple["strength"]), bp.inputs["Strength"])
        L(hgt, bp.inputs["Height"])
        if nrm is not None:
            L(nrm, bp.inputs["Normal"])
        nrm = bp.outputs["Normal"]
    if nrm is not None:
        L(nrm, bs.inputs["Normal"])
    ao = _n(nt, "ShaderNodeAmbientOcclusion", samples=16, label="AO", only_local=True)
    ao.inputs["Distance"].default_value = ao_dist
    m["bake_sockets"] = True
    return m


def bake_socket(mat, key):
    lab = {"albedo": "ALBEDO", "rough": "ROUGH", "metal": "METAL", "ao": "AO"}[key]
    n = next(n for n in mat.node_tree.nodes if n.label == lab)
    if key == "ao":
        return n.outputs["AO"]
    return n.outputs[2] if key == "albedo" else n.outputs[0]


def library(spec):
    """Finish library; colours are linear RGB. Spec 'finishes' may override base/rough per key."""
    f = spec.get("finishes", {})

    def g(k, key, dflt):
        return tuple(f.get(k, {}).get(key, dflt)) if isinstance(dflt, tuple) else f.get(k, {}).get(key, dflt)
    stip = spec.get("stipple_zone", [-0.0605, -0.0035, -0.0390])
    steel = g("slide", "base", (0.030, 0.031, 0.034))
    return {
        # black nitride / blued slide: satin, faint micro texture, edges worn to bare steel
        "steel": make("HP_SlideSteel", steel, g("slide", "rough", 0.34), 1.0, wear_col=(0.36, 0.36, 0.37), wear_rough=0.20,
                      wear_metal=1.0, wear_gain=34.0, micro={"scale": 5000.0, "strength": 0.04}),
        "barrel": make("HP_Barrel", g("barrel", "base", (0.055, 0.056, 0.060)), g("barrel", "rough", 0.26), 1.0,
                       wear_col=(0.50, 0.50, 0.51), wear_rough=0.16, wear_gain=30.0),
        "bore": make("HP_Bore", (0.015, 0.015, 0.016), 0.45, 1.0, grain=0.0),
        "magsteel": make("HP_MagSteel", (0.040, 0.040, 0.043), 0.40, 1.0, wear_col=(0.35, 0.35, 0.36), wear_rough=0.22),
        # glass-filled polymer frame: matte, very fine noise; grip zone gets raised stipple pyramids
        "polymer": make("HP_Polymer", g("frame", "base", (0.024, 0.024, 0.026)), g("frame", "rough", 0.58), 0.0,
                        wear_col=(0.050, 0.050, 0.052), wear_rough=0.42, wear_metal=0.0, wear_gain=22.0,
                        micro={"scale": 9000.0, "strength": 0.06},
                        stipple={"scale": 1350.0, "strength": 0.85, "zone": stip, "rough": 0.80,
                                 "base": (0.030, 0.030, 0.032)}),
        "polymer_plain": make("HP_PolymerPlain", g("frame", "base", (0.024, 0.024, 0.026)), g("frame", "rough", 0.58), 0.0,
                              wear_col=(0.050, 0.050, 0.052), wear_rough=0.42, wear_metal=0.0, wear_gain=22.0,
                              micro={"scale": 9000.0, "strength": 0.06}),
        "white": make("HP_SightDot", (0.78, 0.78, 0.74), 0.5, 0.0, grain=0.02),
    }
