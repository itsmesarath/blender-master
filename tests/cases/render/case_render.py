import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402
import bm_verify  # noqa: E402


def body():
    ctx = H.make_ctx(project="render_test", facts={"hero_camera": "CAM_hero", "resolution": [192, 108]},
                     subskill="render-compositing",
                     deliverables=[{"kind": "still", "cameras": ["CAM_hero", "CAM_top"]}])
    bm_scene.clear_scene()
    bm_mesh.box("GEO_floor", (3, 3, 0.02), (0, 0, -0.02))
    bm_mesh.box("GEO_cube", (0.4, 0.4, 0.4))
    L = H.ops("lighting-cameras")
    L.world(ctx, "studio", strength=0.5)
    L.camera(ctx, "CAM_hero", 50, "three_quarter", objects="GEO_cube")
    L.camera(ctx, "CAM_top", 50, "top", objects="GEO_cube")
    L.three_point(ctx, objects="GEO_cube", camera="CAM_hero")
    R = H.ops("render-compositing")

    R.render_preset(ctx, "preview", samples=8, denoiser="compositor")
    R.compositor(ctx, denoise=True, mist={"start": 1.0, "depth": 10.0}, glare={"kind": "Fog Glow"})
    ok, v = H.check(ctx, "compositor_chain", contains=["CompositorNodeDenoise", "CompositorNodeGlare"])
    H.expect("chain", ok, v)
    sc = bpy.context.scene
    H.expect("single_denoiser", not sc.cycles.use_denoising, sc.cycles.use_denoising, False)
    R.output_format(ctx, "png8")
    R.render_deliverables(ctx)
    ok, v = H.check(ctx, "render_ok", pattern="renders/*.png", min_count=2, size=[192, 108])
    H.expect("deliverables_rendered", ok, v)

    # transparent film keeps alpha
    R.compositor(ctx, denoise=False, reset=True)
    R.render_preset(ctx, "preview", samples=8, transparent=True, res=[96, 54])
    import bm_render
    p = bm_render.render_still(ctx.path("alpha", "hero_alpha.png"), "CAM_hero")
    st = bm_verify.image_stats(p)
    H.expect("alpha_present", st["alpha_min"] < 0.5, st["alpha_min"], "< 0.5")

    # multilayer EXR: media type before file format
    R.output_format(ctx, "exr_multilayer")
    img = sc.render.image_settings
    H.expect("exr_format", img.file_format == "OPEN_EXR_MULTILAYER" and img.media_type == "MULTI_LAYER_IMAGE",
             [img.media_type, img.file_format])

    # final preset raises quality, eevee preset selects the 5.x engine id
    R.render_preset(ctx, "final", samples=128)
    H.expect("final_samples", sc.cycles.samples == 128, sc.cycles.samples)
    R.eevee_preset(ctx)
    H.expect("eevee_engine", sc.render.engine == "BLENDER_EEVEE", sc.render.engine)


H.run(body)
