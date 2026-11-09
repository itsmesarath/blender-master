"""lighting-cameras ops: world setups, light rigs sized from the subject's bounds, cameras with
framing, depth of field, orbit/turntable rigs. Fixers: framing (dolly) and exposure (scale
light power)."""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

import bm_anim
import bm_camera
import bm_checks
import bm_scene
import bm_verify


def _subject(objects):
    objs = bm_checks.select(objects)
    lo, hi = bm_verify.bounds_of(objs)
    return objs, lo, hi, (lo + hi) / 2, max((hi - lo).length, 0.05)


def _light(name, kind, location, target=None, energy=100.0, size=1.0, temperature=None, color=None, spread=None):
    if not name.startswith("LGT_"):
        name = "LGT_" + name
    bm_scene.remove_object(name)
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    if kind == "AREA":
        data.shape = "RECTANGLE"
        sx, sy = (size, size) if not isinstance(size, (list, tuple)) else size
        data.size, data.size_y = sx, sy
        if spread is not None:
            data.spread = math.radians(spread)
    elif kind in ("POINT", "SPOT"):
        data.shadow_soft_size = size if not isinstance(size, (list, tuple)) else size[0]
    elif kind == "SUN":
        data.angle = math.radians(size)
    if temperature:
        data.use_temperature = True
        data.temperature = temperature
    if color:
        data.color = color[:3]
    o = bpy.data.objects.new(name, data)
    bm_scene.link_exclusive(o)
    o.location = location
    if target is not None:
        o.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    o["base_energy"] = energy
    return o


# ------------------------------------------------------------------ world
def world(ctx, kind="studio", color=(0.05, 0.05, 0.055), strength=1.0, sun_elevation=35.0, sun_rotation=0.0):
    """kind: studio (flat colour), sky (physical sky), night (near-black), gradient (horizon fade)."""
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("WLD_main")
    sc.world = w
    nt = w.node_tree
    for n in [n for n in nt.nodes if n.bl_idname != "ShaderNodeOutputWorld"]:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    if kind == "sky":
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "MULTIPLE_SCATTERING"
        sky.sun_elevation = math.radians(sun_elevation)
        sky.sun_rotation = math.radians(sun_rotation)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    elif kind == "gradient":
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * 0.4 for c in color], 1)
        ramp.color_ramp.elements[1].color = (*color, 1)
        nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
        nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    else:
        c = (0.002, 0.002, 0.003) if kind == "night" else color
        bg.inputs["Color"].default_value = (*c, 1)
    w["base_strength"] = strength
    return f"world {kind} strength {strength}"


# ------------------------------------------------------------------ rigs
def three_point(ctx, objects="GEO_", camera="CAM_hero", key_energy=None, ratio=3.0, warm=4800, cool=7000,
                rim=True, softness=1.0):
    """Key / fill / rim placed relative to the camera's view of the subject. Energy scales with
    distance squared so the same rig works for a ring and a car."""
    objs, lo, hi, c, d = _subject(objects)
    cam = bpy.data.objects.get(camera)
    view = (cam.location - c).normalized() if cam else Vector((0.6, -1, 0.4)).normalized()
    side = view.cross(Vector((0, 0, 1))).normalized()
    r = d * 1.8
    key_energy = key_energy or 60.0 * r * r
    k = _light("key", "AREA", c + (view * 0.6 - side * 0.8).normalized() * r + Vector((0, 0, d * 0.8)), c,
               key_energy, d * 0.9 * softness, warm)
    f = _light("fill", "AREA", c + (view * 0.7 + side * 0.9).normalized() * r + Vector((0, 0, d * 0.3)), c,
               key_energy / ratio, d * 1.4 * softness, cool)
    out = [k.name, f.name]
    if rim:
        rl = _light("rim", "AREA", c - view * r * 0.9 + Vector((0, 0, d * 1.0)), c, key_energy * 0.8, d * 0.5, cool)
        out.append(rl.name)
    return f"three-point {out} key {key_energy:.0f} W"


