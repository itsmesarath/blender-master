"""product-shots ops: studio setups sized to the product (sweep, softboxes, long lens), product
turntables and motion beats on a pivot, cloth reveals, logo reveals, end cards - plus the
lighting and camera ops re-exported, and a title/action-safe framing check."""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Vector

import bm_anim
import bm_checks
import bm_part
import bm_scene
import bm_verify

SKILL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_L = bm_part.load_subskill(SKILL_ROOT, "lighting-cameras")
_M = bm_part.load_subskill(SKILL_ROOT, "modeling-topology")
_S = bm_part.load_subskill(SKILL_ROOT, "materials-shading")


def _bounds(objects):
    objs = bm_checks.select(objects)
    bpy.context.view_layer.update()
    lo, hi = bm_verify.bounds_of(objs)
    return objs, lo, hi


STYLES = {"white": (0.8, 0.8, 0.8), "grey": (0.35, 0.35, 0.36), "dark": (0.03, 0.03, 0.035),
          "warm": (0.75, 0.6, 0.45), "cool": (0.4, 0.5, 0.62)}


def studio(ctx, subject="GEO_", style="grey", color=None, camera="CAM_hero", lens=85.0, view="three_quarter",
           fill=0.6, sweep_scale=12.0, world_strength=0.3):
    """Seamless sweep scaled to the product, sweep material, soft top + strip lights and (if
    missing) an 85 mm hero camera. Hand-placed cameras are left alone."""
    objs, lo, hi = _bounds(subject)
    size = max((hi - lo).length, 0.05)
    w = size * sweep_scale
    _M.cyclorama(ctx, "GEO_sweep", width=w, depth=w * 0.6, height=w * 0.4, radius=w * 0.12, thickness=size * 0.05)
    sw = bpy.data.objects["GEO_sweep"]
    sw.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2 + w * 0.15, lo.z - 1e-4)
    sw["is_ground"] = True
    col = color or STYLES[style]
    _S.material(ctx, "sweep", preset="paper_backdrop", color=col)
    _S.assign(ctx, "sweep", ["GEO_sweep"])
    _L.world(ctx, kind="studio", color=tuple(c * 0.3 for c in col), strength=world_strength)
    if camera not in bpy.data.objects:
        _L.camera(ctx, camera, lens=lens, view=view, objects=[o.name for o in objs], fill=fill)
    _L.softbox_studio(ctx, objects=[o.name for o in objs], camera=camera)
    return f"studio {style}: sweep {w:.2f} m, {lens} mm"


def _pivot(objects, name="CTRL_product_pivot"):
    objs, lo, hi = _bounds(objects)
    p = bpy.data.objects.get(name)
    if p is None:
        p = bpy.data.objects.new(name, None)
        p.empty_display_type = "CIRCLE"
        bm_scene.link_exclusive(p)
        p.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
        p.empty_display_size = max((hi - lo).x, (hi - lo).y)
        bpy.context.view_layer.update()
    for o in objs:
        if o.parent != p:
            mw = o.matrix_world.copy()
            o.parent = p
            o.matrix_parent_inverse = p.matrix_world.inverted()
            o.matrix_world = mw
    return p


def turntable(ctx, subject="GEO_", frames=96, degrees=360.0, start=1, loop=True):
    """Spin the product on a pivot at its base (linear, seamless when ``loop``). The camera stays
    still, so reflections slide across the product (unlike a camera orbit)."""
    p = _pivot(subject)
    bm_anim.key(p, "rotation_euler", 2, start, 0.0, "LINEAR")
    bm_anim.key(p, "rotation_euler", 2, start + frames, math.radians(degrees), "LINEAR")
    if loop:
        bm_anim.make_cyclic(p, "rotation_euler")
    return f"turntable {degrees} deg over {frames} frames"


