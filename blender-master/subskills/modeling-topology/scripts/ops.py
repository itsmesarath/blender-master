"""modeling-topology ops: real-size primitives, lathe, hard-surface bevel stack, panel insets,
boolean cuts, room shells with openings, simple furniture kit, quick UVs, modifier apply.

Every op writes GEO_ objects with scale 1 and base-centre placement (z = 0 is the floor).
"""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Vector

import bm_io
import bm_mesh
import bm_scene


def _obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise KeyError(f"object {name!r} not found")
    return o


def _geo(name):
    return name if name.startswith("GEO_") else "GEO_" + name


def _rad(rot):
    return tuple(math.radians(r) for r in rot)


# ------------------------------------------------------------------ primitives
def box(ctx, name, size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0)):
    o = bm_mesh.box(_geo(name), size, location, _rad(rotation))
    return o.name


def cylinder(ctx, name, radius=0.5, depth=1.0, segments=32, location=(0, 0, 0), rotation=(0, 0, 0)):
    o = bm_mesh.cylinder(_geo(name), radius, depth, segments, location, _rad(rotation))
    return o.name


def sphere(ctx, name, radius=0.5, segments=32, rings=16, location=(0, 0, 0), centered=True):
    """UV sphere; ``centered`` puts its centre (not its base) at ``location`` (eyes, balls)."""
    loc = list(location)
    if centered:
        loc[2] -= radius
    o = bm_mesh.sphere(_geo(name), radius, segments, rings, tuple(loc))
    return o.name


def lathe(ctx, name, profile, segments=48, location=(0, 0, 0), smooth=True):
    o = bm_mesh.lathe(_geo(name), profile, segments, location, smooth)
    return f"{o.name} {len(o.data.vertices)} verts"


def from_proxy(ctx, proxy, name=None, hide_proxy=True):
    """Copy a proxy's mesh into a GEO_ object at the same place (a start for refinement)."""
    p = _obj(proxy)
    name = _geo(name or proxy.replace("PRX_", ""))
    bm_scene.remove_object(name)
    o = bpy.data.objects.new(name, p.data.copy())
    o.matrix_world = p.matrix_world.copy()
    bm_scene.link_exclusive(o)
    if hide_proxy:
        p.hide_render = True
        p.hide_set(True)
    return name


def hide_proxies(ctx):
    n = 0
    for o in bpy.context.scene.objects:
        if o.name.startswith("PRX_"):
            o.hide_render = True
            o.hide_set(True)
            n += 1
    return f"{n} proxies hidden"


# ------------------------------------------------------------------ hard-surface
def hs_bevel(ctx, target, width=0.01, segments=3, angle=30.0, harden=True, weighted_normals=True):
    """Non-destructive hard-surface edge treatment: angle-limited Bevel -> Weighted Normal,
    smooth shading by angle. Keeps the base mesh low and editable."""
    o = _obj(target)
    for m in [m for m in o.modifiers if m.name in ("HS_bevel", "HS_wnormal")]:
        o.modifiers.remove(m)
    b = o.modifiers.new("HS_bevel", "BEVEL")
    b.width, b.segments, b.limit_method = width, segments, "ANGLE"
    b.angle_limit = math.radians(angle)
    b.harden_normals = harden
    b.miter_outer = "MITER_ARC"
    b.profile = 0.5
    if weighted_normals:
        w = o.modifiers.new("HS_wnormal", "WEIGHTED_NORMAL")
        w.keep_sharp = True
        w.mode = "FACE_AREA"
    _shade_by_angle(o, angle)
    return f"{o.name}: bevel {width} m x{segments}, weighted normals={weighted_normals}"


def _shade_by_angle(o, angle):
    _activate(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle), keep_sharp_edges=True)


def _activate(o):
    for x in bpy.context.view_layer.objects:
        if x is not None:
            x.select_set(False)
    o.hide_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def panel_inset(ctx, target, thickness=0.03, depth=0.015, faces="sides", min_area=0.0, inner_material_index=None):
    """Inset faces individually and push them in: a recessed panel with a raised frame.
    faces: 'sides' (|normal.z| < 0.5), 'top', 'all'. inner_material_index tags the recessed
    faces so a second material can tell panel from frame."""
    o = _obj(target)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    sel = []
    for f in bm.faces:
        nz = abs(f.normal.z)
        if faces == "all" or (faces == "sides" and nz < 0.5) or (faces == "top" and f.normal.z > 0.5):
            if f.calc_area() >= min_area:
                sel.append(f)
    bmesh.ops.inset_individual(bm, faces=sel, thickness=thickness, depth=-depth, use_even_offset=True)
    if inner_material_index is not None:
        for f in sel:                       # the original faces become the recessed panels
            f.material_index = inner_material_index
    bm.normal_update()
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return f"{o.name}: {len(sel)} panels inset"