def softbox_studio(ctx, objects="GEO_", camera="CAM_hero", energy=None, strips=True, top=True, kicker=True):
    """Product studio: big soft top light, two tall strip lights for long clean reflections on
    glossy edges, and a low kicker behind for separation."""
    objs, lo, hi, c, d = _subject(objects)
    cam = bpy.data.objects.get(camera)
    view = (cam.location - c).normalized() if cam else Vector((0, -1, 0.3)).normalized()
    view.z = 0
    view.normalize()
    side = view.cross(Vector((0, 0, 1))).normalized()
    r = d * 1.6
    energy = energy or 90.0 * r * r
    out = []
    if top:
        out.append(_light("top", "AREA", c + Vector((0, 0, r * 1.2)), c, energy, (d * 1.6, d * 1.6), 5600).name)
    if strips:
        for s, nm in ((-1, "strip_L"), (1, "strip_R")):
            o = _light(nm, "AREA", c + side * s * r + view * r * 0.35, c, energy * 0.6, (d * 0.25, d * 1.8), 5600)
            out.append(o.name)
    if kicker:
        out.append(_light("kicker", "AREA", c - view * r + Vector((0, 0, d * 0.15)), c, energy * 0.5, d * 0.6, 6500).name)
    return f"softbox studio {out}"


def sun(ctx, elevation=35.0, azimuth=30.0, energy=4.0, angle=1.5, temperature=5600, name="LGT_sun"):
    """Directional sun. azimuth 0 = light travelling towards +Y (sun in the south)."""
    o = _light(name, "SUN", (0, 0, 10), None, energy, angle, temperature)
    o.rotation_euler = (math.radians(90 - elevation), 0, math.radians(azimuth))
    return f"sun elev {elevation} az {azimuth} {energy} W/m2"


def interior_daylight(ctx, window="GEO_window_glass", room=(4.0, 3.5, 2.6), sun_energy=5.0, elevation=30.0,
                      azimuth=None, fill_energy=None, portal=True, sky_strength=1.0):
    """Daylight through a window: physical sky, sun aimed through the opening, an area light in
    the opening (portal in Cycles) and a soft ceiling bounce fill so corners are not black."""
    w, d, h = room
    world(ctx, "sky", strength=sky_strength, sun_elevation=elevation)
    win = bpy.data.objects.get(window)
    if win is not None:
        lo, hi = bm_verify.world_bounds(win)
        wc = (lo + hi) / 2
        ws = hi - lo
    else:
        wc, ws = Vector((0, d / 2, 1.5)), Vector((1.0, 0.05, 1.2))
    inward = Vector((0, -1, 0)) if abs(wc.y) >= abs(wc.x) and wc.y > 0 else \
        Vector((0, 1, 0)) if abs(wc.y) >= abs(wc.x) else Vector((-1, 0, 0)) if wc.x > 0 else Vector((1, 0, 0))
    if azimuth is None:
        azimuth = math.degrees(math.atan2(-inward.x, inward.y)) + 20.0
    sun(ctx, elevation, azimuth, sun_energy)
    width = max(ws.x, ws.y)
    out = []
    a = _light("window_fill", "AREA", wc + inward * 0.05, wc + inward * 2, 60.0 * width * ws.z, (width, ws.z), 6500)
    if portal:
        # Cycles-only alternative: a second area light with cycles.is_portal = True guides sky
        # samples through the opening. Kept off by default so EEVEE previews match Cycles.
        a["portal_hint"] = True
    out.append(a.name)
    fill_energy = fill_energy or 25.0 * w * d
    b = _light("bounce", "AREA", Vector((0, 0, h - 0.05)), Vector((0, 0, 0)), fill_energy, (w * 0.7, d * 0.7), 5000)
    out.append(b.name)
    return f"interior daylight via {window}: {out}"


def practical(ctx, name, location, energy=40.0, radius=0.05, temperature=2700):
    o = _light(name, "POINT", location, None, energy, radius, temperature)
    return o.name


# ------------------------------------------------------------------ cameras
def camera(ctx, name="CAM_hero", lens=50.0, view="three_quarter", objects="GEO_", target=None, location=None,
           fill=0.7, eye_height=None, ortho=False, shift=(0.0, 0.0), sensor=36.0, active=None):
    if not name.startswith("CAM_"):
        name = "CAM_" + name
    hero = name == ctx.facts.get("hero_camera", "CAM_hero") if active is None else active
    cam = bm_camera.make_camera(name, lens, view, bm_checks.select(objects), target, location, fill,
                                sensor, ortho, eye_height, None, hero)
    cam.data.shift_x, cam.data.shift_y = shift
    return f"{name} {lens}mm"


