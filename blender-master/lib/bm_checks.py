"""Acceptance-check registry shared by all sub-skills.

A brief's part lists acceptance items as ``{"check": name, "args": {...}, "desc": "..."}``.
Each check returns ``(passed, value, expected, detail)``. Sub-skills may register extra checks
and fixers through ``register`` / ``register_fix``.

Object selectors (``objects`` arg): a list of names, a prefix string ending in "_" (e.g. "GEO_"),
or "*" for all mesh objects in the scene.
"""
from __future__ import annotations

import glob
import os

import bpy

import bm_scene
import bm_verify

CHECKS: dict = {}
FIXES: dict = {}


def register(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


def register_fix(name):
    def deco(fn):
        FIXES[name] = fn
        return fn
    return deco


def select(sel, mesh_only: bool = True):
    scene_objs = list(bpy.context.scene.objects)
    if sel in (None, "*"):
        objs = scene_objs
    elif isinstance(sel, str):
        objs = [o for o in scene_objs if o.name.startswith(sel)] if sel.endswith("_") else \
            [o for o in scene_objs if o.name == sel]
    else:
        objs = [bpy.data.objects[n] for n in sel if n in bpy.data.objects]
    return [o for o in objs if o.type == "MESH"] if mesh_only else objs


def run(ctx, item: dict):
    name = item["check"]
    if name not in CHECKS:
        return False, None, None, f"unknown check {name!r}"
    try:
        return CHECKS[name](ctx, **item.get("args", {}))
    except Exception as exc:  # a crashing check is a failing check, with the reason
        return False, None, None, f"{type(exc).__name__}: {exc}"


# ------------------------------------------------------------------ generic checks
@register("objects_exist")
def _objects_exist(ctx, names=None, prefix=None, min_count=1, types=None):
    if names:
        missing = [n for n in names if n not in bpy.data.objects]
        return not missing, {"missing": missing}, names, ""
    objs = [o for o in bpy.context.scene.objects if o.name.startswith(prefix or "")]
    if types:
        objs = [o for o in objs if o.type in types]
    return len(objs) >= min_count, len(objs), f">={min_count}", prefix or ""


@register("names_valid")
def _names_valid(ctx, ignore_prefixes=("TMP_",)):
    bad = [n for n in bm_scene.bad_names() if not n.startswith(tuple(ignore_prefixes))]
    return not bad, bad, "PREFIX_Name for every object", ""


@register("bounds_size")
def _bounds_size(ctx, objects="GEO_", target=(None, None, None), tol=0.05):
    objs = select(objects)
    ok, size = bm_verify.size_within(objs, target, tol)
    return ok and bool(objs), size, {"target": list(target), "tol": tol}, f"{len(objs)} objects"


@register("max_dimension")
def _max_dimension(ctx, objects="GEO_", max_m=1.0, min_m=0.0):
    s = bm_verify.size_of(select(objects))
    m = max(s)
    return min_m <= m <= max_m, round(m, 4), [min_m, max_m], ""


@register("no_overlaps")
def _no_overlaps(ctx, objects="GEO_", allow=()):
    allow_set = {frozenset(p) for p in allow}
    hits = bm_verify.overlaps(select(objects), allow_set)
    return not hits, hits, [], ""


@register("on_ground")
def _on_ground(ctx, objects="GEO_", ground_z=0.0, eps=0.002):
    objs = select(objects)
    lo, _ = bm_verify.bounds_of(objs)
    return abs(lo.z - ground_z) <= eps, round(lo.z, 4), ground_z, "lowest point of the group"


@register("no_floating")
def _no_floating(ctx, objects="GEO_", ground_z=0.0):
    fl = bm_verify.floating(select(objects), ground_z)
    return not fl, fl, [], ""


@register("scale_applied")
def _scale_applied(ctx, objects="GEO_"):
    bad = [o.name for o in select(objects) if not bm_verify.scale_applied(o) or bm_verify.negative_scale(o)]
    return not bad, bad, [], ""


@register("quad_ratio")
def _quad_ratio(ctx, objects="GEO_", min_ratio=0.9):
    res = {o.name: bm_verify.face_stats(o)["quad_ratio"] for o in select(objects)}
    bad = {k: v for k, v in res.items() if v < min_ratio}
    return not bad and bool(res), res, f">={min_ratio}", ""


@register("no_ngons")
def _no_ngons(ctx, objects="GEO_"):
    res = {o.name: bm_verify.face_stats(o)["ngons"] for o in select(objects)}
    bad = {k: v for k, v in res.items() if v}
    return not bad, bad, 0, "base mesh"


@register("manifold")
def _manifold(ctx, objects="GEO_", allow_open=()):
    bad = {}
    for o in select(objects):
        if o.name in allow_open:
            continue
        r = bm_verify.manifold_report(o)
        if r["non_manifold_edges"] or r["loose_verts"]:
            bad[o.name] = r
    return not bad, bad, "0 non-manifold edges, 0 loose verts", ""


@register("normals_outward")
def _normals(ctx, objects="GEO_"):
    bad = [o.name for o in select(objects) if not bm_verify.normals_outward(o)]
    return not bad, bad, [], "signed volume > 0 on closed meshes"


@register("tri_budget")
def _tri_budget(ctx, objects="GEO_", max_tris=10000, evaluated=True):
    total = 0
    for o in select(objects):
        total += bm_verify.face_stats(o, evaluated=evaluated)["tri_count_triangulated"]
    return total <= max_tris, total, f"<={max_tris}", "after modifiers" if evaluated else "base"


@register("materials_filled")
def _materials_filled(ctx, objects="GEO_"):
    bad = bm_verify.materials_filled(select(objects))
    return not bad, bad, [], "every slot has a material, no missing images"


@register("uv_present")
def _uv_present(ctx, objects="GEO_"):
    bad = [o.name for o in select(objects) if not o.data.uv_layers]
    return not bad, bad, [], ""


@register("modifier_present")
def _modifier_present(ctx, objects="GEO_", types=("BEVEL",), min_objects=1):
    have = [o.name for o in select(objects) if set(types) <= {m.type for m in o.modifiers}]
    return len(have) >= min_objects, have, f">={min_objects} objects with {list(types)}", ""


@register("cameras_exist")
def _cameras_exist(ctx, names=("CAM_hero",)):
    missing = [n for n in names if n not in bpy.data.objects or bpy.data.objects[n].type != "CAMERA"]
    return not missing, {"missing": missing}, list(names), ""


@register("camera_frames")
def _camera_frames(ctx, camera="CAM_hero", objects="GEO_", margin=0.04, min_fill=0.15):
    cam = bpy.data.objects.get(camera)
    if cam is None:
        return False, None, camera, "camera missing"
    cov = bm_verify.frame_coverage(cam, select(objects), margin)
    return cov["inside"] and cov["fill"] >= min_fill, cov, {"margin": margin, "min_fill": min_fill}, camera


@register("lights_exist")
def _lights_exist(ctx, min_count=1):
    n = sum(1 for o in bpy.context.scene.objects if o.type == "LIGHT")
    emissive_world = bpy.context.scene.world is not None
    return n >= min_count, n, f">={min_count}", f"world set: {emissive_world}"


@register("exposure")
def _exposure(ctx, camera="CAM_hero", mean_min=0.12, mean_max=0.75, max_clipped=0.02, max_black=0.35,
              res=(320, 180), samples=12):
    import bm_render
    path = os.path.join(ctx.out_dir, "previews", f"{ctx.part_id}_exposure_a{ctx.attempt}.png")
    sc = bpy.context.scene
    keep = (sc.render.resolution_x, sc.render.resolution_y,
            sc.cycles.samples if sc.render.engine == "CYCLES" else None)
    bm_render.preview_settings(samples=samples, res=res)
    bm_render.render_still(path, camera)
    sc.render.resolution_x, sc.render.resolution_y = keep[0], keep[1]
    st = bm_verify.image_stats(path)
    ctx.report.artefact(path, "exposure_probe")
    ok = bm_verify.exposure_ok(st, (mean_min, mean_max), max_clipped, max_black)
    return ok, {k: round(v, 4) if isinstance(v, float) else v for k, v in st.items()}, \
        {"mean": [mean_min, mean_max], "clipped<=": max_clipped, "black<=": max_black}, camera


@register("render_ok")
def _render_ok(ctx, pattern="renders/*.png", min_count=1, size=None, need_alpha=False,
               mean_min=0.03, max_black=0.9):
    paths = sorted(glob.glob(os.path.join(ctx.out_dir, pattern)))
    bad = {}
    for p in paths:
        st = bm_verify.image_stats(p)
        why = []
        if size and [st["width"], st["height"]] != list(size):
            why.append(f"size {st['width']}x{st['height']}")
        if st["mean"] < mean_min or st["black"] > max_black:
            why.append("near-black")
        if need_alpha and st["alpha_min"] > 0.99:
            why.append("no transparency")
        if why:
            bad[os.path.basename(p)] = why
    return len(paths) >= min_count and not bad, {"count": len(paths), "bad": bad}, \
        {"min_count": min_count, "size": size, "alpha": need_alpha}, pattern


@register("files_exist")
def _files_exist(ctx, patterns=()):
    missing = [p for p in patterns if not glob.glob(os.path.join(ctx.out_dir, p))]
    return not missing, {"missing": missing}, list(patterns), ""


@register("compositor_chain")
def _compositor_chain(ctx, contains=("CompositorNodeDenoise",)):
    import bm_compositor
    chain = bm_compositor.chain_types()
    ok = all(c in chain for c in contains) and chain[-1:] == ["NodeGroupOutput"]
    return ok, chain, list(contains) + ["NodeGroupOutput last"], ""


@register("custom_prop")
def _custom_prop(ctx, objects="PRX_", key="brief_note", mesh_only=True):
    objs = select(objects, mesh_only)
    missing = [o.name for o in objs if key not in o.keys()]
    return not missing and bool(objs), missing, f"{key} on every object", ""


# ------------------------------------------------------------------ generic fixes
@register_fix("on_ground")
def _fix_ground(ctx, args, attempt):
    objs = select(args.get("objects", "GEO_"))
    lo, _ = bm_verify.bounds_of(objs)
    dz = args.get("ground_z", 0.0) - lo.z
    for o in objs:
        if o.parent is None or o.parent not in objs:
            o.location.z += dz
    bpy.context.view_layer.update()
    return f"moved group by dz={dz:.4f}"


@register_fix("scale_applied")
def _fix_scale(ctx, args, attempt):
    objs = select(args.get("objects", "GEO_"))
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(o in objs)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return f"applied scale on {len(objs)} objects"


@register_fix("normals_outward")
def _fix_normals(ctx, args, attempt):
    import bmesh
    fixed = []
    for o in select(args.get("objects", "GEO_")):
        if bm_verify.normals_outward(o):
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(o.data)
        bm.free()
        fixed.append(o.name)
    return f"recalculated normals: {fixed}"


@register_fix("materials_filled")
def _fix_materials(ctx, args, attempt):
    mat = bpy.data.materials.get("MAT_placeholder") or bpy.data.materials.new("MAT_placeholder")
    mat.diffuse_color = (1.0, 0.0, 1.0, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.0, 0.8, 1.0)
    n = 0
    for o in bm_verify.materials_filled(select(args.get("objects", "GEO_"))):
        ob = bpy.data.objects[o]
        if not ob.material_slots:
            ob.data.materials.append(mat)
        for s in ob.material_slots:
            if s.material is None:
                s.material = mat
        n += 1
    return f"placeholder material on {n} objects (flagged magenta: replace it)"


@register_fix("names_valid")
def _fix_names(ctx, args, attempt):
    renamed = []
    for name in bm_scene.bad_names():
        o = bpy.data.objects[name]
        pre = {"CAMERA": "CAM_", "LIGHT": "LGT_", "EMPTY": "CTRL_", "GREASEPENCIL": "REV_"}.get(o.type, "GEO_")
        o.name = pre + "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
        bm_scene.link_exclusive(o)
        renamed.append(o.name)
    return f"renamed {renamed}"