def boolean_cut(ctx, target, shape="box", size=(0.2, 0.2, 0.2), location=(0, 0, 0), rotation=(0, 0, 0),
                solver="EXACT", apply=True, name="CUT"):
    """Subtract a box/cylinder cutter. Applies by default (checkpoint saved first)."""
    o = _obj(target)
    cname = f"TMP_{name}"
    if shape == "box":
        c = bm_mesh.box(cname, size, location, _rad(rotation))
    else:
        c = bm_mesh.cylinder(cname, size[0] / 2, size[2], 32, location, _rad(rotation), smooth=False)
    # cutters are base-centred like everything else; centre them on `location` instead
    c.location.z -= size[2] / 2 if shape == "box" else 0.0
    m = o.modifiers.new(f"BOOL_{name}", "BOOLEAN")
    m.operation, m.solver, m.object = "DIFFERENCE", solver, c
    c.display_type = "WIRE"
    c.hide_render = True
    if apply:
        bm_io.checkpoint(os.path.join(ctx.out_dir, "blend", "checkpoints"), f"{ctx.part_id}_{o.name}_{name}")
        _move_first(o, m.name)
        _activate(o)
        bpy.ops.object.modifier_apply(modifier=m.name)
        bm_scene.remove_object(cname)
    return f"{o.name} - {shape} {list(size)} ({solver})"


def _move_first(o, mod_name):
    idx = o.modifiers.find(mod_name)
    if idx > 0:
        o.modifiers.move(idx, 0)


# ------------------------------------------------------------------ interiors
def room_shell(ctx, name="GEO_room", width=4.0, depth=3.5, height=2.6, wall=0.12, floor=0.1,
               ceiling=True, openings=()):
    """Closed room shell: an outer block minus the inner air volume, so the result is one
    watertight solid whose inner faces point into the room. Interior spans x = +-width/2,
    y = +-depth/2, z = 0..height. Openings: {wall: north|south|east|west, kind, width,
    height, sill, offset} cut with exact booleans."""
    name = _geo(name)
    hw, hd = width / 2, depth / 2
    top = floor if ceiling else 0.0
    o = bm_mesh.box(name, (width + 2 * wall, depth + 2 * wall, height + floor + top), (0, 0, -floor))
    inner = (width, depth, height + (0 if ceiling else floor + 1.0))
    boolean_cut(ctx, name, "box", inner, (0, 0, inner[2] / 2), (0, 0, 0), "EXACT", True, "air")
    for i, op in enumerate(openings):
        w = op.get("wall", "north")
        ow, oh, sill, off = op.get("width", 1.0), op.get("height", 1.2), op.get("sill", 0.9), op.get("offset", 0.0)
        t = wall * 3
        if w in ("north", "south"):
            y = hd + wall / 2 if w == "north" else -hd - wall / 2
            loc, size = (off, y, sill + oh / 2), (ow, t, oh)
        else:
            x = hw + wall / 2 if w == "east" else -hw - wall / 2
            loc, size = (x, off, sill + oh / 2), (t, ow, oh)
        boolean_cut(ctx, name, "box", size, loc, (0, 0, 0), "EXACT", True, f"open{i}_{op.get('kind', 'window')}")
    _clean(o)
    o["room"] = f"{width}x{depth}x{height}"
    return f"{name} {width}x{depth}x{height} m, {len(openings)} openings"


