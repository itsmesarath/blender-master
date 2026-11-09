"""Numeric checks used by every sub-skill's acceptance criteria.

All functions are read-only: they never change the scene. They take evaluated geometry
(modifiers applied in memory) unless stated otherwise.
"""
from __future__ import annotations

import math
from collections import Counter

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# ---------------------------------------------------------------- bounds ------------
def world_bounds(obj: bpy.types.Object, evaluated: bool = True) -> tuple[Vector, Vector]:
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        ob = obj.evaluated_get(dg)
    else:
        ob = obj
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def bounds_of(objects) -> tuple[Vector, Vector]:
    objects = [o for o in objects if o.type in {"MESH", "CURVE", "CURVES", "FONT", "SURFACE", "META"}]
    if not objects:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    los, his = zip(*(world_bounds(o) for o in objects))
    lo = Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los)))
    hi = Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his)))
    return lo, hi


def size_of(objects) -> Vector:
    lo, hi = bounds_of(objects)
    return hi - lo


def size_within(objects, target_xyz, tol: float = 0.05) -> tuple[bool, list[float]]:
    """Each axis within relative tolerance of target (None axis = ignore)."""
    s = size_of(objects)
    ok = True
    for i, t in enumerate(target_xyz):
        if t is None:
            continue
        if abs(s[i] - t) > tol * max(t, 1e-6):
            ok = False
    return ok, [round(x, 4) for x in s]


# ---------------------------------------------------------------- transforms --------
def scale_applied(obj, eps: float = 1e-4) -> bool:
    return all(abs(s - 1.0) < eps for s in obj.scale)


def negative_scale(obj) -> bool:
    return obj.matrix_world.determinant() < 0


def on_ground(obj, ground_z: float = 0.0, eps: float = 0.002) -> bool:
    lo, _ = world_bounds(obj)
    return abs(lo.z - ground_z) <= eps


def floating(objects, ground_z: float = 0.0, eps: float = 0.002) -> list[str]:
    """Objects whose lowest point is above ground and that do not touch another object below."""
    out = []
    objects = list(objects)
    boxes = {o.name: world_bounds(o) for o in objects}
    for o in objects:
        lo, hi = boxes[o.name]
        if lo.z <= ground_z + eps:
            continue
        supported = False
        for other in objects:
            if other is o:
                continue
            olo, ohi = boxes[other.name]
            xy = lo.x <= ohi.x + eps and hi.x >= olo.x - eps and lo.y <= ohi.y + eps and hi.y >= olo.y - eps
            if xy and olo.z - eps <= lo.z <= ohi.z + eps:
                supported = True
                break
        if not supported:
            out.append(o.name)
    return out


# ---------------------------------------------------------------- geometry ----------
def _bm_eval(obj, world: bool = True) -> bmesh.types.BMesh:
    dg = bpy.context.evaluated_depsgraph_get()
    ob = obj.evaluated_get(dg)
    me = ob.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    if world:
        bm.transform(ob.matrix_world)
    ob.to_mesh_clear()
    return bm


def face_stats(obj, evaluated: bool = False) -> dict:
    """tris / quads / ngons counts and ratios on base (default) or evaluated mesh."""
    if evaluated:
        bm = _bm_eval(obj, world=False)
        sizes = Counter(len(f.verts) for f in bm.faces)
        bm.free()
    else:
        sizes = Counter(len(p.vertices) for p in obj.data.polygons)
    total = sum(sizes.values()) or 1
    tris, quads = sizes.get(3, 0), sizes.get(4, 0)
    ngons = total - tris - quads if sum(sizes.values()) else 0
    return {"faces": sum(sizes.values()), "tris": tris, "quads": quads, "ngons": ngons,
            "quad_ratio": round(quads / total, 4), "tri_count_triangulated": sum(max(k - 2, 0) * v for k, v in sizes.items())}


