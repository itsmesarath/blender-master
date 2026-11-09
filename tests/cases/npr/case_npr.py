import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_mesh  # noqa: E402
import bm_render  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="npr_test", subskill="npr-stylized")
    bm_scene.clear_scene()
    N, L = H.ops("npr-stylized"), H.ops("lighting-cameras")
    bm_mesh.sphere("GEO_ball", 0.5, 48, 24)
    bm_mesh.box("GEO_block", (0.6, 0.6, 0.6), (1.0, 0.2, 0))
    N.toon_material(ctx, "toon_red", color=(0.85, 0.2, 0.15), steps=3, rim=0.15, targets=["GEO_ball"])
    N.toon_material(ctx, "toon_blue", color=(0.2, 0.4, 0.85), steps=2, targets=["GEO_block"])
    N.outline(ctx, ["GEO_ball", "GEO_block"], thickness=0.015)
    ok, v = H.check(ctx, "npr_setup", objects=["GEO_ball", "GEO_block"], need_outline=True)
    H.expect("setup", ok, v)
    N.flat_world(ctx, (0.9, 0.86, 0.78))
    L.camera(ctx, "CAM_hero", lens=50, view="three_quarter", objects=["GEO_ball", "GEO_block"], fill=0.6)
    bm_render.preview_settings(samples=8, res=(320, 180))
    bm_render.render_still(ctx.path("renders", "toon.png"), "CAM_hero")
    ok, v = H.check(ctx, "npr_flat", pattern="renders/toon.png")
    H.expect("flat_bands", ok, v)
    N.painterly(ctx, size=4, posterize=6, glare=0.0)
    tree = bpy.context.scene.compositing_node_group
    H.expect("painterly_chain", any(n.bl_idname == "CompositorNodeKuwahara" for n in tree.nodes))
    bm_render.render_still(ctx.path("renders", "paint.png"), "CAM_hero")
    H.expect("paint_render", ctx.path("renders", "paint.png"))
    N.freestyle(ctx, thickness=1.2)
    H.expect("freestyle_on", bpy.context.scene.render.use_freestyle)
    H.data("lineart", N.line_art(ctx))
    gp = bpy.data.objects["FX_lineart"]
    H.expect("lineart_modifier", any(m.type == "LINEART" for m in gp.modifiers))


H.run(body)
