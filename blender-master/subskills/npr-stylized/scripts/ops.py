"""npr-stylized ops: toon materials (light-direction bands that render in any engine, or
Shader-to-RGB bands for EEVEE), inverted-hull outlines, Line Art (Grease Pencil) and Freestyle
lines, painterly and poster compositor looks (Kuwahara, posterize, glare, colour balance) - plus
checks that the setup is complete and the render really reads as flat bands."""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

import bm_checks
import bm_compositor
import bm_scene


def _mat(name):
    if not name.startswith("MAT_"):
        name = "MAT_" + name
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.node_tree.nodes.clear()
    return m


def _ramp(nt, colors, positions, loc):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.location = loc
    r.color_ramp.interpolation = "CONSTANT"
    els = r.color_ramp.elements
    while len(els) < len(colors):
        els.new(0.5)
    for e, c, p in zip(els, colors, positions):
        e.position = p
        e.color = (*c[:3], 1.0)
    return r


def toon_material(ctx, name, color=(0.8, 0.3, 0.2), shadow=None, steps=2, mode="any", light_dir=(-0.4, -0.6, 0.7),
                  rim=0.0, rim_color=(1, 1, 1), spec=0.0, targets=None, threshold=0.5):
    """Flat cel shading. mode "any": bands from a fixed light direction (renders the same in
    Cycles and EEVEE, ignores scene lights); mode "eevee": bands from real lights via Shader to
    RGB (EEVEE only). ``steps`` 2-4 bands from ``shadow`` to ``color``; optional rim and spec."""
    m = _mat(name)
    nt = m.node_tree
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    lit = Vector(color[:3])
    sh = Vector(shadow[:3]) if shadow else lit * 0.45
    cols = [tuple(sh.lerp(lit, i / (steps - 1))) for i in range(steps)]
    pos = [0.0] + [threshold + (i - 1) * (1 - threshold) / max(steps - 1, 1) for i in range(1, steps)]
    ramp = _ramp(nt, cols, pos, (100, 0))
    if mode == "eevee":
        d = nt.nodes.new("ShaderNodeBsdfDiffuse")
        d.location = (-400, 0)
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        s2r.location = (-200, 0)
        nt.links.new(d.outputs[0], s2r.inputs[0])
        nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        geo.location = (-600, 0)
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "DOT_PRODUCT"
        vm.location = (-400, 0)
        vm.inputs[1].default_value = Vector(light_dir).normalized()
        nt.links.new(geo.outputs["Normal"], vm.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.location = (-200, 0)
        mr.inputs["From Min"].default_value = -1.0
        nt.links.new(vm.outputs["Value"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    col_out = ramp.outputs["Color"]
    if rim > 0:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.location = (100, -300)
        lw.inputs["Blend"].default_value = 0.5
        st = nt.nodes.new("ShaderNodeMath")
        st.operation = "GREATER_THAN"
        st.inputs[1].default_value = 1 - rim   # rim = width of the edge band (0-1)
        st.location = (300, -300)
        nt.links.new(lw.outputs["Facing"], st.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.location = (500, 0)
        nt.links.new(st.outputs[0], mx.inputs[0])
        nt.links.new(col_out, mx.inputs[6])
        mx.inputs[7].default_value = (*rim_color, 1)
        col_out = mx.outputs[2]
    em = nt.nodes.new("ShaderNodeEmission")
    em.location = (700, 0)
    nt.links.new(col_out, em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m["npr"] = f"toon {mode} {steps} steps"
    if targets:
        for o in bm_checks.select(targets, mesh_only=False):
            if o.type in {"MESH", "CURVES"}:
                o.data.materials.clear()
                o.data.materials.append(m)
    return f"{m.name}: {steps}-band toon ({mode})"


def outline(ctx, targets="GEO_", thickness=0.01, color=(0.02, 0.02, 0.03)):
    """Inverted-hull outline: a flipped Solidify shell with a black material whose camera-facing
    side is transparent (Backfacing), so only the silhouette rim shows. Works in every engine."""
    m = bpy.data.materials.get("MAT_npr_outline")
    if m is None:
        m = _mat("npr_outline")
        nt = m.node_tree
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*color, 1)
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
        nt.links.new(em.outputs[0], mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        m.use_backface_culling = False
        m["npr"] = "outline"
    objs = bm_checks.select(targets)
    for o in objs:
        if m.name not in [x.name for x in o.data.materials if x]:
            o.data.materials.append(m)
        idx = [x.name if x else None for x in o.data.materials].index(m.name)
        mod = o.modifiers.get("NPR_outline") or o.modifiers.new("NPR_outline", "SOLIDIFY")
        mod.thickness = abs(thickness)
        mod.offset = 1.0            # grow outward along the normals
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.material_offset = idx
        mod.material_offset_rim = idx
    return f"outline {thickness} m on {len(objs)} objects"


def line_art(ctx, name="FX_lineart", radius=0.002, color=(0.02, 0.02, 0.03), crease=140.0, source=None):
    """Grease Pencil Line Art over the scene (or one collection ``source``): contours, creases,
    intersections as strokes of ``radius`` metres (Grease Pencil v3 uses radius, not pixel
    thickness). Rendered as an overlay layer."""
    bm_scene.remove_object(name)
    bpy.ops.object.grease_pencil_add(type="LINEART_SCENE" if source is None else "LINEART_COLLECTION")
    o = bpy.context.object
    o.name = name
    mod = next(m for m in o.modifiers if m.type == "LINEART")
    if source is not None:
        mod.source_type = "COLLECTION"
        mod.source_collection = bpy.data.collections[source]
    mod.radius = radius
    mod.crease_threshold = math.radians(crease)
    for mat in o.data.materials:
        if mat and mat.grease_pencil:
            mat.grease_pencil.color = (*color, 1)
    bm_scene.link_exclusive(o)
    return f"{name}: line art radius {radius} m"


def freestyle(ctx, thickness=1.5, crease=134.0, color=(0.02, 0.02, 0.03), silhouette=True, border=True):
    """Freestyle lines (renders in Cycles and EEVEE, slower, good for technical/ink looks)."""
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = thickness
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(crease)
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new("NPR_lines")
    ls.select_by_visibility = True
    ls.select_silhouette = silhouette
    ls.select_border = border
    ls.select_crease = True
    ls.linestyle.color = color
    ls.linestyle.thickness = thickness
    return f"freestyle {thickness}px"


def painterly(ctx, size=6, kind="Anisotropic", glare=0.0, saturation=1.1, posterize=0):
    """Compositor brush look: Kuwahara (anisotropic follows edges like strokes), optional
    posterize bands, glare bloom and a saturation lift, inserted before the output."""
    tree, rl, out = bm_compositor.ensure_tree()
    src = bm_compositor._feed(tree, out) or rl.outputs["Image"]
    k = tree.nodes.new("CompositorNodeKuwahara")
    k.location = (0, 200)
    k.inputs["Size"].default_value = size
    try:
        k.inputs["Type"].default_value = kind
    except TypeError:
        pass
    tree.links.new(src, k.inputs["Image"])
    last = k.outputs["Image"]
    if posterize:
        p = tree.nodes.new("CompositorNodePosterize")
        p.inputs["Steps"].default_value = posterize
        tree.links.new(last, p.inputs["Image"])
        last = p.outputs["Image"]
    if glare:
        g = tree.nodes.new("CompositorNodeGlare")
        g.inputs["Strength"].default_value = glare
        tree.links.new(last, g.inputs["Image"])
        last = g.outputs["Image"]
    if saturation != 1.0:
        h = tree.nodes.new("CompositorNodeHueSat")
        h.inputs["Saturation"].default_value = saturation
        tree.links.new(last, h.inputs["Image"])
        last = h.outputs["Image"]
    tree.links.new(last, out.inputs["Image"])
    return f"painterly size {size} {kind}" + (f", posterize {posterize}" if posterize else "")


def flat_world(ctx, color=(0.85, 0.82, 0.75), strength=1.0):
    """Plain background colour for toon renders (no environment lighting effect on emission)."""
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("WLD_main")
    sc.world = w
    nt = w.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None) or nt.nodes.new("ShaderNodeBackground")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    sc.view_settings.view_transform = "Standard"   # keep toon colours as picked
    return "flat world, Standard view transform"


@bm_checks.register("npr_setup")
def _npr_setup(ctx, objects="GEO_", need_outline=False):
    bad = {}
    for o in bm_checks.select(objects):
        mats = [m for m in o.data.materials if m]
        toon = any(str(m.get("npr", "")).startswith("toon") for m in mats)
        line = any(m.type == "SOLIDIFY" and m.name == "NPR_outline" for m in o.modifiers)
        if not toon or (need_outline and not line):
            bad[o.name] = {"toon": toon, "outline": line}
    return not bad, bad or "ok", "toon material" + (" and outline" if need_outline else "") + " on every object", ""


@bm_checks.register("npr_flat")
def _npr_flat(ctx, pattern="renders/*.png", levels=24, top=6, min_share=0.6):
    """The render reads as flat bands: the ``top`` most common of ``levels`` luminance buckets
    hold at least ``min_share`` of the pixels (a photoreal render spreads much wider)."""
    import glob
    files = sorted(glob.glob(os.path.join(ctx.out_dir, pattern)))
    if not files:
        return False, None, pattern, "no render"
    res, ok = {}, True
    for f in files:
        img = bpy.data.images.load(f, check_existing=False)
        px = img.pixels[:]
        bpy.data.images.remove(img)
        hist = [0] * levels
        n = 0
        for i in range(0, len(px), 4 * 5):
            lum = 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
            hist[min(levels - 1, int(max(0.0, min(1.0, lum)) * levels))] += 1
            n += 1
        share = sum(sorted(hist, reverse=True)[:top]) / max(n, 1)
        res[os.path.basename(f)] = round(share, 3)
        ok = ok and share >= min_share
    return ok, res, f"top {top}/{levels} luminance buckets >= {min_share}", ""


OPS = {"toon_material": toon_material, "outline": outline, "line_art": line_art, "freestyle": freestyle,
       "painterly": painterly, "flat_world": flat_world}
FIXES = {}