def _clean(o):
    """Merge coplanar boolean leftovers so walls stay simple quads where possible."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts, edges=bm.edges)
    bm.to_mesh(o.data)
    bm.free()


def window_frame(ctx, name, width=1.0, height=1.2, sill=0.9, wall="north", room=(4, 3.5), wall_t=0.12,
                 frame=0.05, offset=0.0, glass=True):
    """Frame (4 bars) + optional glass pane placed in a room_shell opening."""
    name = _geo(name)
    hw, hd = room[0] / 2, room[1] / 2
    parts = []
    t = wall_t * 0.8
    bars = [((width, t, frame), (0, 0, sill)), ((width, t, frame), (0, 0, sill + height - frame)),
            ((frame, t, height - 2 * frame), (-width / 2 + frame / 2, 0, sill + frame)),
            ((frame, t, height - 2 * frame), (width / 2 - frame / 2, 0, sill + frame))]
    for i, (s, l) in enumerate(bars):
        parts.append(bm_mesh.box(f"TMP_bar{i}", s, l))
    o = bm_mesh.join_parts(name, parts)
    g = bm_mesh.box(_geo(name.replace("GEO_", "") + "_glass"), (width - 2 * frame, 0.006, height - 2 * frame), (0, 0, sill + frame)) if glass else None
    for ob in [o] + ([g] if g else []):
        if wall in ("north", "south"):
            ob.location = (offset, (hd + wall_t / 2) * (1 if wall == "north" else -1), ob.location.z)
        else:
            ob.location = ((hw + wall_t / 2) * (1 if wall == "east" else -1), offset, ob.location.z)
            ob.rotation_euler.z = math.radians(90)
    return f"{name}{' + glass' if g else ''}"


def cyclorama(ctx, name="GEO_sweep", width=3.0, depth=2.5, height=1.5, radius=0.5, segments=12, thickness=0.02):
    """Seamless studio backdrop: floor curving up into a back wall (no horizon line).
    Floor front edge at y = -depth/2, wall at y = +depth/2. Given thickness so it is a closed solid."""
    name = _geo(name)
    prof = []
    y0, y1 = -depth / 2, depth / 2 - radius
    prof.append((y0, 0.0))
    for i in range(segments + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / segments
        prof.append((y1 + radius * math.cos(a), radius + radius * math.sin(a)))
    prof.append((depth / 2, height))
    bm = bmesh.new()
    left = [bm.verts.new((-width / 2, y, z)) for y, z in prof]
    right = [bm.verts.new((width / 2, y, z)) for y, z in prof]
    for i in range(len(prof) - 1):
        bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
    bm.normal_update()
    if thickness:
        res = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = bm_mesh._finish(name, bm, smooth=True)
    return f"{name} {width}x{depth}x{height} r={radius}"


FURNITURE = {}


def _furn(kind):
    def deco(fn):
        FURNITURE[kind] = fn
        return fn
    return deco


@_furn("bed")
def _bed(w=1.4, d=2.0, h=0.55):
    return [((w, d, 0.25), (0, 0, 0.1)), ((w - 0.04, d - 0.04, 0.22), (0, 0, 0.35)),
            ((w, 0.06, 1.0), (0, d / 2 - 0.03, 0.0)),
            ((0.06, 0.06, 0.1), (w / 2 - 0.05, -d / 2 + 0.05, 0)), ((0.06, 0.06, 0.1), (-w / 2 + 0.05, -d / 2 + 0.05, 0)),
            ((0.06, 0.06, 0.1), (w / 2 - 0.05, d / 2 - 0.12, 0)), ((0.06, 0.06, 0.1), (-w / 2 + 0.05, d / 2 - 0.12, 0)),
            ((w * 0.38, 0.4, 0.12), (-w * 0.22, d / 2 - 0.32, 0.57)), ((w * 0.38, 0.4, 0.12), (w * 0.22, d / 2 - 0.32, 0.57))]


@_furn("desk")
def _desk(w=1.2, d=0.6, h=0.75):
    t, leg = 0.035, 0.05
    out = [((w, d, t), (0, 0, h - t))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(((leg, leg, h - t), (sx * (w / 2 - leg), sy * (d / 2 - leg), 0)))
    return out


@_furn("chair")
def _chair(w=0.45, d=0.45, h=0.9):
    seat, leg = 0.45, 0.04
    out = [((w, d, 0.04), (0, 0, seat - 0.04)), ((w, 0.04, h - seat), (0, d / 2 - 0.02, seat))]
    for sx in (-1, 1):
        for sy in (-1, 1):
            out.append(((leg, leg, seat - 0.04), (sx * (w / 2 - leg / 2), sy * (d / 2 - leg / 2), 0)))
    return out


@_furn("shelf")
def _shelf(w=0.8, d=0.3, h=1.8, shelves=5):
    t = 0.02
    out = [((t, d, h), (-w / 2 + t / 2, 0, 0)), ((t, d, h), (w / 2 - t / 2, 0, 0)), ((w, 0.01, h), (0, d / 2 - 0.005, 0))]
    for i in range(shelves):
        out.append(((w - 2 * t, d - 0.01, t), (0, -0.005, i * (h - t) / (shelves - 1))))
    return out


@_furn("table")
def _table(w=1.0, d=1.0, h=0.74):
    return _desk(w, d, h)


@_furn("rug")
def _rug(w=1.6, d=1.0, h=0.01):
    return [((w, d, h), (0, 0, 0))]


def furniture(ctx, kind, name=None, location=(0, 0, 0), rotation_z=0.0, bevel=0.004, **dims):
    """Simple parametric furniture built from boxes, joined, welded into one solid, bevelled."""
    if kind not in FURNITURE:
        raise ValueError(f"kind must be one of {sorted(FURNITURE)}")
    name = _geo(name or kind)
    boxes = FURNITURE[kind](**dims)
    parts = [bm_mesh.box(f"TMP_{kind}{i}", s, l) for i, (s, l) in enumerate(boxes)]
    o = bm_mesh.join_parts(name, parts)   # overlapping closed boxes: each island stays manifold
    o.location = location
    o.rotation_euler.z = math.radians(rotation_z)
    if bevel:
        hs_bevel(ctx, name, width=bevel, segments=2, angle=40)
    return f"{name} ({kind})"


# ------------------------------------------------------------------ modifiers / UV
def mirror(ctx, target, axis="X", clip=True):
    o = _obj(target)
    m = o.modifiers.new("MIRROR", "MIRROR")
    m.use_axis = [axis == "X", axis == "Y", axis == "Z"]
    m.use_clip = clip
    return f"{o.name} mirror {axis}"


def subdivide(ctx, target, levels=2, render_levels=None):
    o = _obj(target)
    m = o.modifiers.new("SUBSURF", "SUBSURF")
    m.levels, m.render_levels = levels, render_levels or levels
    return f"{o.name} subsurf {levels}"


def apply_modifiers(ctx, target, types=None):
    o = _obj(target)
    bm_io.checkpoint(os.path.join(ctx.out_dir, "blend", "checkpoints"), f"{ctx.part_id}_{o.name}_apply")
    _activate(o)
    names = [m.name for m in o.modifiers if types is None or m.type in types]
    for n in names:
        bpy.ops.object.modifier_apply(modifier=n)
    return f"{o.name}: applied {names}"


def uv_quick(ctx, targets="GEO_", angle=66.0, margin=0.02):
    """Fast automatic UVs (angle-based islands). Good for procedural/box-mapped looks and export
    sanity; hand-placed seams for hero assets belong to the UV sub-skill."""
    import bm_checks
    objs = [o for o in bm_checks.select(targets) if not o.data.uv_layers]
    for o in objs:
        _activate(o)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")
    return f"smart UVs on {len(objs)} objects"


def place(ctx, target, location=None, rotation=None):
    o = _obj(target)
    if location is not None:
        o.location = location
    if rotation is not None:
        o.rotation_euler = _rad(rotation)
    return o.name


# ------------------------------------------------------------------ character base mesh
def _figure_joints(h, arm_angle=40.0, head_scale=1.0):
    """Joint name -> (position, radius) for a neutral standing figure facing -Y, feet near z=0.
    Values are fractions of height ``h``; ``arm_angle`` lowers the arms from horizontal (A-pose)."""
    a = math.radians(arm_angle)
    up, fore, hand = 0.17 * h, 0.15 * h, 0.085 * h
    sh = Vector((0.1 * h, 0.0, 0.79 * h))
    d = Vector((math.cos(a), 0.0, -math.sin(a)))
    j = {
        "pelvis": ((0, 0, 0.52 * h), 0.075 * h),
        "spine": ((0, 0.003 * h, 0.62 * h), 0.068 * h),
        "chest": ((0, 0, 0.72 * h), 0.08 * h),
        "neck": ((0, 0.004 * h, 0.825 * h), 0.032 * h),
        "head": ((0, -0.006 * h, 0.885 * h), 0.062 * h * head_scale),
        "head_top": ((0, -0.004 * h, 0.95 * h), 0.058 * h * head_scale),
    }
    for side, sx in (("L", 1), ("R", -1)):
        j[f"hip_{side}"] = ((sx * 0.055 * h, 0, 0.5 * h), 0.052 * h)
        j[f"knee_{side}"] = ((sx * 0.06 * h, -0.006 * h, 0.28 * h), 0.036 * h)
        j[f"ankle_{side}"] = ((sx * 0.064 * h, 0.008 * h, 0.05 * h), 0.026 * h)
        j[f"toe_{side}"] = ((sx * 0.07 * h, -0.075 * h, 0.022 * h), 0.022 * h)
        el = sh + d * up
        wr = el + d * fore
        j[f"shoulder_{side}"] = ((sh.x * sx, sh.y, sh.z), 0.036 * h)
        j[f"elbow_{side}"] = (tuple(Vector((el.x * sx, el.y, el.z))), 0.03 * h)
        j[f"wrist_{side}"] = (tuple(Vector((wr.x * sx, wr.y, wr.z))), 0.022 * h)
        j[f"hand_{side}"] = (tuple(Vector(((wr + d * hand).x * sx, 0, (wr + d * hand).z))), 0.02 * h)
    return j


FIGURE_EDGES = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head"),
                ("head", "head_top")] + [e for s in "LR" for e in (
                    ("pelvis", f"hip_{s}"), (f"hip_{s}", f"knee_{s}"), (f"knee_{s}", f"ankle_{s}"),
                    (f"ankle_{s}", f"toe_{s}"), ("chest", f"shoulder_{s}"), (f"shoulder_{s}", f"elbow_{s}"),
                    (f"elbow_{s}", f"wrist_{s}"), (f"wrist_{s}", f"hand_{s}"))]


def skin_figure(ctx, name="GEO_char_body", height=1.8, arm_angle=40.0, head_scale=1.0, subdiv=1):
    """Humanoid base mesh from a joint skeleton with the Skin modifier, applied to real quads.
    Joint positions are stored on the object (``joints`` JSON property) for the rigging step.
    A starting point for sculpting or a stylized low-poly character, not a finished body."""
    import json
    name = _geo(name)
    j = _figure_joints(height, arm_angle, head_scale)
    keys = list(j)
    me = bpy.data.meshes.new(name + "_skel")
    me.from_pydata([j[k][0] for k in keys], [(keys.index(a), keys.index(b)) for a, b in FIGURE_EDGES], [])
    tmp = bpy.data.objects.new("TMP_skin", me)
    bm_scene.link_exclusive(tmp)
    skin = tmp.modifiers.new("Skin", "SKIN")
    skin.branch_smoothing = 0.6
    skin.use_smooth_shade = True
    for i, k in enumerate(keys):
        r = j[k][1]
        me.skin_vertices[0].data[i].radius = (r, r * (0.8 if k in ("pelvis", "spine", "chest") else 1.0))
    me.skin_vertices[0].data[keys.index("pelvis")].use_root = True
    if subdiv:
        sd = tmp.modifiers.new("Subdivision", "SUBSURF")
        sd.levels = sd.render_levels = subdiv
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me)
    bm_scene.remove_object(name)
    mesh.name = name
    obj = bpy.data.objects.new(name, mesh)
    bm_scene.link_exclusive(obj)
    zmin = min(v.co.z for v in mesh.vertices)
    k_s = height / (max(v.co.z for v in mesh.vertices) - zmin)  # hull + subdivision shrink: rescale
    for v in mesh.vertices:
        v.co = Vector((v.co.x * k_s, v.co.y * k_s, (v.co.z - zmin) * k_s))
    mesh.shade_smooth()
    joints = {k: [round(p[0] * k_s, 5), round(p[1] * k_s, 5), round((p[2] - zmin) * k_s, 5)]
              for k, (p, _r) in j.items()}
    obj["joints"] = json.dumps(joints)
    obj["joint_edges"] = json.dumps(FIGURE_EDGES)
    return f"{name}: {len(mesh.polygons)} faces, {len(joints)} joints, height {max(v.co.z for v in mesh.vertices):.2f} m"


OPS = {"skin_figure": skin_figure, "sphere": sphere, "box": box, "cylinder": cylinder, "lathe": lathe, "from_proxy": from_proxy, "hide_proxies": hide_proxies,
       "hs_bevel": hs_bevel, "panel_inset": panel_inset, "boolean_cut": boolean_cut, "room_shell": room_shell,
       "window_frame": window_frame, "cyclorama": cyclorama, "furniture": furniture, "mirror": mirror, "subdivide": subdivide,
       "apply_modifiers": apply_modifiers, "uv_quick": uv_quick, "place": place}
FIXES = {}
