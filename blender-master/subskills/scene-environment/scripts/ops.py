"""scene-environment ops: terrain with a flat set area, streets with sidewalks and markings,
modular kit pieces on a grid and layouts of linked copies, prop scattering (via geometry-nodes),
proxy-to-asset swaps - and checks for z-fighting and camera coverage."""
from __future__ import annotations

import math
import bmesh
import bpy
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

import bm_checks
import bm_mesh
import bm_part
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _geo(name):
    return name if name.startswith("GEO_") else "GEO_" + name


def terrain(ctx, name="GEO_terrain", size=(60, 60), resolution=96, height=4.0, scale=0.04, seed=0,
            flat_center=(0, 0), flat_radius=8.0, flat_falloff=10.0, octaves=4):
    """Noise terrain. Inside ``flat_radius`` of ``flat_center`` it is flat at z = 0 (the set),
    blending to full height over ``flat_falloff`` metres."""
    name = _geo(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=resolution, y_segments=resolution, size=0.5)
    off = Vector((seed * 17.3, seed * 5.1, 0))
    fc = Vector((*flat_center, 0))
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        p = Vector((v.co.x, v.co.y, 0))
        h = noise.fractal(p * scale + off, 0.5, 2.0, octaves) * height
        d = (p - fc).length
        t = min(1.0, max(0.0, (d - flat_radius) / max(flat_falloff, 1e-6)))
        t = t * t * (3 - 2 * t)
        v.co.z = h * t
    o = bm_mesh._finish(name, bm, smooth=True)
    o["is_ground"] = True
    return f"{name}: {size[0]}x{size[1]} m, {len(o.data.polygons)} faces"


def street(ctx, name="street", length=40.0, road_width=7.0, sidewalk=2.5, curb=0.15, lanes=2,
           location=(0, 0, 0), rotation_z=0.0, markings=True):
    """Road along Y with sidewalks and curbs on both sides and dashed lane lines. Parts are
    GEO_<name>_road / _walk_L / _walk_R / _lines."""
    base = _geo(name)
    made = []
    rz = math.radians(rotation_z)
    loc = Vector(location)
    rot = Matrix.Rotation(rz, 3, "Z")

    def put(o):
        o.location = loc + rot @ Vector(o.location)
        o.rotation_euler.z = rz
        made.append(o.name)

    # the road runs 1 cm under each curb and 1 cm deeper: no coplanar faces (no z-fighting)
    put(bm_mesh.box(f"{base}_road", (road_width + 0.02, length, 0.06), (0, 0, -0.06)))
    for side, sx in (("L", -1), ("R", 1)):
        put(bm_mesh.box(f"{base}_walk_{side}", (sidewalk, length, curb + 0.05),
                        (sx * (road_width + sidewalk) / 2, 0, -0.05)))
    if markings and lanes > 1:
        bm = bmesh.new()
        dash, gap = 3.0, 3.0
        for li in range(1, lanes):
            x = -road_width / 2 + road_width * li / lanes
            y = -length / 2 + gap / 2
            while y + dash < length / 2:
                r = bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
                vs = r["verts"]
                bmesh.ops.scale(bm, vec=Vector((0.15, dash, 1)), verts=vs)
                bmesh.ops.translate(bm, vec=Vector((x, y + dash / 2, 0.002)), verts=vs)
                y += dash + gap
        put(bm_mesh._finish(f"{base}_lines", bm))
    return f"street {base}: {made}"


KIT = {  # piece -> builder(grid, height, thickness)
    "wall": lambda g, h, t: ((g, t, h), (g / 2, t / 2, 0)),
    "floor": lambda g, h, t: ((g, g, t), (g / 2, g / 2, -t)),
    "pillar": lambda g, h, t: ((t * 2, t * 2, h), (0, 0, 0)),
    "step": lambda g, h, t: ((g, g / 4, h / 12), (g / 2, g / 8, 0)),
}


def modular_kit(ctx, prefix="kit", pieces=("wall", "floor", "pillar"), grid=2.0, height=3.0, thickness=0.2,
                hide=True, location=(0, -50, 0)):
    """Kit pieces sized to a ``grid`` (origin on a grid corner, so snapping is exact). Each is a
    separate mesh reused by `kit_layout` as linked copies."""
    made = []
    for i, p in enumerate(pieces):
        size, offset = KIT[p](grid, height, thickness)
        n = _geo(f"{prefix}_{p}")
        o = bm_mesh.box(n, size, (0, 0, 0))
        o.data.transform(Matrix.Translation(Vector(offset)))  # origin on the grid corner
        o.location = Vector(location) + Vector((i * grid * 1.5, 0, 0))
        o["kit_piece"] = p
        o["kit_grid"] = grid
        o["kit_height"] = height
        if hide:
            o.hide_render = True
        made.append(n)
    return f"kit {made} on a {grid} m grid"


