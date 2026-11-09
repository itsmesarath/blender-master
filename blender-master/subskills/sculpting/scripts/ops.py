"""sculpting ops: high-resolution sculpt copies, voxel remesh, multires, scripted brush-like
deformations (inflate, grab, surface noise, smooth, crease), symmetry, and detail checks.

Interactive sculpting needs a person at the viewport; these ops prepare the mesh for that
session and cover the procedural parts (broad forms, noise, symmetry) headless."""
from __future__ import annotations

import os

import bmesh
import bpy
from mathutils import Vector, kdtree, noise

import bm_checks
import bm_io
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _bake_modifiers(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    if old.users == 0:
        bpy.data.meshes.remove(old)


def make_high(ctx, source, name=None, levels=2, hide_source=False):
    """Duplicate ``source`` as GEO_<name>_high with ``levels`` of smooth subdivision applied:
    the dense copy you sculpt on while the original stays the clean low-poly base."""
    src = _obj(source)
    name = name or f"{src.name}_high"
    bm_scene.remove_object(name)
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.animation_data_clear()
    bm_scene.link_exclusive(o)
    for m in list(o.modifiers):
        if m.type in {"ARMATURE", "SUBSURF", "MULTIRES"}:
            o.modifiers.remove(m)
    sd = o.modifiers.new("Subdivision", "SUBSURF")
    sd.levels = sd.render_levels = levels
    _bake_modifiers(o)
    for k in ("joints", "joint_edges"):
        if k in src.keys():
            o[k] = src[k]
    src.hide_render = src.hide_render or hide_source
    return f"{o.name}: {len(o.data.vertices)} verts"


def voxel_remesh(ctx, target, voxel=0.01, adaptivity=0.0, keep_volume=True):
    """Even, all-quads density over the whole surface (joins intersecting parts). Lose UVs and
    shape keys; do it before detailing, not after."""
    o = _obj(target)
    bm_io.checkpoint(os.path.join(ctx.out_dir, "blend", "checkpoints"), f"{ctx.part_id}_{o.name}_remesh")
    m = o.modifiers.new("Remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = adaptivity
    m.use_smooth_shade = True
    _bake_modifiers(o)
    return f"{o.name}: voxel {voxel} -> {len(o.data.vertices)} verts"


def multires(ctx, target, levels=2):
    """Add a Multires modifier and subdivide it (keeps the base editable, details on levels)."""
    o = _obj(target)
    m = next((m for m in o.modifiers if m.type == "MULTIRES"), None) or o.modifiers.new("Multires", "MULTIRES")
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        for _ in range(max(0, levels - m.total_levels)):
            bpy.ops.object.multires_subdivide(modifier=m.name, mode="CATMULL_CLARK")
    m.levels = m.sculpt_levels = m.render_levels = m.total_levels
    return f"{o.name}: multires {m.total_levels} levels"


def _falloff(d, radius):
    t = max(0.0, 1.0 - d / radius)
    return t * t * (3 - 2 * t)


def _region(o, center, radius, mirror_x):
    c = Vector(center)
    cs = [c] + ([Vector((-c.x, c.y, c.z))] if mirror_x and abs(c.x) > 1e-6 else [])
    out = []
    for v in o.data.vertices:
        w = max(_falloff((v.co - cc).length, radius) for cc in cs)
        if w > 0:
            out.append((v, w))
    return out


def inflate(ctx, target, center, radius, amount, mirror_x=True):
    """Push vertices along their normals inside a soft sphere (cheeks, muscles, belly)."""
    o = _obj(target)
    hits = _region(o, center, radius, mirror_x)
    for v, w in hits:
        v.co += v.normal * amount * w
    o.data.update()
    return f"{o.name}: inflated {len(hits)} verts"


def grab(ctx, target, center, radius, offset, mirror_x=True):
    """Move a soft region by ``offset`` (mirrored on X: the X component flips on the far side)."""
    o = _obj(target)
    c = Vector(center)
    off = Vector(offset)
    n = 0
    for v in o.data.vertices:
        w = _falloff((v.co - c).length, radius)
        if mirror_x and abs(c.x) > 1e-6:
            wm = _falloff((v.co - Vector((-c.x, c.y, c.z))).length, radius)
            if wm > w:
                v.co += Vector((-off.x, off.y, off.z)) * wm
                n += 1
                continue
        if w > 0:
            v.co += off * w
            n += 1
    o.data.update()
    return f"{o.name}: moved {n} verts"


def surface_noise(ctx, target, strength=0.003, scale=40.0, seed=0, symmetric=True):
    """Fine organic breakup (skin pores at small scale, rock or bark at large scale).
    Symmetric noise samples |x| so the result stays mirror-exact."""
    o = _obj(target)
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in o.data.vertices:
        p = Vector((abs(v.co.x) if symmetric else v.co.x, v.co.y, v.co.z)) * scale + off
        v.co += v.normal * noise.noise(p) * strength
    o.data.update()
    return f"{o.name}: noise {strength} m at scale {scale}"


def crease(ctx, target, points, radius=0.01, depth=0.003, mirror_x=True):
    """Carve a soft groove along a polyline of points (eyelids, muscle separations, panel lines)."""
    o = _obj(target)
    pts = [Vector(p) for p in points]
    lines = [pts] + ([[Vector((-p.x, p.y, p.z)) for p in pts]] if mirror_x else [])
    n = 0
    for v in o.data.vertices:
        best = 0.0
        for line in lines:
            for a, b in zip(line, line[1:]):
                ab = b - a
                t = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-12)))
                best = max(best, _falloff((v.co - (a + ab * t)).length, radius))
        if best > 0:
            v.co -= v.normal * depth * best
            n += 1
    o.data.update()
    return f"{o.name}: creased {n} verts"