def poles(obj) -> dict:
    """Interior vertex valence report: 3-poles, 5-poles, 6+ poles (base mesh)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    c = Counter()
    for v in bm.verts:
        if v.is_boundary or not v.link_faces:
            continue
        val = len(v.link_edges)
        if val == 3:
            c["n3"] += 1
        elif val == 5:
            c["n5"] += 1
        elif val >= 6:
            c["n6plus"] += 1
    bm.free()
    return {"n3": c["n3"], "n5": c["n5"], "n6plus": c["n6plus"]}


def manifold_report(obj, evaluated: bool = True) -> dict:
    bm = _bm_eval(obj, world=False) if evaluated else _bm_base(obj)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    loose_v = sum(1 for v in bm.verts if not v.link_edges)
    islands = _islands(bm)
    bm.free()
    return {"non_manifold_edges": non_manifold, "boundary_edges": boundary, "loose_verts": loose_v,
            "islands": islands}


def _bm_base(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def _islands(bm) -> int:
    seen, n = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        stack = [v]
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            stack.extend(e.other_vert(x) for e in x.link_edges if e.other_vert(x).index not in seen)
    return n


def signed_volume(obj) -> float:
    """Positive for closed meshes with outward normals; negative means flipped normals."""
    bm = _bm_eval(obj, world=True)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return vol


def normals_outward(obj, eps: float = 1e-9) -> bool:
    rep = manifold_report(obj)
    if rep["non_manifold_edges"] or rep["boundary_edges"]:
        return True  # open meshes: volume test not meaningful; report separately
    return signed_volume(obj) > eps


# ---------------------------------------------------------------- overlaps ----------
def _bvh(obj):
    bm = _bm_eval(obj, world=True)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def overlaps(objects, allow: set[frozenset] | None = None) -> list[tuple[str, str]]:
    """Pairs of mesh objects whose surfaces intersect (BVH triangle overlap).

    Touching faces (coplanar contact) can also register; use ``allow`` for intended contacts
    such as a bottle standing on a table, or check only objects that should never touch.
    """
    allow = allow or set()
    meshes = [o for o in objects if o.type == "MESH"]
    boxes = {o.name: world_bounds(o) for o in meshes}
    trees = {}
    hits = []
    for i, a in enumerate(meshes):
        for b in meshes[i + 1:]:
            if frozenset((a.name, b.name)) in allow:
                continue
            alo, ahi = boxes[a.name]
            blo, bhi = boxes[b.name]
            if any(alo[k] > bhi[k] or blo[k] > ahi[k] for k in range(3)):
                continue
            ta = trees.setdefault(a.name, _bvh(a))
            tb = trees.setdefault(b.name, _bvh(b))
            if ta.overlap(tb):
                hits.append((a.name, b.name))
    return hits


# ---------------------------------------------------------------- materials ---------
def material_report(obj) -> dict:
    slots = list(obj.material_slots)
    empty = [i for i, s in enumerate(slots) if s.material is None]
    missing_images = []
    for s in slots:
        m = s.material
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE":
                    img = n.image
                    if img is None or (img.source == "FILE" and not img.has_data and not _image_file_exists(img)):
                        missing_images.append(f"{m.name}:{n.name}")
    return {"slots": len(slots), "empty_slots": empty, "missing_images": missing_images}


def _image_file_exists(img) -> bool:
    import os
    try:
        return os.path.exists(bpy.path.abspath(img.filepath))
    except Exception:
        return False


def materials_filled(objects) -> list[str]:
    """Names of mesh objects with no material or an empty slot."""
    bad = []
    for o in objects:
        if o.type != "MESH":
            continue
        r = material_report(o)
        if r["slots"] == 0 or r["empty_slots"] or r["missing_images"]:
            bad.append(o.name)
    return bad


# ---------------------------------------------------------------- cameras -----------
def frame_coverage(cam_obj, objects, margin: float = 0.0, scene=None) -> dict:
    """Project every bound-box corner into the camera. Reports whether all are inside the frame
    (shrunk by ``margin`` on each side, as a fraction) and how much of the frame the subject fills."""
    from bpy_extras.object_utils import world_to_camera_view
    scene = scene or bpy.context.scene
    pts = []
    for o in objects:
        if o.type not in {"MESH", "CURVE", "CURVES", "FONT"}:
            continue
        dg = bpy.context.evaluated_depsgraph_get()
        ob = o.evaluated_get(dg)
        pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    if not pts:
        return {"inside": False, "fill": 0.0, "behind": 0}
    ndc = [world_to_camera_view(scene, cam_obj, p) for p in pts]
    behind = sum(1 for p in ndc if p.z <= 0)
    xs, ys = [p.x for p in ndc], [p.y for p in ndc]
    inside = behind == 0 and min(xs) >= margin and max(xs) <= 1 - margin and min(ys) >= margin and max(ys) <= 1 - margin
    fill = max(0.0, (min(max(xs), 1) - max(min(xs), 0))) * max(0.0, (min(max(ys), 1) - max(min(ys), 0)))
    return {"inside": inside, "fill": round(fill, 4), "behind": behind,
            "x": [round(min(xs), 3), round(max(xs), 3)], "y": [round(min(ys), 3), round(max(ys), 3)]}


# ---------------------------------------------------------------- images ------------
def image_stats(path: str) -> dict:
    """Mean luminance, fraction of clipped and of black pixels, alpha range, size."""
    import numpy as np
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(-1, 4)
        lum = 0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]
        return {"width": w, "height": h, "mean": float(lum.mean()), "clipped": float((lum >= 0.995).mean()),
                "black": float((lum <= 0.005).mean()), "alpha_min": float(px[:, 3].min()),
                "alpha_max": float(px[:, 3].max()), "std": float(lum.std())}
    finally:
        bpy.data.images.remove(img)


def exposure_ok(stats: dict, mean_range=(0.12, 0.75), max_clipped: float = 0.02, max_black: float = 0.35) -> bool:
    return mean_range[0] <= stats["mean"] <= mean_range[1] and stats["clipped"] <= max_clipped and stats["black"] <= max_black


# ---------------------------------------------------------------- modifiers ---------
def modifier_order(obj) -> list[str]:
    return [m.type for m in obj.modifiers]


def degenerate_dims(obj, eps: float = 1e-5) -> bool:
    return any(d < eps for d in obj.dimensions)


def angle_deg(v1: Vector, v2: Vector) -> float:
    return math.degrees(v1.angle(v2))
