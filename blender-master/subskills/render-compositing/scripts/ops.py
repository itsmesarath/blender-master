"""render-compositing ops: engine presets, colour management, compositor chains (5.x node-group
compositor), deliverable renders for stills and frame ranges."""
from __future__ import annotations

import os

import bpy

import bm_compositor
import bm_render
import bm_version


def render_preset(ctx, kind="preview", engine="CYCLES", samples=None, res=None, transparent=False,
                  view="AgX", look="None", exposure=0.0, denoiser="render"):
    """kind: preview (fast, CPU-safe) or final. denoiser: 'render' (Cycles built-in) or
    'compositor' (Denoise node fed by denoising passes) or 'none'."""
    sc = bpy.context.scene
    facts = ctx.facts
    res = tuple(res or facts.get("resolution", (1920, 1080)))
    if kind == "final":
        bm_render.final_settings(sc, engine, samples or 256, res, transparent=transparent, view=view)
    else:
        bm_render.preview_settings(sc, engine, samples or 32, res, denoise=denoiser == "render",
                                   transparent=transparent, view=view)
    try:
        sc.view_settings.look = look
    except TypeError:
        pass
    sc.view_settings.exposure = exposure
    if sc.render.engine == "CYCLES":
        sc.cycles.use_denoising = denoiser == "render"
    return f"{kind} {sc.render.engine} {res[0]}x{res[1]} samples={sc.cycles.samples if sc.render.engine == 'CYCLES' else sc.eevee.taa_render_samples}"


def compositor(ctx, denoise=False, mist=None, glare=None, reset=True):
    """Build the compositor chain: [Denoise] -> [Mist blend] -> [Glare] -> Group Output.
    mist: {start, depth, color, amount}. glare: {kind, threshold, strength}."""
    sc = bpy.context.scene
    bm_compositor.ensure_tree(sc, reset=reset)
    steps = []
    if denoise:
        if sc.render.engine != "CYCLES":
            raise ValueError("compositor denoise needs Cycles denoising passes")
        sc.cycles.use_denoising = False          # one denoiser only
        bm_compositor.add_denoise(sc)
        steps.append("denoise")
    if mist:
        bm_compositor.add_mist(sc, **mist)
        steps.append("mist")
    if glare:
        bm_compositor.add_glare(sc, **glare)
        steps.append("glare")
    return f"compositor {steps or ['pass-through']} -> Group Output"


def output_format(ctx, kind="png8"):
    """png8 / png16 / exr_multilayer (all passes in one file for grading later)."""
    img = bpy.context.scene.render.image_settings
    if kind == "exr_multilayer":
        img.media_type = "MULTI_LAYER_IMAGE"
        img.file_format = "OPEN_EXR_MULTILAYER"
        img.color_depth = "32"
    else:
        img.media_type = "IMAGE"
        img.file_format = "PNG"
        img.color_depth = "16" if kind == "png16" else "8"
    return kind


def render_deliverables(ctx, cameras=None, frames=None, subdir="renders"):
    """Render each deliverable camera to <out>/renders/<camera>.png, or a frame list per camera."""
    sc = bpy.context.scene
    cams = cameras or [c for d in ctx.brief.get("deliverables", []) for c in d.get("cameras", [])] or [sc.camera.name]
    out = []
    for cam in dict.fromkeys(cams):
        if frames:
            for f in frames:
                sc.frame_set(int(f))
                out.append(bm_render.render_still(ctx.path(subdir, f"{cam}_f{int(f):04d}.png"), cam))
        else:
            out.append(bm_render.render_still(ctx.path(subdir, f"{cam}.png"), cam))
    for p in out:
        ctx.report.artefact(p, "render")
    if frames:
        sc.frame_set(sc.frame_start)   # leave the file on its first frame for later parts
    return f"{len(out)} renders"


def eevee_preset(ctx, raytracing=True, shadows_rays=2, samples=64):
    """EEVEE settings for look-dev (GPU / software GL needed in background mode)."""
    sc = bpy.context.scene
    sc.render.engine = bm_version.eevee_id()
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_raytracing = raytracing
    sc.eevee.shadow_ray_count = shadows_rays
    return "eevee"


OPS = {"render_preset": render_preset, "compositor": compositor, "output_format": output_format,
       "render_deliverables": render_deliverables, "eevee_preset": eevee_preset}
FIXES = {}