def smooth(ctx, target, iterations=2, factor=0.5, preserve_volume=True):
    o = _obj(target)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for _ in range(iterations):
        if preserve_volume:
            bmesh.ops.smooth_laplacian_vert(bm, verts=bm.verts, lambda_factor=factor, lambda_border=0.0,
                                            use_x=True, use_y=True, use_z=True, preserve_volume=True)
        else:
            bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=factor, use_axis_x=True, use_axis_y=True,
                                  use_axis_z=True)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return f"{o.name}: smoothed x{iterations}"


def symmetrize(ctx, target, direction="-X"):
    """Copy one half onto the other: "-X" copies the -X side onto +X, "X" the reverse."""
    o = _obj(target)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction=direction, dist=1e-5)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return f"{o.name}: symmetrized {direction}"


def setup_session(ctx, target, symmetry_x=True, dyntopo=False, detail=12.0):
    """Prepare a mesh for an interactive sculpt session: mirror flags on, a note with the plan."""
    o = _obj(target)
    o.data.use_mirror_x = symmetry_x
    o["sculpt_session"] = f"symmetry_x={symmetry_x} dyntopo={dyntopo} detail={detail}"
    return f"{o.name}: session prepared"


def _sym_error(o):
    verts = o.data.vertices
    kd = kdtree.KDTree(len(verts))
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()
    return max((kd.find(Vector((-v.co.x, v.co.y, v.co.z)))[2] for v in verts), default=0.0)


@bm_checks.register("sculpt_detail")
def _sculpt_detail(ctx, objects="GEO_", min_verts=20000):
    objs = bm_checks.select(objects)
    vals = {}
    for o in objs:
        dg = bpy.context.evaluated_depsgraph_get()
        vals[o.name] = len(o.evaluated_get(dg).data.vertices)
    ok = bool(vals) and all(v >= min_verts for v in vals.values())
    return ok, vals, f">={min_verts} verts", ""


@bm_checks.register("symmetry_ok")
def _symmetry_ok(ctx, objects="GEO_", tol=0.002):
    vals = {o.name: round(_sym_error(o), 5) for o in bm_checks.select(objects)}
    return bool(vals) and all(v <= tol for v in vals.values()), vals, f"mirror error <= {tol} m", ""


@bm_checks.register_fix("symmetry_ok")
def _fix_symmetry(ctx, args, attempt):
    for o in bm_checks.select(args.get("objects", "GEO_")):
        symmetrize(ctx, o.name)
    return "symmetrized"


OPS = {"make_high": make_high, "voxel_remesh": voxel_remesh, "multires": multires, "inflate": inflate,
       "grab": grab, "surface_noise": surface_noise, "crease": crease, "smooth": smooth,
       "symmetrize": symmetrize, "setup_session": setup_session}
FIXES = {"symmetry_ok": _fix_symmetry}
