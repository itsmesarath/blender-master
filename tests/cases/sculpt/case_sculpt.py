import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import bm_scene  # noqa: E402


def body():
    ctx = H.make_ctx(project="sculpt_test", subskill="sculpting")
    bm_scene.clear_scene()
    M, S = H.ops("modeling-topology"), H.ops("sculpting")
    M.skin_figure(ctx, "GEO_char_body", height=1.8)
    base_ok, base_v = H.check(ctx, "symmetry_ok", objects=["GEO_char_body"], tol=0.003)
    H.data("base_symmetry", base_v)
    S.make_high(ctx, "GEO_char_body", levels=2)
    hi = bpy.data.objects["GEO_char_body_high"]
    H.expect("high_dense", len(hi.data.vertices) > 10000, len(hi.data.vertices))
    H.expect("joints_copied", "joints" in hi.keys())
    S.inflate(ctx, "GEO_char_body_high", (0.06, -0.08, 1.3), 0.08, 0.01)
    S.grab(ctx, "GEO_char_body_high", (0.0, -0.1, 1.62), 0.05, (0, -0.01, 0))
    S.crease(ctx, "GEO_char_body_high", [(0.02, -0.12, 1.66), (0.05, -0.11, 1.66)], radius=0.01)
    S.surface_noise(ctx, "GEO_char_body_high", strength=0.002, scale=30)
    S.smooth(ctx, "GEO_char_body_high", iterations=1, factor=0.3)
    ok, v = H.check(ctx, "symmetry_ok", objects=["GEO_char_body_high"], tol=0.003)
    H.expect("symmetric_after_brushes", ok, v)
    ok, v = H.check(ctx, "sculpt_detail", objects=["GEO_char_body_high"], min_verts=10000)
    H.expect("detail", ok, v)
    S.grab(ctx, "GEO_char_body_high", (0.2, 0, 1.0), 0.1, (0.03, 0, 0), mirror_x=False)
    ok, _ = H.check(ctx, "symmetry_ok", objects=["GEO_char_body_high"], tol=0.003)
    S.symmetrize(ctx, "GEO_char_body_high", direction="X")
    ok2, v2 = H.check(ctx, "symmetry_ok", objects=["GEO_char_body_high"], tol=0.003)
    H.expect("asym_detected_then_fixed", (not ok) and ok2, v2)
    bm_scene.remove_object("GEO_char_body_high")
    M.box(ctx, "GEO_rock", (1, 1, 1))
    S.voxel_remesh(ctx, "GEO_rock", voxel=0.05)
    S.multires(ctx, "GEO_rock", levels=1)
    rock = bpy.data.objects["GEO_rock"]
    H.expect("multires", rock.modifiers and rock.modifiers[0].total_levels == 1)
    S.setup_session(ctx, "GEO_rock")
    H.expect("session", rock.data.use_mirror_x)


H.run(body)
