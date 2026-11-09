"""blockout-spatial-brief ops: scene setup, real-scale proxies, hero cameras, review layer,
spatial-brief files. All ops are idempotent (re-running replaces, never duplicates)."""
from __future__ import annotations

import json
import math
import os

import bpy
from mathutils import Vector

import bm_mesh
import bm_scene
import bm_verify

SHAPES = {"box", "cylinder", "sphere", "plane"}


def setup_scene(ctx, units="METRIC", fps=24, frame_range=(1, 48), clear=True):
    if clear:
        bm_scene.clear_scene()
    bm_scene.set_units(units)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = frame_range
    for c in ("BLOCKOUT", "GEO", "LIGHTS", "CAMERAS", "REVIEW"):
        bm_scene.ensure_collection(c)
    return f"units={units} fps={fps} frames={list(frame_range)}"


def proxy(ctx, name, shape="box", size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0), note="", display="SOLID"):
    """A real-scale stand-in. size = full extents in metres (cylinder/sphere: diameter, diameter, height)."""
    if not name.startswith("PRX_"):
        name = "PRX_" + name
    if shape not in SHAPES:
        raise ValueError(f"shape must be one of {sorted(SHAPES)}")
    rot = tuple(math.radians(r) for r in rotation)
    if shape == "box":
        o = bm_mesh.box(name, size, location, rot)
    elif shape == "cylinder":
        o = bm_mesh.cylinder(name, size[0] / 2, size[2], 24, location, rot)
        if abs(size[0] - size[1]) > 1e-6:
            raise ValueError("cylinder proxies are round: size[0] must equal size[1]")
    elif shape == "sphere":
        o = bm_mesh.sphere(name, size[0] / 2, 24, 12, location)
    else:
        o = bm_mesh.plane(name, size[:2], location)
    o.display_type = display
    o.color = (0.55, 0.6, 0.7, 1.0)
    bm_scene.set_note(o, note or f"{shape} proxy")
    return f"{name} {shape} {list(size)}"


def ground(ctx, size=(6, 6), name="PRX_ground", note="ground plane at z=0"):
    o = bm_mesh.plane(name, size)
    bm_scene.set_note(o, note)
    o["is_ground"] = True          # cameras fit the subject, not the floor
    return name


def camera(ctx, name="CAM_hero", lens=50.0, view="three_quarter", target=None, location=None,
           fill=0.7, objects="PRX_", eye_height=None, sensor=36.0, ortho=False, clip_end=None):
    """Hero camera. Give location+target, or a named view and let it fit the bounds of ``objects``
    so the subject fills ``fill`` of the short frame side. Views: front, back, left, right,
    three_quarter(_left), high, low_hero, top."""
    import bm_camera
    import bm_checks
    if not name.startswith("CAM_"):
        name = "CAM_" + name
    hero = name == ctx.facts.get("hero_camera", "CAM_hero")
    subject = [o for o in bm_checks.select(objects) if not o.get("is_ground")]
    cam = bm_camera.make_camera(name, lens, view, subject, target, location, fill, sensor,
                                ortho, eye_height, clip_end, set_active=hero)
    cam["brief_note"] = f"{view if location is None else 'placed'} {lens}mm"
    return f"{name} {lens}mm at {[round(x, 3) for x in cam.location]}"


def resolution(ctx, res=(1920, 1080)):
    r = bpy.context.scene.render
    r.resolution_x, r.resolution_y = res
    return f"{res[0]}x{res[1]}"


def review_layer(ctx, name="REV_review"):
    """Grease Pencil object for paint-over review: red strokes = remove/fix, green = add."""
    bm_scene.remove_object(name)
    gp = bpy.data.grease_pencils.new(name)
    for lname in ("REVIEW",):
        layer = gp.layers.new(lname)
        layer.frames.new(bpy.context.scene.frame_start)
    for mname, col in (("GPM_review_red", (1, 0.05, 0.05, 1)), ("GPM_review_green", (0.05, 1, 0.2, 1))):
        m = bpy.data.materials.get(mname)
        if m is None:
            m = bpy.data.materials.new(mname)
            bpy.data.materials.create_gpencil_data(m)
        m.grease_pencil.color = col
        gp.materials.append(m)
    obj = bpy.data.objects.new(name, gp)
    bm_scene.link_exclusive(obj)
    obj.hide_render = True
    return name


def review_mark(ctx, points, kind="red", note="", name="REV_review"):
    """Add one review stroke (list of xyz points). kind: red (remove/fix) or green (add)."""
    obj = bpy.data.objects[name]
    gp = obj.data
    layer = gp.layers["REVIEW"]
    frame = layer.frames[0]
    d = frame.drawing
    d.add_strokes([len(points)])
    st = d.strokes[len(d.strokes) - 1]
    for p, xyz in zip(st.points, points):
        p.position = xyz
        p.radius = 0.01
    st.material_index = 0 if kind == "red" else 1
    notes = json.loads(obj.get("review_notes", "[]"))
    notes.append({"kind": kind, "note": note, "at": list(points[0])})
    obj["review_notes"] = json.dumps(notes)
    return f"{kind} mark ({len(points)} pts)"


def write_spatial_brief(ctx):
    """brief/spatial_brief.md + brief/cameras.json from the scene."""
    sc = bpy.context.scene
    cams = []
    for o in sc.objects:
        if o.type == "CAMERA":
            cams.append({"name": o.name, "lens": o.data.lens, "type": o.data.type,
                         "location": [round(v, 4) for v in o.location],
                         "rotation_deg": [round(math.degrees(v), 2) for v in o.rotation_euler]})
    lines = ["# Spatial brief", "", f"Project: {ctx.brief['project']}", "", "| Object | Size (m) | Base | Note |", "|---|---|---|---|"]
    for o in sorted(sc.objects, key=lambda x: x.name):
        if o.type == "MESH" and o.name.startswith("PRX_"):
            lo, hi = bm_verify.world_bounds(o)
            s = hi - lo
            lines.append(f"| {o.name} | {s.x:.3f} x {s.y:.3f} x {s.z:.3f} | ({o.location.x:.2f}, {o.location.y:.2f}, {lo.z:.2f}) | {o.get('brief_note', '')} |")
    lines += ["", "## Cameras", ""] + [f"- {c['name']}: {c['lens']} mm {c['type'].lower()}" for c in cams]
    p = ctx.path("brief", "spatial_brief.md")
    with open(p, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(ctx.path("brief", "cameras.json"), "w") as f:
        json.dump(cams, f, indent=2)
    ctx.report.artefact(p, "spatial_brief")
    return f"{len(cams)} cameras"


OPS = {"setup_scene": setup_scene, "proxy": proxy, "ground": ground, "camera": camera,
       "resolution": resolution, "review_layer": review_layer, "review_mark": review_mark,
       "write_spatial_brief": write_spatial_brief}


FIXES = {}