def motion_beats(ctx, subject="GEO_", beats=()):
    """Keyed hero moves on the pivot: beats = [{"frame": f, "rotate_z": deg, "lift": m,
    "scale": s, "tilt": deg}, ...] with eased (Bezier) transitions and holds."""
    p = _pivot(subject)
    z0 = p.location.z
    for b in beats:
        f = b["frame"]
        if "rotate_z" in b:
            bm_anim.key(p, "rotation_euler", 2, f, math.radians(b["rotate_z"]))
        if "tilt" in b:
            bm_anim.key(p, "rotation_euler", 0, f, math.radians(b["tilt"]))
        if "lift" in b:
            bm_anim.key(p, "location", 2, f, z0 + b["lift"])
        if "scale" in b:
            for i in range(3):
                bm_anim.key(p, "scale", i, f, b["scale"])
    for fc in bm_anim.fcurves(p):
        for kp in fc.keyframe_points:
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()
    return f"{len(beats)} beats on {p.name}"


def cloth_reveal(ctx, subject="GEO_", frames=(1, 72), pull_start=24, preset="silk", margin=1.6,
                 resolution=40, color=(0.5, 0.05, 0.08), name="GEO_reveal_cloth"):
    """A sheet drapes over the product, then a hooked edge pulls it up and away from
    ``pull_start``. Bakes the cloth so renders in later parts read the same motion."""
    phys = bm_part.load_subskill(SKILL_ROOT, "physics-simulation")
    objs, lo, hi = _bounds(subject)
    c = (lo + hi) / 2
    s = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) * margin * 1.6
    bm_scene.remove_object(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=resolution, y_segments=resolution, size=s / 2)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    cl = bpy.data.objects.new(name, me)
    bm_scene.link_exclusive(cl)
    cl.location = (c.x, c.y, hi.z + s * 0.05)
    edge = [v.index for v in me.vertices if v.co.y > s / 2 - 1e-6]   # back edge is pulled
    vg = cl.vertex_groups.new(name="pin")
    vg.add(edge, 1.0, "REPLACE")
    hook = bpy.data.objects.new("CTRL_reveal_hook", None)
    bm_scene.link_exclusive(hook)
    hook.location = cl.location + Vector((0, s / 2, 0))
    hm = cl.modifiers.new("Hook", "HOOK")
    hm.object = hook
    hm.vertex_indices_set(edge)
    bpy.context.view_layer.update()
    hm.center = hook.location
    hm.matrix_inverse = hook.matrix_world.inverted()
    phys.cloth(ctx, name, preset=preset, pin="pin", quality=6, frame_start=frames[0], frame_end=frames[1])
    phys.collision(ctx, [o.name for o in objs] + ([n for n in ("GEO_sweep",) if n in bpy.data.objects]))
    h0 = hook.location.copy()
    bm_anim.key(hook, "location", 1, frames[0], h0.y)
    bm_anim.key(hook, "location", 2, frames[0], h0.z)
    bm_anim.key(hook, "location", 1, pull_start, h0.y)
    bm_anim.key(hook, "location", 2, pull_start, h0.z)
    bm_anim.key(hook, "location", 1, frames[1], h0.y + s * 2.5)
    bm_anim.key(hook, "location", 2, frames[1], h0.z + s * 1.5)
    _S.material(ctx, "reveal_cloth", preset="fabric", color=color)
    _S.assign(ctx, "reveal_cloth", [name])
    phys.bake(ctx)
    return f"{name}: {preset} reveal, pull from frame {pull_start}"


def _text(name, body, size, extrude, align="CENTER"):
    bm_scene.remove_object(name)
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    o = bpy.data.objects.new(name, cu)
    bm_scene.link_exclusive(o)
    return o


