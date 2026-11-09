"""Camera placement that frames real bounds, plus refit used by the framing fixer."""
from __future__ import annotations

import bpy
from mathutils import Vector

import bm_render
import bm_scene
import bm_verify

VIEWS = {  # direction from subject to camera
    "front": (0, -1, 0.0), "back": (0, 1, 0.0), "left": (-1, 0, 0.0), "right": (1, 0, 0.0),
    "three_quarter": (0.75, -1.0, 0.45), "three_quarter_left": (-0.75, -1.0, 0.45),
    "high": (0.6, -1.0, 1.1), "low_hero": (0.55, -1.0, 0.12), "top": (0.0, -0.0001, 1.0),
}


def make_camera(name, lens=50.0, view="three_quarter", objects=(), target=None, location=None, fill=0.7,
                sensor=36.0, ortho=False, eye_height=None, clip_end=None, set_active=False):
    bm_scene.remove_object(name)
    data = bpy.data.cameras.new(name)
    data.lens, data.sensor_width, data.sensor_fit = lens, sensor, "AUTO"
    cam = bpy.data.objects.new(name, data)
    bm_scene.link_exclusive(cam)
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    objs = list(objects)
    lo, hi = bm_verify.bounds_of(objs) if objs else (Vector((-0.5, -0.5, 0)), Vector((0.5, 0.5, 1)))
    centre = Vector(target) if target else (lo + hi) / 2
    if location is None:
        direction = Vector(VIEWS[view]).normalized()
        diameter = max((hi - lo).length, 0.05)
        loc = centre + direction * bm_render.fit_distance(diameter, lens, sensor, aspect, fill)
        if eye_height is not None:
            loc.z = eye_height
    else:
        loc = Vector(location)
    cam.location = loc
    aim(cam, centre)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = max(hi - lo) / fill
    dist = (loc - centre).length
    data.clip_start = 0.01 if dist < 5 else 0.1
    data.clip_end = clip_end or max(100.0, dist * 10)
    data.show_composition_thirds = True
    data.passepartout_alpha = 0.8
    cam["target"] = list(centre)
    cam["autofit"] = location is None
    if set_active or sc.camera is None:
        sc.camera = cam
    return cam


def aim(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()


def refit(cam, objects, margin=0.04, min_fill=0.15, max_steps=12):
    """Dolly along the view axis until all bounds sit inside the frame with margin, then (if the
    subject is tiny) dolly in until it fills at least min_fill. Lens stays unchanged; an auto-placed
    camera is first re-aimed at its stored target (it was built looking at it)."""
    target = Vector(cam.get("target", bm_verify.bounds_of(objects)[0] * 0.5 + bm_verify.bounds_of(objects)[1] * 0.5))
    if cam.get("autofit") and (cam.location - target).length > 1e-6:
        aim(cam, target)
    for _ in range(max_steps):
        bpy.context.view_layer.update()
        cov = bm_verify.frame_coverage(cam, objects, margin)
        offset = cam.location - target
        if not cov["inside"]:
            cam.location = target + offset * 1.15
        elif cov["fill"] < min_fill:
            cam.location = target + offset * 0.9
        else:
            return cov
        if cam.data.type == "ORTHO":
            cam.data.ortho_scale *= 1.15 if not cov["inside"] else 0.9
    bpy.context.view_layer.update()
    return bm_verify.frame_coverage(cam, objects, margin)
