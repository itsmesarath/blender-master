"""hair-fur ops: strand hair and fur as Blender hair-curves objects generated from Python -
region-limited root sampling on a surface, guide strands with length, gravity, curl and clumping,
root-to-tip radius - plus a Principled Hair material and checks for strand count and roots."""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import bm_checks
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _face_ok(o, p, region, vg_index):
    if not region:
        return True
    c = p.center
    if "z_min" in region and c.z < region["z_min"]:
        return False
    if "z_max" in region and c.z > region["z_max"]:
        return False
    if "direction" in region:
        d = Vector(region["direction"]).normalized()
        if p.normal.dot(d) < region.get("min_dot", 0.0):
            return False
    if "center" in region and (c - Vector(region["center"])).length > region.get("radius", 1.0):
        return False
    if vg_index is not None:
        ws = []
        for vi in p.vertices:
            w = next((g.weight for g in o.data.vertices[vi].groups if g.group == vg_index), 0.0)
            ws.append(w)
        if sum(ws) / len(ws) < 0.5:
            return False
    return True


def _sample_roots(o, count, region, rng):
    """Area-weighted random points (local space) with normals on faces inside ``region``."""
    vg = region.get("vertex_group") if region else None
    vg_index = o.vertex_groups[vg].index if vg else None
    me = o.data
    faces = [p for p in me.polygons if _face_ok(o, p, region, vg_index)]
    if not faces:
        raise ValueError(f"no faces of {o.name} inside region {region}")
    tris = []
    for p in faces:
        vs = [me.vertices[i].co for i in p.vertices]
        for k in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[k], vs[k + 1]
            tris.append((a, b, c, ((b - a).cross(c - a)).length / 2, p.normal.copy()))
    total = sum(t[3] for t in tris)
    acc, cum = 0.0, []
    for t in tris:
        acc += t[3]
        cum.append(acc)
    out = []
    import bisect
    for _ in range(count):
        a, b, c, _area, n = tris[min(len(tris) - 1, bisect.bisect(cum, rng.random() * total))]
        u, v = rng.random(), rng.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        out.append((a + (b - a) * u + (c - a) * v, n))
    return out, total


def _guide(root, n, length, segs, gravity, curl, curl_radius, lift, rng):
    pts = [root.copy()]
    d = n.copy()
    down = Vector((0, 0, -1))
    perp = n.cross(Vector((0, 0, 1)))
    if perp.length < 1e-4:
        perp = n.cross(Vector((1, 0, 0)))
    perp.normalize()
    perp2 = n.cross(perp).normalized()
    phase = rng.random() * math.tau
    step = length / segs
    p = root.copy() + n * lift
    for i in range(1, segs + 1):
        t = i / segs
        d = (d + (down * gravity * 0.6 * t)).normalized()
        p = p + d * step
        if curl:
            a = phase + curl * math.tau * t
            off = (perp * math.cos(a) + perp2 * math.sin(a)) * curl_radius * t
        else:
            off = Vector()
        pts.append(p + off)
    return pts


def groom(ctx, name, surface, count=2000, length=0.12, length_var=0.25, region=None, gravity=0.6,
          curl=0.0, curl_radius=0.01, clump=0.4, guides=60, segments=8, radius_root=0.0006,
          radius_tip=0.0001, lift=0.002, seed=0, material=None):
    """Grow ``count`` strands on ``surface`` inside ``region`` (dict with any of z_min, z_max,
    direction+min_dot, center+radius, vertex_group). Strands follow ``guides`` guide strands and
    clump toward them by ``clump`` (0-1) towards the tips. Units are metres."""
    if not name.startswith("GEO_"):
        name = "GEO_" + name
    surf = _obj(surface)
    rng = random.Random(seed)
    roots, area = _sample_roots(surf, count, region or {}, rng)
    groots, _ = _sample_roots(surf, max(1, min(guides, count)), region or {}, random.Random(seed + 1))
    gstrands = [_guide(r, n, length, segments, gravity, curl, curl_radius, lift, rng) for r, n in groots]
    bm_scene.remove_object(name)
    old = bpy.data.hair_curves.get(name)
    if old is not None:
        bpy.data.hair_curves.remove(old)
    cv = bpy.data.hair_curves.new(name)
    cv.add_curves([segments + 1] * count)
    positions = []
    for root, n in roots:
        gi = min(range(len(groots)), key=lambda k: (groots[k][0] - root).length_squared)
        g = gstrands[gi]
        scale = 1.0 + (rng.random() * 2 - 1) * length_var
        own = _guide(root, n, length * scale, segments, gravity, curl, curl_radius, lift, rng)
        for i, p in enumerate(own):
            t = i / segments
            follow = root + (g[i] - g[0]) * scale
            mixed = p.lerp(follow, 0.5)  # share the guide's flow
            q = mixed.lerp(g[i], clump * t * t)
            positions.extend(q)
    cv.position_data.foreach_set("vector", positions)
    rad = cv.attributes.new("radius", "FLOAT", "POINT")
    radii = [radius_root + (radius_tip - radius_root) * (i / segments) for _ in range(count) for i in range(segments + 1)]
    rad.data.foreach_set("value", radii)
    cv.surface = surf
    obj = bpy.data.objects.new(name, cv)
    bm_scene.link_exclusive(obj)
    obj.parent = surf
    obj.matrix_parent_inverse.identity()
    if material:
        mat = bpy.data.materials.get(material if material.startswith("MAT_") else "MAT_" + material)
        if mat:
            cv.materials.append(mat)
    obj["hair_params"] = f"count={count} length={length} gravity={gravity} curl={curl} clump={clump}"
    return f"{name}: {count} strands over {area:.3f} m2 ({count / max(area, 1e-9):.0f}/m2)"