def kit_layout(ctx, layout, prefix="kit", name="layout", grid=None):
    """``layout``: [[piece, gx, gy, rot_deg(, gz)], ...] in grid cells. Creates linked copies
    (shared mesh data: one edit updates every copy) named GEO_<name>_<piece>_<n>."""
    made = 0
    for k, item in enumerate(layout):
        piece, gx, gy, rot = item[:4]
        gz = item[4] if len(item) > 4 else 0
        src = _obj(_geo(f"{prefix}_{piece}"))
        g = grid or src.get("kit_grid", 2.0)
        n = _geo(f"{name}_{piece}_{k:03d}")
        bm_scene.remove_object(n)
        o = bpy.data.objects.new(n, src.data)
        bm_scene.link_exclusive(o)
        o.location = (gx * g, gy * g, gz * src.get("kit_height", 3.0))
        o.rotation_euler.z = math.radians(rot)
        o.hide_render = False
        made += 1
    return f"{made} kit pieces placed"


def scatter_props(ctx, surface, source, name=None, density=0.5, seed=0, scale_min=0.8, scale_max=1.2):
    """Scatter ``source`` over ``surface`` with the geometry-nodes scatter group."""
    gn = bm_part.load_subskill(ctx.skill_root, "geometry-nodes")
    name = name or f"{source.replace('GEO_', '')}_scatter"
    return gn.scatter(ctx, name, surface, source, density=density, seed=seed, scale_min=scale_min,
                      scale_max=scale_max)


def swap_proxy(ctx, proxy, asset, name=None, fit=True, hide_proxy=True):
    """Replace a blockout proxy with a linked copy of ``asset`` at the proxy's place and
    rotation, scaled (uniformly, optional) to the proxy's height."""
    p, a = _obj(proxy), _obj(asset)
    name = _geo(name or proxy.replace("PRX_", ""))
    bm_scene.remove_object(name)
    o = bpy.data.objects.new(name, a.data)
    bm_scene.link_exclusive(o)
    o.matrix_world = p.matrix_world.copy()
    o.scale = (1, 1, 1)
    if fit:
        bpy.context.view_layer.update()
        ph = p.dimensions.z or 1.0
        ah = a.dimensions.z / max(a.scale.z, 1e-9) or 1.0
        s = ph / ah
        o.scale = (s, s, s)
    if hide_proxy:
        p.hide_render = True
        p.hide_set(True)
    return f"{proxy} -> {name}"


# ------------------------------------------------------------------ checks
def _tree(o):
    mw = o.matrix_world
    dg = bpy.context.evaluated_depsgraph_get()
    me = o.evaluated_get(dg).data
    return BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons]), me, mw


@bm_checks.register("no_zfight")
def _no_zfight(ctx, objects="GEO_", eps=2e-4, max_faces=1500, allow=()):
    """Coplanar overlapping faces between different objects (flicker in render)."""
    objs = [o for o in bm_checks.select(objects) if not o.hide_render and o.data.polygons]
    allow = {frozenset(p) for p in allow}
    trees = {o.name: _tree(o) for o in objs}
    hits = {}
    for i, a in enumerate(objs):
        ta, me, mw = trees[a.name]
        nmat = mw.to_3x3().inverted().transposed()
        step = max(1, len(me.polygons) // max_faces)
        for b in objs[i + 1:]:
            if frozenset((a.name, b.name)) in allow:
                continue
            tb = trees[b.name][0]
            n = 0
            for poly in me.polygons[::step]:
                c = mw @ poly.center
                r = tb.find_nearest(c, eps)
                if r[0] is not None and abs((nmat @ poly.normal).normalized().dot(r[1])) > 0.999:
                    n += 1
            if n:
                hits[f"{a.name}|{b.name}"] = n
    return not hits, hits or "none", "no coplanar overlapping faces", ""


@bm_checks.register("camera_coverage")
def _camera_coverage(ctx, camera="CAM_hero", objects="GEO_", min_fraction=0.8):
    """Share of the listed objects whose bounds centre is inside the camera frame."""
    from bpy_extras.object_utils import world_to_camera_view
    import bm_verify
    cam = bpy.data.objects.get(camera)
    objs = [o for o in bm_checks.select(objects) if not o.hide_render and not o.get("is_ground")]
    if cam is None or not objs:
        return False, None, camera, "camera or objects missing"
    sc = bpy.context.scene
    inside = 0
    for o in objs:
        lo, hi = bm_verify.world_bounds(o)
        p = world_to_camera_view(sc, cam, (lo + hi) / 2)
        inside += 0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0
    f = inside / len(objs)
    return f >= min_fraction, round(f, 3), f">= {min_fraction} of objects in frame", ""


OPS = {"terrain": terrain, "street": street, "modular_kit": modular_kit, "kit_layout": kit_layout,
       "scatter_props": scatter_props, "swap_proxy": swap_proxy}
FIXES = {}
