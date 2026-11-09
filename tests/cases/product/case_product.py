import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import math  # noqa: E402

import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="product_test", subskill="product-shots")
    bm_scene.clear_scene()
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 48
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    M, P = H.ops("modeling-topology"), H.ops("product-shots")
    M.lathe(ctx, "GEO_can", [[0, 0], [0.033, 0], [0.033, 0.115], [0.028, 0.122], [0, 0.122]], segments=32)
    P.studio(ctx, "GEO_can", style="grey", camera="CAM_hero", lens=85, fill=0.5)
    for n in ("GEO_sweep", "CAM_hero"):
        H.expect(f"made_{n}", n in bpy.data.objects)
    H.expect("lights", sum(1 for o in bpy.data.objects if o.type == "LIGHT") >= 2)
    ok, v = H.check(ctx, "camera_frames", camera="CAM_hero", objects=["GEO_can"], min_fill=0.05)
    H.expect("frames", ok, v)
    ok, v = H.check(ctx, "safe_area", camera="CAM_hero", objects=["GEO_can"], safe=0.8)
    H.expect("title_safe", ok, v)
    P.turntable(ctx, "GEO_can", frames=48)
    piv = bpy.data.objects["CTRL_product_pivot"]
    sc.frame_set(25)
    H.expect("half_turn", abs(piv.rotation_euler.z - math.pi) < 0.01, piv.rotation_euler.z)
    sc.frame_set(1)
    P.logo_reveal(ctx, "ACME", location=(0, -0.08, 0.16), size=0.03, frames=(10, 30))
    ok, v = H.check(ctx, "hidden_until", objects="GEO_logo", camera="CAM_hero")
    H.expect("logo_hidden_before_reveal", ok, v)
    P.logo_reveal(ctx, "PEEK", name="GEO_logo_peek", location=(0, -0.08, 0.16), size=0.03, frames=(10, 30),
                  hidden_before=False)
    ok, v = H.check(ctx, "hidden_until", objects="GEO_logo_peek", camera="CAM_hero")
    H.expect("peeking_logo_caught", not ok, v)
    bpy.data.objects.remove(bpy.data.objects["GEO_logo_peek"])
    logo = bpy.data.objects["GEO_logo"]
    sc.frame_set(10)
    z10 = logo.matrix_world.translation.z
    sc.frame_set(30)
    H.expect("logo_rises", logo.matrix_world.translation.z - z10 > 0.03, z10, logo.matrix_world.translation.z)
    P.end_card(ctx, "ACME", "Stay refreshed", frame=40)
    card = bpy.data.objects["GEO_end_card"]
    sc.frame_set(39)
    H.expect("card_hidden_before", card.location.z > 0)
    sc.frame_set(40)
    ok, v = H.check(ctx, "safe_area", camera="CAM_hero", objects=["GEO_end_card_title"], safe=0.8)
    H.expect("card_title_safe", ok and card.location.z < 0, v)
    sc.frame_set(1)
    msg = P.cloth_reveal(ctx, "GEO_can", frames=(1, 30), pull_start=12, resolution=16)
    H.data("reveal", msg)
    ok, v = H.check(ctx, "sim_moved", objects=["GEO_reveal_cloth"])
    H.expect("cloth_moves", ok, v)
    sc.frame_set(12)
    dg = bpy.context.evaluated_depsgraph_get()
    cl = bpy.data.objects["GEO_reveal_cloth"].evaluated_get(dg)
    covered = sum(1 for v in cl.data.vertices if abs((cl.matrix_world @ v.co).x) < 0.03
                  and abs((cl.matrix_world @ v.co).y) < 0.03 and (cl.matrix_world @ v.co).z > 0.1)
    H.expect("draped_before_pull", covered > 0, covered)
    sc.frame_set(1)
    ok, v = H.check(ctx, "reveal_clear", subject=["GEO_can"])
    H.expect("uncovered_at_end", ok, v)
    H.expect("lighting_ops_exported", {"softbox_studio", "depth_of_field", "camera"} <= set(P.OPS))


H.run(body)
