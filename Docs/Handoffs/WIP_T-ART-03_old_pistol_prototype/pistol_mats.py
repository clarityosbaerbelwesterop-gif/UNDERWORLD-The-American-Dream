"""High-poly bake materials for WPN_Pistol_01 (Bot 2). Each material exposes three value sockets
(albedo / roughness / metallic) that the baker routes into an Emission shader, plus a Principled BSDF
(with bump) for close-up preview renders and the tangent-space normal bake.
Edge wear = curvature mask from the Cycles Bevel node: 1 - dot(bevelled normal, true normal)."""
import bpy


def _n(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def make(name, base, rough, metal, wear_col=None, wear_rough=None, wear_metal=None, wear_gain=40.0,
         grain=0.08, bump=None):
    """bump: dict(kind='stipple'|'brushed'|'cast', scale=..., strength=...)"""
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
    # curvature (convex edges) via bevel normal
    bev = _n(nt, "ShaderNodeBevel", samples=16)
    bev.inputs["Radius"].default_value = 0.0007
    dot = _n(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    L(bev.outputs[0], dot.inputs[0])
    L(geo.outputs["Normal"], dot.inputs[1])
    inv = _n(nt, "ShaderNodeMath", operation="SUBTRACT")
    inv.inputs[0].default_value = 1.0
    L(dot.outputs["Value"], inv.inputs[1])
    # flat faces give 1-dot ~ 0 (+ sampling noise); only real convex edges pass the window
    gain = _n(nt, "ShaderNodeMapRange")
    gain.inputs["From Min"].default_value = 0.04
    gain.inputs["From Max"].default_value = 0.04 + 6.0 / wear_gain
    L(inv.outputs[0], gain.inputs["Value"])
    # break the wear mask up with noise so it reads as handling wear, not an outline
    nz = _n(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 900.0
    nz.inputs["Detail"].default_value = 6.0
    L(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = _n(nt, "ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.45
    ramp.inputs["From Max"].default_value = 0.62
    L(nz.outputs["Fac"], ramp.inputs["Value"])
    wear = _n(nt, "ShaderNodeMath", operation="MULTIPLY", use_clamp=True)
    L(gain.outputs["Result"], wear.inputs[0])
    L(ramp.outputs["Result"], wear.inputs[1])
    # fine grain variation of the base colour/roughness
    gn = _n(nt, "ShaderNodeTexNoise")
    gn.inputs["Scale"].default_value = 2500.0
    gn.inputs["Detail"].default_value = 3.0
    L(tc.outputs["Object"], gn.inputs["Vector"])
    gmix = _n(nt, "ShaderNodeMapRange")
    gmix.inputs["To Min"].default_value = 1.0 - grain
    gmix.inputs["To Max"].default_value = 1.0 + grain
    L(gn.outputs["Fac"], gmix.inputs["Value"])
    basec = _n(nt, "ShaderNodeVectorMath", operation="SCALE")
    basec.inputs[0].default_value = base
    L(gmix.outputs["Result"], basec.inputs["Scale"])
    alb = _n(nt, "ShaderNodeMix", data_type="RGBA", label="ALBEDO")
    L(wear.outputs[0], alb.inputs["Factor"])
    L(basec.outputs[0], alb.inputs[6])
    alb.inputs[7].default_value = (*(wear_col or base), 1.0)
    rgh = _n(nt, "ShaderNodeMix", data_type="FLOAT", label="ROUGH")
    L(wear.outputs[0], rgh.inputs["Factor"])
    rbase = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
    rbase.inputs[0].default_value = rough
    L(gmix.outputs["Result"], rbase.inputs[1])
    L(rbase.outputs[0], rgh.inputs[2])
    rgh.inputs[3].default_value = wear_rough if wear_rough is not None else rough
    met = _n(nt, "ShaderNodeMix", data_type="FLOAT", label="METAL")
    L(wear.outputs[0], met.inputs["Factor"])
    met.inputs[2].default_value = metal
    met.inputs[3].default_value = wear_metal if wear_metal is not None else metal
    L(alb.outputs[2], bs.inputs["Base Color"])
    L(rgh.outputs[0], bs.inputs["Roughness"])
    L(met.outputs[0], bs.inputs["Metallic"])
    if bump:
        if bump["kind"] == "stipple":
            tx = _n(nt, "ShaderNodeTexVoronoi", feature="F1", distance="EUCLIDEAN")
            tx.inputs["Scale"].default_value = bump["scale"]
            tx.inputs["Randomness"].default_value = 0.8
            src = tx.outputs["Distance"]
        else:
            tx = _n(nt, "ShaderNodeTexNoise")
            tx.inputs["Scale"].default_value = bump["scale"]
            tx.inputs["Detail"].default_value = 8.0
            src = tx.outputs["Fac"]
        L(tc.outputs["Object"], tx.inputs["Vector"])
        bp = _n(nt, "ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump["strength"]
        bp.inputs["Distance"].default_value = bump.get("distance", 0.0003)
        if bump.get("invert"):
            bp.invert = True
        L(src, bp.inputs["Height"])
        L(bp.outputs["Normal"], bs.inputs["Normal"])
    ao = _n(nt, "ShaderNodeAmbientOcclusion", samples=16, label="AO")
    ao.inputs["Distance"].default_value = 0.012
    m["bake_sockets"] = True
    return m


def bake_socket(mat, key):
    """Return the output socket for 'albedo' | 'rough' | 'metal'."""
    lab = {"albedo": "ALBEDO", "rough": "ROUGH", "metal": "METAL", "ao": "AO"}[key]
    n = next(n for n in mat.node_tree.nodes if n.label == lab)
    if key == "ao":
        return n.outputs["AO"]
    return n.outputs[2] if key == "albedo" else n.outputs[0]


def library():
    steel = (0.040, 0.041, 0.044)          # black nitride slide
    return {
        "steel": make("HP_Steel", steel, 0.36, 1.0, wear_col=(0.42, 0.42, 0.43), wear_rough=0.22, wear_metal=1.0,
                      bump={"kind": "noise", "scale": 4000.0, "strength": 0.05}),
        "barrel": make("HP_Barrel", (0.20, 0.20, 0.21), 0.28, 1.0, wear_col=(0.55, 0.55, 0.56), wear_rough=0.18, wear_metal=1.0),
        "magsteel": make("HP_MagSteel", (0.055, 0.055, 0.058), 0.45, 1.0, wear_col=(0.40, 0.40, 0.41), wear_rough=0.25),
        "polymer": make("HP_Polymer", (0.020, 0.020, 0.022), 0.58, 0.0, wear_col=(0.055, 0.055, 0.058), wear_rough=0.45,
                        wear_metal=0.0, wear_gain=25.0, bump={"kind": "noise", "scale": 6000.0, "strength": 0.08}),
        "stipple": make("HP_Stipple", (0.024, 0.024, 0.026), 0.80, 0.0, wear_col=(0.05, 0.05, 0.052), wear_rough=0.6,
                        wear_metal=0.0, wear_gain=25.0,
                        bump={"kind": "stipple", "scale": 1400.0, "strength": 0.9, "distance": 0.0004, "invert": True}),
        "white": make("HP_White", (0.80, 0.80, 0.76), 0.5, 0.0, grain=0.02),
    }
