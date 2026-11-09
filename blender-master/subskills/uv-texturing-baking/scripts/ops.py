"""uv-texturing-baking ops: seams by angle, unwrap (smart, angle-based, conformal, lightmap),
island packing, texel-density report, Cycles texture baking (AO, normal, diffuse colour,
roughness, emit, combined; optionally high -> low) saved as PNG and wired into the material,
plus UV and bake checks."""
from __future__ import annotations

import math
import os

import bmesh
import bpy

import bm_checks
import bm_textures


def _objs(targets):
    objs = bm_checks.select(targets)
    if not objs:
        raise KeyError(f"no mesh objects match {targets!r}")
    return objs


def _edit(objs):
    """Enter edit mode on all ``objs`` together (multi-object editing) and select everything."""
    vl = bpy.context.view_layer
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in vl.objects:
        if o is not None:
            o.select_set(o in objs)
    vl.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")


def _object_mode():
    bpy.ops.object.mode_set(mode="OBJECT")


def mark_seams(ctx, targets="GEO_", angle=60.0, clear=True, material_borders=True):
    """Seams on edges sharper than ``angle`` and (optionally) where materials change: a decent
    start for hard-surface props. Organic meshes want hand-placed seams in hidden places."""
    n = 0
    for o in _objs(targets):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        lim = math.radians(angle)
        for e in bm.edges:
            if clear:
                e.seam = False
            if len(e.link_faces) != 2:
                e.seam = True
            else:
                f1, f2 = e.link_faces
                if f1.normal.angle(f2.normal, 0.0) > lim or (material_borders and f1.material_index != f2.material_index):
                    e.seam = True
            n += e.seam
        bm.to_mesh(o.data)
        bm.free()
    return f"{n} seam edges"


def seam_loop(ctx, target, axis="X", value=0.0, eps=1e-4):
    """Mark seams on edges lying on a plane (e.g. the centre line x=0 of a character, the back)."""
    o = bpy.data.objects[target]
    i = "XYZ".index(axis)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n = 0
    for e in bm.edges:
        if all(abs(v.co[i] - value) < eps for v in e.verts):
            e.seam = True
            n += 1
    bm.to_mesh(o.data)
    bm.free()
    return f"{target}: {n} seam edges on {axis}={value}"


def unwrap(ctx, targets="GEO_", method="smart", angle=66.0, margin=0.01, uv_name="UVMap", pack=True):
    """smart: automatic islands by angle (props). angle/conformal: follow marked seams
    (characters, cloth). lightmap: one non-overlapping layout for light baking."""
    objs = _objs(targets)
    for o in objs:
        if uv_name not in o.data.uv_layers:
            o.data.uv_layers.new(name=uv_name)
        o.data.uv_layers.active = o.data.uv_layers[uv_name]
    _edit(objs)
    if method == "smart":
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, scale_to_bounds=False)
    elif method in ("angle", "conformal"):
        bpy.ops.uv.unwrap(method="ANGLE_BASED" if method == "angle" else "CONFORMAL", margin=margin)
    elif method == "lightmap":
        _object_mode()
        for o in objs:
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], edit_object=None):
                bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_MARGIN_DIV=0.2)
        _edit(objs)
    else:
        raise ValueError(method)
    if pack:
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method="CONCAVE")
    _object_mode()
    return f"{method} unwrap on {len(objs)} objects"


def pack(ctx, targets="GEO_", margin=0.01, rotate=True, together=True):
    objs = _objs(targets)
    if together:
        _edit(objs)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=rotate, margin=margin, shape_method="CONCAVE")
        _object_mode()
    else:
        for o in objs:
            _edit([o])
            bpy.ops.uv.select_all(action="SELECT")
            bpy.ops.uv.pack_islands(rotate=rotate, margin=margin)
            _object_mode()
    return f"packed {len(objs)} objects"