def logo_reveal(ctx, text="BRAND", name="GEO_logo", location=(0, 0, 0.3), size=0.1, extrude=0.01,
                frames=(1, 24), style="rise", material=None, color=(0.9, 0.75, 0.35), facing=(90, 0, 0),
                hidden_before=True):
    """Text logo that rises (or scales) into place between ``frames`` with an ease-out and a
    small overshoot. Faces -Y by default (toward a front camera). With ``hidden_before`` it is
    switched off in renders until the move starts, so it never peeks out earlier (check
    ``hidden_until``)."""
    o = _text(name, text, size, extrude)
    o.rotation_euler = [math.radians(a) for a in facing]
    loc = Vector(location)
    f0, f1 = frames
    if style == "rise":
        bm_anim.key(o, "location", 2, f0, loc.z - size * 1.5)
        bm_anim.key(o, "location", 2, f1 - (f1 - f0) * 0.2, loc.z + size * 0.08)
        bm_anim.key(o, "location", 2, f1, loc.z)
        o.location.x, o.location.y = loc.x, loc.y
    else:
        o.location = loc
        for i in range(3):
            bm_anim.key(o, "scale", i, f0, 0.001)
            bm_anim.key(o, "scale", i, f1 - (f1 - f0) * 0.2, 1.08)
            bm_anim.key(o, "scale", i, f1, 1.0)
    mat_name = material or "logo"
    if f"MAT_{mat_name}" not in bpy.data.materials:
        _S.material(ctx, mat_name, preset="metal_gold", color=color)
    o.data.materials.append(bpy.data.materials[f"MAT_{mat_name}"])
    o["reveal_start"] = int(f0)
    if hidden_before:
        sc = bpy.context.scene
        for f, hide in ((min(sc.frame_start, f0 - 1), True), (f0 - 1, True), (f0, False)):
            o.hide_render = o.hide_viewport = hide
            o.keyframe_insert("hide_render", frame=f)
            o.keyframe_insert("hide_viewport", frame=f)
        o.hide_render = o.hide_viewport = False
    return f"{name}: '{text}' {style} {f0}-{f1}"