def depth_of_field(ctx, camera="CAM_hero", focus="GEO_", fstop=2.8, blades=7):
    """Focus on an empty at the subject centre (an empty survives geometry edits)."""
    cam = bpy.data.objects[camera]
    objs, lo, hi, c, d = _subject(focus) if focus.endswith("_") or focus in bpy.data.objects else (None, None, None, Vector(focus), 1)
    name = "CTRL_focus_" + camera.replace("CAM_", "")
    bm_scene.remove_object(name)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SPHERE"
    e.empty_display_size = 0.05
    bm_scene.link_exclusive(e)
    e.location = c
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = e
    cam.data.dof.aperture_fstop = fstop
    cam.data.dof.aperture_blades = blades
    return f"{camera} DoF f/{fstop} on {name}"


def track_to(ctx, camera="CAM_hero", target=None, objects="GEO_"):
    cam = bpy.data.objects[camera]
    if target is None:
        objs, lo, hi, c, d = _subject(objects)
        target = "CTRL_aim_" + camera.replace("CAM_", "")
        bm_scene.remove_object(target)
        e = bpy.data.objects.new(target, None)
        bm_scene.link_exclusive(e)
        e.location = c
    con = cam.constraints.get("TRACK") or cam.constraints.new("TRACK_TO")
    con.name = "TRACK"
    con.target = bpy.data.objects[target]
    con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    return f"{camera} tracks {target}"


def turntable(ctx, camera="CAM_hero", objects="GEO_", frames=48, degrees=360.0, start=1):
    """Orbit the camera around the subject: camera parented to a pivot empty keyed with linear
    interpolation and a cycles modifier, so frame start+frames equals frame start (seamless loop)."""
    objs, lo, hi, c, d = _subject(objects)
    cam = bpy.data.objects[camera]
    piv = "CTRL_orbit"
    bm_scene.remove_object(piv)
    e = bpy.data.objects.new(piv, None)
    bm_scene.link_exclusive(e)
    e.location = (c.x, c.y, lo.z)
    mw = cam.matrix_world.copy()
    cam.parent = e
    cam.matrix_world = mw
    bm_anim.key(e, "rotation_euler", 2, start, 0.0, "LINEAR")
    bm_anim.key(e, "rotation_euler", 2, start + frames, math.radians(degrees), "LINEAR")
    bm_anim.make_cyclic(e)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = start, start + frames - 1
    return f"turntable {frames} frames, {degrees} deg"


OPS = {"world": world, "three_point": three_point, "softbox_studio": softbox_studio, "sun": sun,
       "interior_daylight": interior_daylight, "practical": practical, "camera": camera,
       "depth_of_field": depth_of_field, "track_to": track_to, "turntable": turntable}


# ------------------------------------------------------------------ fixers
def _fix_frames(ctx, args, attempt):
    cam = bpy.data.objects.get(args.get("camera", "CAM_hero"))
    if cam is None:
        return "SKIP: camera missing, cannot refit"
    if cam.constraints or cam.parent is not None or not cam.get("autofit", False):
        return "SKIP: camera was placed by hand, constrained or parented; ask the user"
    cov = bm_camera.refit(cam, bm_checks.select(args.get("objects", "GEO_")), args.get("margin", 0.04),
                          args.get("min_fill", 0.15))
    return f"dollied camera: {cov}"


def _fix_exposure(ctx, args, attempt):
    """Scale every light (and the world) towards a mid-grey mean, using the last probe render."""
    probe = [c for c in ctx.report.data["checks"] if c["name"] == "exposure"]
    if not probe or not isinstance(probe[-1]["value"], dict):
        return "SKIP: no exposure probe"
    st = probe[-1]["value"]
    lo, hi = args.get("mean_min", 0.12), args.get("mean_max", 0.75)
    target = (lo + hi) / 2 if st["clipped"] <= args.get("max_clipped", 0.02) else lo + (hi - lo) * 0.3
    mean = max(st["mean"], 0.005)
    # AgX is roughly logarithmic: a 2x change in light moves the mean far less than 2x
    factor = max(0.1, min(10.0, (target / mean) ** 2.2))
    if st["clipped"] > args.get("max_clipped", 0.02):
        factor = min(factor, 0.6)
    for o in bpy.context.scene.objects:
        if o.type == "LIGHT":
            o.data.energy *= factor
    w = bpy.context.scene.world
    if w and w.node_tree:
        for n in w.node_tree.nodes:
            if n.bl_idname == "ShaderNodeBackground":
                n.inputs["Strength"].default_value *= factor
    return f"scaled lights x{factor:.2f} (mean {mean:.3f} -> ~{target:.2f})"


FIXES = {"camera_frames": _fix_frames, "exposure": _fix_exposure}