def _texel(o, tex=1024):
    """Pixels per metre: sqrt(uv area * tex^2 / world area)."""
    uv = o.data.uv_layers.active
    if uv is None:
        return 0.0
    mw = o.matrix_world
    a3 = auv = 0.0
    for p in o.data.polygons:
        a3 += p.area * mw.to_scale().x ** 2
        pts = [uv.data[i].uv for i in p.loop_indices]
        s = 0.0
        for k in range(len(pts)):
            x1, y1 = pts[k]
            x2, y2 = pts[(k + 1) % len(pts)]
            s += x1 * y2 - x2 * y1
        auv += abs(s) / 2
    return math.sqrt(auv * tex * tex / a3) if a3 > 0 else 0.0


def texel_report(ctx, targets="GEO_", tex=1024):
    vals = {o.name: round(_texel(o, tex), 1) for o in _objs(targets)}
    ctx.report.data["texel_density"] = vals
    return f"px/m at {tex}: {vals}"


# ------------------------------------------------------------------ baking
BAKE = {  # map -> (Cycles bake type, pass filter, colour space)
    "ao": ("AO", set(), "Non-Color"),
    "normal": ("NORMAL", set(), "Non-Color"),
    "diffuse": ("DIFFUSE", {"COLOR"}, "sRGB"),
    "roughness": ("ROUGHNESS", set(), "Non-Color"),
    "emit": ("EMIT", set(), "sRGB"),
    "combined": ("COMBINED", {"DIRECT", "INDIRECT", "DIFFUSE", "GLOSSY", "TRANSMISSION", "EMIT"}, "sRGB"),
}


def _bake_node(mat, img, label):
    nt = mat.node_tree
    n = nt.nodes.get(label) or nt.nodes.new("ShaderNodeTexImage")
    n.name = n.label = label
    n.image = img
    n.location = (-900, -300 * (len(nt.nodes) % 4))
    nt.nodes.active = n
    return n


