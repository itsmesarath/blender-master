"""Preview renders: engine presets, stills from named cameras, 4-view contact sheet, turntable frames.

Previews are for the verify loop, not finals: small, low-sample, denoised, CPU-safe so they run
headless on any machine (CI included).
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

from bm_version import eevee_id
import bm_verify


def preview_settings(scene=None, engine: str = "CYCLES", samples: int = 24, res=(640, 360),
                     denoise: bool = True, transparent: bool = False, view: str = "AgX") -> None:
    scene = scene or bpy.context.scene
    r = scene.render
    r.engine = eevee_id() if engine.upper().startswith("EEVEE") else engine
    r.resolution_x, r.resolution_y = int(res[0]), int(res[1])
    r.resolution_percentage = 100
    r.film_transparent = transparent
    if r.engine == "CYCLES":
        c = scene.cycles
        c.device = "CPU"
        c.samples = samples
        c.use_adaptive_sampling = True
        c.adaptive_threshold = 0.05
        c.use_denoising = denoise
        c.max_bounces = 6
        c.transparent_max_bounces = 8
        c.transmission_bounces = 6
        c.glossy_bounces = 4
    elif r.engine == eevee_id():
        scene.eevee.taa_render_samples = max(8, samples)
    img = r.image_settings
    img.media_type = "IMAGE"          # 5.x: set media type before file format
    img.file_format = "PNG"
    img.color_mode = "RGBA" if transparent else "RGB"
    try:
        scene.view_settings.view_transform = view
    except TypeError:
        pass


def final_settings(scene=None, engine: str = "CYCLES", samples: int = 256, res=(1920, 1080), **kw) -> None:
    preview_settings(scene, engine=engine, samples=samples, res=res, **kw)
    scene = scene or bpy.context.scene
    if scene.render.engine == "CYCLES":
        scene.cycles.adaptive_threshold = 0.01
        scene.cycles.max_bounces = 12


def render_still(path: str, camera=None, scene=None) -> str:
    scene = scene or bpy.context.scene
    if camera is not None:
        scene.camera = camera if isinstance(camera, bpy.types.Object) else bpy.data.objects[camera]
    if scene.camera is None:
        raise RuntimeError("render_still: scene has no camera")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_cameras(out_dir: str, prefix: str = "CAM_", scene=None, names=None) -> list[str]:
    scene = scene or bpy.context.scene
    cams = [o for o in scene.objects if o.type == "CAMERA" and o.name.startswith(prefix)]
    if names:
        cams = [c for c in cams if c.name in names]
    keep = scene.camera
    paths = [render_still(os.path.join(out_dir, f"{c.name}.png"), c, scene) for c in cams]
    scene.camera = keep
    return paths


def _temp_camera(name, loc, target, ortho_scale=None):
    data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    data.clip_end = max(1000.0, direction.length * 4)
    return cam


def contact_sheet(objects, path: str, tile=(320, 320), scene=None) -> str:
    """Front / right / top (orthographic) + three-quarter perspective, assembled 2x2 into one PNG."""
    import numpy as np
    scene = scene or bpy.context.scene
    lo, hi = bm_verify.bounds_of(objects)
    c = (lo + hi) / 2
    size = max((hi - lo).length, 0.01)
    d = size * 2.5
    views = [
        ("front", c + Vector((0, -d, 0)), size * 1.15),
        ("right", c + Vector((d, 0, 0)), size * 1.15),
        ("top", c + Vector((0, 0.0001, d)), size * 1.15),
        ("persp", c + Vector((d * 0.7, -d * 0.7, d * 0.45)), None),
    ]
    keep = (scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.filepath)
    scene.render.resolution_x, scene.render.resolution_y = tile
    tiles = []
    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(path)), "_sheet_tmp")
    for name, loc, ortho in views:
        cam = _temp_camera(f"TMP_sheet_{name}", loc, c, ortho)
        if ortho is None:
            cam.data.lens = 50
            # fit perspective view to the bounds
            cam.location = c + (Vector(loc) - c).normalized() * size * 1.9
        p = render_still(os.path.join(tmp_dir, f"{name}.png"), cam, scene)
        img = bpy.data.images.load(p, check_existing=False)
        arr = np.empty(tile[0] * tile[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        tiles.append(arr.reshape(tile[1], tile[0], 4))
        bpy.data.images.remove(img)
        bpy.data.objects.remove(cam, do_unlink=True)
    top = np.concatenate([tiles[2], tiles[3]], axis=1)      # image rows start at the bottom
    bottom = np.concatenate([tiles[0], tiles[1]], axis=1)
    sheet = np.concatenate([bottom, top], axis=0)
    out = bpy.data.images.new("contact_sheet", tile[0] * 2, tile[1] * 2, alpha=True)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.filepath = keep
    return path


def render_frames(out_dir: str, frames, camera=None, scene=None) -> list[str]:
    scene = scene or bpy.context.scene
    out = []
    for f in frames:
        scene.frame_set(int(f))
        out.append(render_still(os.path.join(out_dir, f"frame_{int(f):04d}.png"), camera, scene))
    return out


def fit_distance(size: float, lens_mm: float, sensor_mm: float = 36.0, aspect: float = 16 / 9,
                 fill: float = 0.75) -> float:
    """Camera distance so an object of bounding-sphere diameter `size` fills `fill` of the short side."""
    fov_h = 2 * math.atan(sensor_mm / (2 * lens_mm))
    fov_v = 2 * math.atan(math.tan(fov_h / 2) / aspect)
    short = min(fov_h, fov_v)
    return (size / fill) / (2 * math.tan(short / 2))


class preview_scope:
    """Context manager: change render settings for a preview, then put the user's settings back."""

    def __init__(self, scene=None):
        self.scene = scene or bpy.context.scene

    def __enter__(self):
        s, r = self.scene, self.scene.render
        self.saved = {
            "engine": r.engine, "res": (r.resolution_x, r.resolution_y, r.resolution_percentage),
            "transparent": r.film_transparent, "filepath": r.filepath, "camera": s.camera,
            "color_mode": r.image_settings.color_mode,
        }
        if r.engine == "CYCLES":
            self.saved["cycles"] = (s.cycles.samples, s.cycles.use_denoising, s.cycles.adaptive_threshold)
        return self

    def __exit__(self, *exc):
        s, r, v = self.scene, self.scene.render, self.saved
        r.engine = v["engine"]
        r.resolution_x, r.resolution_y, r.resolution_percentage = v["res"]
        r.film_transparent, r.filepath, s.camera = v["transparent"], v["filepath"], v["camera"]
        r.image_settings.color_mode = v["color_mode"]
        if "cycles" in v:
            s.cycles.samples, s.cycles.use_denoising, s.cycles.adaptive_threshold = v["cycles"]
        return False