def fur(ctx, name, surface, density=40000, length=0.02, region=None, seed=0, material=None, max_count=60000):
    """Short dense coat: ``density`` strands per m2 (capped at ``max_count``), little gravity."""
    surf = _obj(surface)
    _r, area = _sample_roots(surf, 1, region or {}, random.Random(seed))
    count = max(100, min(max_count, int(density * area)))
    return groom(ctx, name, surface, count=count, length=length, length_var=0.3, region=region, gravity=0.15,
                 curl=0.0, clump=0.15, guides=200, segments=4, radius_root=0.0003, radius_tip=0.00005,
                 lift=0.0005, seed=seed, material=material)


def hair_material(ctx, name="hair", melanin=0.8, redness=0.3, roughness=0.35, radial_roughness=0.3,
                  random_color=0.1, targets=None, color=None):
    """Principled Hair BSDF: melanin 0 (blond/white) .. 1 (black); redness for auburn and ginger.
    ``color`` switches to direct colouring (dyed or stylized hair)."""
    if not name.startswith("MAT_"):
        name = "MAT_" + name
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    h = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    h.location = (-300, 0)
    if color is not None:
        h.parametrization = "COLOR"
        h.inputs["Color"].default_value = (*color[:3], 1.0)
    else:
        h.parametrization = "MELANIN"
        h.inputs["Melanin"].default_value = melanin
        h.inputs["Melanin Redness"].default_value = redness
    h.inputs["Roughness"].default_value = roughness
    h.inputs["Radial Roughness"].default_value = radial_roughness
    h.inputs["Random Color"].default_value = random_color
    nt.links.new(h.outputs[0], out.inputs["Surface"])
    for o in (bm_checks.select(targets, mesh_only=False) if targets else []):
        if o.type == "CURVES":
            o.data.materials.clear()
            o.data.materials.append(mat)
    return f"{name} ready"


def _curves(sel):
    return [o for o in bm_checks.select(sel, mesh_only=False) if o.type == "CURVES"]


@bm_checks.register("curve_count")
def _curve_count(ctx, prefix="GEO_", min_curves=100, max_curves=None):
    vals = {o.name: len(o.data.curves) for o in _curves(prefix)}
    ok = bool(vals) and all(v >= min_curves and (max_curves is None or v <= max_curves) for v in vals.values())
    return ok, vals, f">= {min_curves} strands", "" if vals else "no hair objects"


@bm_checks.register("hair_roots_on_surface")
def _roots(ctx, prefix="GEO_", tol=0.004):
    vals, ok = {}, True
    for o in _curves(prefix):
        s = o.data.surface
        if s is None:
            vals[o.name] = "no surface"
            ok = False
            continue
        tree = BVHTree.FromPolygons([v.co for v in s.data.vertices], [p.vertices[:] for p in s.data.polygons])
        offs = o.data.curve_offset_data
        pos = o.data.position_data
        worst = 0.0
        for i in range(0, len(o.data.curves), max(1, len(o.data.curves) // 300)):
            r = pos[offs[i].value].vector
            hit = tree.find_nearest(r)
            worst = max(worst, hit[3] if hit[0] is not None else 1.0)
        vals[o.name] = round(worst, 5)
        ok = ok and worst <= tol
    return ok and bool(vals), vals, f"roots within {tol} m of the surface", ""


@bm_checks.register("hair_material")
def _hair_mat(ctx, prefix="GEO_"):
    bad = [o.name for o in _curves(prefix) if not any(m for m in o.data.materials)]
    return not bad, bad, "every hair object has a material", ""


OPS = {"groom": groom, "fur": fur, "hair_material": hair_material}
FIXES = {}