def bake(ctx, target, maps=("ao", "normal"), size=1024, high=None, extrusion=0.02, margin=8, samples=32,
         wire=True, ao_strength=1.0):
    """Bake ``maps`` for ``target`` into textures/<target>_<map>.png. With ``high`` the details of
    that object are projected onto the target (selected-to-active, cage extrusion in metres).
    ``wire`` connects the results: normal -> Normal Map -> BSDF Normal, diffuse -> Base Color,
    ao multiplies Base Color, roughness -> Roughness."""
    low = bpy.data.objects[target]
    if not low.data.uv_layers:
        raise RuntimeError(f"{target} has no UVs: unwrap first")
    if not low.material_slots or not low.material_slots[0].material:
        mat = bpy.data.materials.new(f"MAT_{target[4:] if target.startswith('GEO_') else target}_baked")
        low.data.materials.append(mat)
    scene = bpy.context.scene
    prev_engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    bk = scene.render.bake
    bk.margin = margin
    bk.use_selected_to_active = high is not None
    bk.cage_extrusion = extrusion
    os.makedirs(ctx.path("textures"), exist_ok=True)
    hi = bpy.data.objects[high] if high else None
    if hi is not None:
        hide_r = hi.hide_render
        hi.hide_render = False
    done = {}
    for m in maps:
        kind, passes, cs = BAKE[m]
        img = bpy.data.images.new(f"{target}_{m}", size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = cs
        mats = [s.material for s in low.material_slots if s.material]
        for mat in mats:
            _bake_node(mat, img, f"BAKE_{m}")
        for o in bpy.context.view_layer.objects:
            if o is not None:
                o.select_set(o in (low, hi))
        bpy.context.view_layer.objects.active = low
        kw = {"type": kind, "margin": margin, "use_selected_to_active": hi is not None}
        if passes:
            kw["pass_filter"] = passes
        if hi is not None:
            kw["cage_extrusion"] = extrusion
        bpy.ops.object.bake(**kw)
        path = ctx.path("textures", f"{target}_{m}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        ctx.report.artefact(path, "texture")
        done[m] = path
    if hi is not None:
        hi.hide_render = hide_r
    if wire:
        for mat in [s.material for s in low.material_slots if s.material]:
            _wire(mat, done, ao_strength)
    scene.render.engine = prev_engine
    return f"baked {list(done)} at {size}px"


def _wire(mat, done, ao_strength):
    nodes = {m: mat.node_tree.nodes[f"BAKE_{m}"] for m in done if f"BAKE_{m}" in mat.node_tree.nodes}
    bm_textures.wire(mat, nodes, ao_strength)


# ------------------------------------------------------------------ checks
@bm_checks.register("uv_in_bounds")
def _uv_in_bounds(ctx, objects="GEO_", eps=1e-3):
    bad = {}
    for o in bm_checks.select(objects):
        uv = o.data.uv_layers.active
        if uv is None:
            bad[o.name] = "no uv"
            continue
        out = sum(1 for d in uv.data if not (-eps <= d.uv.x <= 1 + eps and -eps <= d.uv.y <= 1 + eps))
        if out:
            bad[o.name] = out
    return not bad, bad, "all UVs inside 0-1", ""


@bm_checks.register_fix("uv_in_bounds")
def _fix_uv_bounds(ctx, args, attempt):
    pack(ctx, args.get("objects", "GEO_"))
    return "re-packed islands into 0-1"


def _raster(o, res=256):
    uv = o.data.uv_layers.active
    grid = bytearray(res * res)
    over = 0
    for p in o.data.polygons:
        pts = [uv.data[i].uv for i in p.loop_indices]
        for k in range(1, len(pts) - 1):
            tri = (pts[0], pts[k], pts[k + 1])
            xs = [min(res - 1, max(0, int(t.x * res))) for t in tri]
            ys = [min(res - 1, max(0, int(t.y * res))) for t in tri]
            (x0, y0), (x1, y1), (x2, y2) = [(t.x * res, t.y * res) for t in tri]
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-12:
                continue
            for y in range(min(ys), max(ys) + 1):
                for x in range(min(xs), max(xs) + 1):
                    px, py = x + 0.5, y + 0.5
                    a = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / den
                    b = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / den
                    if a >= 0 and b >= 0 and a + b <= 1:
                        i = y * res + x
                        if grid[i]:
                            over += 1
                        grid[i] = 1
    filled = sum(grid)
    return filled, over


@bm_checks.register("uv_no_overlap")
def _uv_no_overlap(ctx, objects="GEO_", max_ratio=0.01, res=256):
    vals, ok = {}, True
    for o in bm_checks.select(objects):
        if not o.data.uv_layers:
            vals[o.name] = "no uv"
            ok = False
            continue
        filled, over = _raster(o, res)
        r = over / max(filled, 1)
        vals[o.name] = {"coverage": round(filled / res / res, 3), "overlap": round(r, 4)}
        ok = ok and r <= max_ratio
    return ok, vals, f"overlap <= {max_ratio}", ""


@bm_checks.register("texel_density")
def _texel_density(ctx, objects="GEO_", tex=1024, min_px_m=None, max_spread=2.0):
    vals = {o.name: _texel(o, tex) for o in bm_checks.select(objects)}
    if not vals:
        return False, vals, "objects", "none"
    lo, hi = min(vals.values()), max(vals.values())
    ok = lo > 0 and hi / lo <= max_spread and (min_px_m is None or lo >= min_px_m)
    return ok, {k: round(v, 1) for k, v in vals.items()}, f"spread <= {max_spread}x", ""


@bm_checks.register("bake_nonempty")
def _bake_nonempty(ctx, pattern="textures/*.png", min_std=0.003):
    """Each map varies (largest per-channel standard deviation >= ``min_std``): catches failed,
    flat or black bakes. Normal maps of subtle detail sit around 0.005-0.02."""
    import glob
    files = sorted(glob.glob(os.path.join(ctx.out_dir, pattern)))
    if not files:
        return False, [], pattern, "no baked files"
    res, ok = {}, True
    for f in files:
        img = bpy.data.images.load(f, check_existing=False)
        px = list(img.pixels[:])
        bpy.data.images.remove(img)
        best = 0.0
        for c in range(3):
            vals = px[c::4 * 7]
            mean = sum(vals) / len(vals)
            best = max(best, math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)))
        res[os.path.basename(f)] = round(best, 4)
        ok = ok and best >= min_std
    return ok, res, f"channel std >= {min_std} (not flat)", ""


OPS = {"mark_seams": mark_seams, "seam_loop": seam_loop, "unwrap": unwrap, "pack": pack,
       "texel_report": texel_report, "bake": bake}
FIXES = {"uv_in_bounds": _fix_uv_bounds}