def end_card(ctx, title="BRAND", subtitle="", camera="CAM_hero", frame=1, color=(0.02, 0.02, 0.025),
             text_color=(0.95, 0.95, 0.95), distance=None, name="GEO_end_card"):
    """Full-frame card in front of ``camera`` from ``frame`` on (hidden behind the camera
    before), with a title and optional subtitle. It sits just past the near clip plane (closer
    than any set object), is lit only by its own emission, and depth of field is switched off
    from ``frame`` so the card stays sharp."""
    cam = bpy.data.objects[camera]
    cd = cam.data
    if distance is None:
        distance = max(cd.clip_start * 2.0, 0.02)
    bpy.context.view_layer.update()
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    # camera angle spans the larger frame side (sensor fit AUTO)
    span = 2 * distance * math.tan(cd.angle / 2)
    w, h = (span, span / aspect) if aspect >= 1 else (span * aspect, span)
    bm_scene.remove_object(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((w * 1.1, h * 1.1, 1)), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    card = bpy.data.objects.new(name, me)
    bm_scene.link_exclusive(card)
    card.parent = cam
    _S.material(ctx, "end_card", preset="emissive")
    m = bpy.data.materials["MAT_end_card"]
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = 1.0
    for b in (bsdf,):
        b.inputs["Specular IOR Level"].default_value = 0.0   # no light reflections: flat colour
        b.inputs["Roughness"].default_value = 1.0
    card.data.materials.append(m)
    t = _text(name + "_title", title, h * 0.14, 0.0)
    t.parent = card
    t.location = (0, h * (0.05 if subtitle else 0), 0.001)
    _S.material(ctx, "end_card_text", preset="emissive")
    tm = bpy.data.materials["MAT_end_card_text"]
    tb = next(n for n in tm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tb.inputs["Emission Color"].default_value = (*text_color, 1)
    tb.inputs["Emission Strength"].default_value = 1.0
    tb.inputs["Specular IOR Level"].default_value = 0.0
    t.data.materials.append(tm)
    if subtitle:
        st = _text(name + "_subtitle", subtitle, h * 0.05, 0.0)
        st.parent = card
        st.location = (0, -h * 0.12, 0.001)
        st.data.materials.append(tm)
    # behind the camera until ``frame``, then in front
    for f, z in ((max(sc.frame_start, frame - 1), distance), (frame, -distance)):
        bm_anim.key(card, "location", 2, f, z, "CONSTANT")
    if cd.dof.use_dof:
        for f, v in ((max(sc.frame_start, frame - 1), True), (frame, False)):
            cd.dof.use_dof = v
            cd.dof.keyframe_insert("use_dof", frame=f)
        cd.dof.use_dof = True
    return f"{name}: '{title}' from frame {frame}"


@bm_checks.register("reveal_clear")
def _reveal_clear(ctx, subject="GEO_", cloth="GEO_reveal_cloth", frame=None):
    """At the end of a reveal no cloth vertex is left over the product's footprint above its
    lower fifth (the product is uncovered)."""
    sc = bpy.context.scene
    objs, lo, hi = _bounds(subject)
    objs = [o for o in objs if o.name != cloth]
    lo, hi = bm_verify.bounds_of(objs)
    sc.frame_set(frame or sc.frame_end)
    dg = bpy.context.evaluated_depsgraph_get()
    cl = bpy.data.objects[cloth].evaluated_get(dg)
    zcut = lo.z + (hi.z - lo.z) * 0.2
    n = sum(1 for v in cl.data.vertices
            for p in [cl.matrix_world @ v.co]
            if lo.x <= p.x <= hi.x and lo.y <= p.y <= hi.y and p.z > zcut)
    sc.frame_set(sc.frame_start)
    return n == 0, n, "no cloth over the product at the end", ""


@bm_checks.register("safe_area")
def _safe_area(ctx, camera="CAM_hero", objects="GEO_", safe=0.9, frame=None):
    """Projected bounds of ``objects`` stay inside the centred safe area (0.9 action-safe,
    0.8 title-safe) of ``camera``."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    cam = bpy.data.objects.get(camera)
    objs = [o for o in bm_checks.select(objects, mesh_only=False)
            if o.type in {"MESH", "FONT", "CURVES"} and not o.get("is_ground") and not o.hide_render]
    if cam is None or not objs:
        return False, None, camera, "camera or objects missing"
    m = (1 - safe) / 2
    xs, ys = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            p = world_to_camera_view(sc, cam, ev.matrix_world @ Vector(c))
            xs.append(p.x)
            ys.append(p.y)
    box = [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]
    ok = box[0] >= m and box[1] >= m and box[2] <= 1 - m and box[3] <= 1 - m
    return ok, box, f"inside [{m:.2f}, {1 - m:.2f}]", ""


@bm_checks.register("hidden_until")
def _hidden_until(ctx, objects="GEO_logo", frame=None, camera="CAM_hero", step=3):
    """Before its reveal (``frame``, or each object's ``reveal_start``) an object is either off
    in renders or entirely outside the camera view - nothing peeks out early."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = bpy.data.objects.get(camera)
    objs = [o for o in bm_checks.select(objects, mesh_only=False) if o.type in {"MESH", "FONT", "CURVES"}]
    if cam is None or not objs:
        return False, None, objects, "camera or objects missing"
    keep = sc.frame_current
    seen = []
    for o in objs:
        start = frame if frame is not None else o.get("reveal_start")
        if start is None:
            continue
        frames = sorted(set(list(range(sc.frame_start, int(start), step)) + [int(start) - 1]))
        for f in frames:
            if f < sc.frame_start:
                continue
            sc.frame_set(f)
            if o.hide_render:
                continue
            ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
            pts = [world_to_camera_view(sc, cam, ev.matrix_world @ Vector(c)) for c in ev.bound_box]
            inside = any(0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0 for p in pts)
            if inside:
                seen.append((o.name, f))
                break
    sc.frame_set(keep)
    return not seen, seen[:5], "hidden or out of frame before the reveal", ""


LIGHTING_OPS = ("world", "three_point", "softbox_studio", "sun", "practical", "camera", "depth_of_field",
                "track_to")
OPS = {k: _L.OPS[k] for k in LIGHTING_OPS if k in _L.OPS}
OPS.update({"studio": studio, "turntable": turntable, "motion_beats": motion_beats, "cloth_reveal": cloth_reveal,
            "logo_reveal": logo_reveal, "end_card": end_card, "camera_orbit": _L.OPS["turntable"]})
FIXES = dict(_L.FIXES)
