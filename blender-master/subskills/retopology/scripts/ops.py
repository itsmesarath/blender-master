"""retopology ops: clean low-poly surfaces from dense sculpts or scans - fit an existing base by
shrinkwrap, automatic quad remesh (QuadriFlow), voxel + decimate fallback, LOD chains - and a
BVH-based surface-distance check that the low mesh really follows the high one."""
from __future__ import annotations

import os

import bpy
from mathutils.bvhtree import BVHTree

import bm_checks
import bm_io
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _bake(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    if old.users == 0:
        bpy.data.meshes.remove(old)


def _copy(src, name):
    bm_scene.remove_object(name)
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.animation_data_clear()
    o.modifiers.clear()
    bm_scene.link_exclusive(o)
    o.hide_render = False
    return o


def shrinkwrap_fit(ctx, low, high, offset=0.0, smooth_iterations=1, hide_high=True, apply=True):
    """Fit an existing clean base (same proportions) onto the high surface: the fastest retopo
    when the sculpt was made from that base. Keeps the base's edge flow, UVs and vertex groups."""
    lo, hi = _obj(low), _obj(high)
    m = lo.modifiers.new("RETOPO_fit", "SHRINKWRAP")
    m.target = hi
    m.wrap_method = "NEAREST_SURFACEPOINT"
    m.offset = offset
    if smooth_iterations:
        s = lo.modifiers.new("RETOPO_relax", "CORRECTIVE_SMOOTH")
        s.iterations = smooth_iterations
        s.smooth_type = "LENGTH_WEIGHTED"
    if apply:
        _bake(lo)
    hi.hide_render = hi.hide_render or hide_high
    return f"{lo.name} fitted to {hi.name}"


def quad_remesh(ctx, source, name, faces=2000, use_symmetry=True, preserve_sharp=False, hide_source=True):
    """Automatic quad layout (QuadriFlow) on a copy of ``source``. Good for props, rocks and
    background characters; hero faces still want hand-placed loops around eyes and mouth."""
    src = _obj(source)
    o = _copy(src, name)
    bm_io.checkpoint(os.path.join(ctx.out_dir, "blend", "checkpoints"), f"{ctx.part_id}_{o.name}_qf")
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o],
                                   selected_editable_objects=[o]):
        res = bpy.ops.object.quadriflow_remesh(target_faces=faces, use_mesh_symmetry=use_symmetry,
                                               use_preserve_sharp=preserve_sharp, use_preserve_boundary=True,
                                               seed=0, mode="FACES")
    if "FINISHED" not in res or not o.data.polygons:
        return voxel_decimate(ctx, source, name, faces=faces, hide_source=hide_source)
    src.hide_render = src.hide_render or hide_source
    o.data.shade_smooth()
    return f"{o.name}: quadriflow {len(o.data.polygons)} faces"


def voxel_decimate(ctx, source, name, voxel=None, faces=2000, hide_source=True):
    """Fallback retopo: voxel remesh (even quads) then planar/collapse decimate to a budget."""
    src = _obj(source)
    o = _copy(src, name)
    size = max(src.dimensions)
    r = o.modifiers.new("Remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel or size / 60.0
    _bake(o)
    if len(o.data.polygons) > faces:
        d = o.modifiers.new("Decimate", "DECIMATE")
        d.ratio = faces / len(o.data.polygons)
        _bake(o)
    o.data.shade_smooth()
    src.hide_render = src.hide_render or hide_source
    return f"{o.name}: voxel+decimate {len(o.data.polygons)} faces"


def lod_chain(ctx, target, ratios=(0.5, 0.25, 0.1)):
    """Copies <target>_LOD1.. with collapse decimation. LOD0 is the target itself."""
    src = _obj(target)
    made = []
    for i, r in enumerate(ratios, 1):
        o = _copy(src, f"{src.name}_LOD{i}")
        d = o.modifiers.new("Decimate", "DECIMATE")
        d.ratio = r
        d.use_collapse_triangulate = True
        _bake(o)
        o.location = src.location
        made.append(f"{o.name}:{len(o.data.polygons)}")
    return "LODs " + ", ".join(made)


def _distances(low, high, samples=4000):
    dg = bpy.context.evaluated_depsgraph_get()
    he = high.evaluated_get(dg)
    hm = he.data
    mw = high.matrix_world
    tree = BVHTree.FromPolygons([mw @ v.co for v in hm.vertices], [p.vertices[:] for p in hm.polygons])
    le = low.evaluated_get(dg)
    verts = le.data.vertices
    step = max(1, len(verts) // samples)
    out = []
    for v in verts[::step]:
        hit = tree.find_nearest(low.matrix_world @ v.co)
        if hit[0] is not None:
            out.append(hit[3])
    return out


@bm_checks.register("surface_distance")
def _surface_distance(ctx, low="GEO_", high=None, max_mean=0.003, max_max=None):
    lows = bm_checks.select(low)
    hi = bpy.data.objects.get(high or "")
    if not lows or hi is None:
        return False, None, "low and high objects", "missing object"
    res, ok = {}, True
    for lo in lows:
        if lo == hi:
            continue
        d = _distances(lo, hi)
        mean, mx = sum(d) / max(len(d), 1), max(d, default=0.0)
        res[lo.name] = {"mean": round(mean, 5), "max": round(mx, 5)}
        ok = ok and mean <= max_mean and (max_max is None or mx <= max_max)
    return ok, res, f"mean <= {max_mean} m" + (f", max <= {max_max}" if max_max else ""), ""


@bm_checks.register_fix("surface_distance")
def _fix_distance(ctx, args, attempt):
    hi = args.get("high")
    for lo in bm_checks.select(args.get("low", "GEO_")):
        if lo.name != hi:
            shrinkwrap_fit(ctx, lo.name, hi, smooth_iterations=0)
    return "re-shrinkwrapped low onto high"


OPS = {"shrinkwrap_fit": shrinkwrap_fit, "quad_remesh": quad_remesh, "voxel_decimate": voxel_decimate,
       "lod_chain": lod_chain}
FIXES = {"surface_distance": _fix_distance}
